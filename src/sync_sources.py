"""Fetching and parsing for the roster/fixture/headshot sync job.

Kept separate from sync.py's diff-and-write logic so each source's endpoint,
selectors and licensing rules can be fixed or swapped without touching how a
parsed result gets reconciled against the database. Every function here
returns plain dicts/lists -- no D1, no js.Response objects past this module.
"""

import datetime
import html as html_entities
import json
import re

from js import fetch

# Denver Summit's team page on nwslsoccer.com. Both the schedule and roster
# tabs were assumed to render schema.org JSON-LD; verified against real
# snapshots of both on 2026-09-21/22, neither does -- they're plain
# server-rendered Next.js markup (a match-list widget and a roster table,
# respectively), so both scrape that markup directly instead. The slug also
# used to be missing "-fc" (.../denver-summit/... 404s; the real path is
# .../denver-summit-fc/...) -- that alone broke every sync regardless of
# how the response body got parsed.
NWSL_TEAM_SLUG = "cbfcacbef5bc4a278442c00926ac9ebc/denver-summit-fc"
NWSL_SCHEDULE_URL = "https://www.nwslsoccer.com/teams/{}/schedule".format(NWSL_TEAM_SLUG)

# The team id nwslsoccer.com uses internally (the first path segment of
# NWSL_TEAM_SLUG) -- used to tell which side of a match is "us" by id rather
# than by matching the team name against "denver"/"summit" substrings,
# which breaks the moment the display name is shortened (the schedule
# widget renders "Bay" and "Angel City" rather than "Bay FC"/"Angel City
# FC", so name-sniffing has false negatives even for the away teams; it
# would have false positives too if some future opponent's name ever
# contained "denver" or "summit").
DENVER_SUMMIT_TEAM_ID = NWSL_TEAM_SLUG.split("/")[0]
DENVER_SUMMIT_TEAM_SLUG = NWSL_TEAM_SLUG.split("/")[1]


def _team_roster_url(team_id, team_slug):
    """Any team's roster page, not just Denver Summit's -- fetch_nwsl_roster
    takes (team_id, team_slug) so it can fetch an opponent's roster too, for
    the Visitors dossiers. team_id is always solid (nwslsoccer.com's own
    stable id for that club, read straight off the schedule page -- see
    fetch_nwsl_schedule). team_slug is not: Denver Summit's own match-page
    slug ("denver-summit") differs from its roster-page slug
    ("denver-summit-fc"), so a same-pattern guess for another club is not
    trustworthy either. Callers other than Denver Summit's own sync pass a
    slug inferred from that club's official name and stored on
    opponents.source_slug (see migrations/0006_opponent_sync.sql) -- expect
    it to be wrong sometimes; fetch_nwsl_roster below fails loudly rather
    than silently when it is.
    """
    return "https://www.nwslsoccer.com/teams/{}/{}/roster".format(team_id, team_slug)


NWSL_ROSTER_URL = _team_roster_url(DENVER_SUMMIT_TEAM_ID, DENVER_SUMMIT_TEAM_SLUG)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
# A descriptive User-Agent, as Wikimedia's API etiquette asks for.
WIKIPEDIA_USER_AGENT = "SquadSeatsSyncBot/1.0 (https://github.com/CreativeMaladjustment/summit-basecamp)"

# NWSL club names to Wikipedia page titles for fetching current squad data
WIKIPEDIA_TEAM_PAGES = {
    "Angel City": "Angel_City_FC",
    "Bay": "Bay_FC",
    "Boston Legacy": "Boston_Legacy_FC",
    "Chicago Stars": "Chicago_Stars_FC",
    "Gotham FC": "Gotham_FC",
    "Houston Dash": "Houston_Dash",
    "Kansas City Current": "Kansas_City_Current",
    "North Carolina Courage": "North_Carolina_Courage",
    "Orlando Pride": "Orlando_Pride",
    "Portland Thorns": "Portland_Thorns_FC",
    "Racing Louisville": "Racing_Louisville_FC",
    "San Diego Wave": "San_Diego_Wave_FC",
    "Seattle Reign": "Seattle_Reign_FC",
    "Utah Royals": "Utah_Royals",
    "Washington Spirit": "Washington_Spirit",
}

# Licenses permissive enough to redistribute an image without further
# clearance. Anything else (including plain "Fair use") is skipped -- public
# data only, nothing copyrighted, per floutenvy's 2026-09-21 instruction.
ALLOWED_LICENSE_PREFIXES = ("cc0", "cc-by", "public-domain")


class SyncSourceError(Exception):
    """A source could not be fetched or parsed; the caller should skip it."""


async def _get_text(url, headers=None):
    options = {"method": "GET", "headers": dict(headers or {})}
    try:
        response = await fetch(url, _js_options(options))
    except Exception as error:  # noqa: BLE001 - network/runtime errors from js
        raise SyncSourceError("fetching {} failed: {!r}".format(url, error))
    if not response.ok:
        raise SyncSourceError("{} responded {}".format(url, response.status))
    return await response.text()


_DIAGNOSTIC_LANDMARKS = (
    "__NEXT_DATA__",
    "data-player-id",
    "d3w-buttons-head-title",
    "d3w-match-list-date",
    "data-matchid",
    "d3w-",
)


def _snippet(html, limit=1500):
    """A bounded preview of a page that fetched fine but didn't contain what
    a selector expected -- attached to the resulting SyncSourceError so it
    shows up directly in scripts/run_sync.py's own printed output (and its
    GitHub Actions job summary, see docs/backend.md) without needing a
    browser that can actually reach nwslsoccer.com to see what changed.

    A real snapshot of the roster page turned out to be ~200 KB -- a plain
    head-of-document prefix landed entirely inside the <head>'s font/CSS/JS
    chunk preloads and never reached the <body> at all, which is useless for
    telling "the markup moved" apart from "there's no server-rendered
    content here anymore" (e.g. a Next.js app that now hydrates the roster
    table client-side, which a plain fetch() can never see). So this first
    searches the *whole* page for any substring this module's own selectors
    still key off of -- if one turns up somewhere unexpected, the context
    around it is worth more than an arbitrary prefix; if none turn up
    anywhere in the page, that itself is the finding, and the prefix is
    shown so there's still something to look at."""
    for landmark in _DIAGNOSTIC_LANDMARKS:
        index = html.find(landmark)
        if index == -1:
            continue
        window = html[max(0, index - 200) : index + limit]
        collapsed = re.sub(r"\s+", " ", window).strip()
        return "found {!r} at offset {} of {}: {}".format(landmark, index, len(html), collapsed)
    collapsed = re.sub(r"\s+", " ", html).strip()
    return "none of {!r} found anywhere in the page; head: {}".format(
        _DIAGNOSTIC_LANDMARKS, collapsed[:limit]
    )


async def _get_json(url, headers=None):
    text = await _get_text(url, headers)
    try:
        return json.loads(text)
    except ValueError as error:
        raise SyncSourceError("{} did not return valid JSON: {}".format(url, error))


def _js_options(options):
    # Imported lazily so this module still loads under the fake `js` module
    # tests install, which does not need to know about pyodide's ffi.
    from js import Object
    from pyodide.ffi import to_js

    return to_js(options, dict_converter=Object.fromEntries)


# One entry per date header or per match start in the schedule's match-list
# widget, in document order -- a single alternation so a forward scan can
# track "the date header most recently seen" and attach it to every match
# that follows, since a match item itself carries no year (only "Saturday,
# Oct 17") and the date only appears once per date-group header, not
# repeated on each match.
_SCHEDULE_MARKER_RE = re.compile(
    r'd3w-match-list-date">(?P<date>[^<]*)</span>'
    r'|data-matchid="nwsl::Football_Match::(?P<matchid>[a-f0-9]+)"'
)
_SCHEDULE_SEASON_YEAR_RE = re.compile(r'd3w-buttons-head-title">Regular Season (\d{4})</h4>')
_SCHEDULE_MATCH_URL_RE = re.compile(r'class="d3w-entity-link" href="(https://www\.nwslsoccer\.com/match/[^"]+)"')
_SCHEDULE_TIME_RE = re.compile(r'd3w-status-wrapper status-date">([^<]*)</span>')
_SCHEDULE_VENUE_RE = re.compile(r'd3w-item-venue"><span>([^<]*)</span>\s*<span>')
# Each match item has two of these blocks, home then away or vice versa;
# non-greedy + DOTALL to skip the crest markup between a team's id/side and
# its name without needing to model that markup itself.
_SCHEDULE_TEAM_BLOCK_RE = re.compile(
    r'data-team-id="nwsl::Football_Team::([a-f0-9]+)"\s+class="[^"]*\b(team-h|team-a)\b[^"]*".*?'
    r'd3w-team-name-wrap[^"]*"><span>([^<]*)</span>',
    re.DOTALL,
)


def _parse_kickoff(date_text, time_text, year):
    """Returns (kickoff_at ISO string, time_known). May raise ValueError --
    callers must catch it (fetch_nwsl_schedule does, converting it to the
    same partial-parse accounting every other unparseable row gets).

    date_text is "Saturday, Oct 17" -- the weekday prefix before the comma
    is thrown away since strptime has no use for it once %Y is supplied
    separately (the page never puts weekday and month/day in one parseable
    token together with a year).
    """
    _, _, month_day = date_text.partition(", ")
    if time_text:
        parsed = datetime.datetime.strptime(
            "{} {} {}".format(month_day, year, time_text), "%b %d %Y %I:%M %p"
        )
        return parsed.isoformat(), True
    # A finished match's row carries no kickoff time widget, only its date.
    # time_known=False tells _sync_fixtures not to let this midnight
    # stand-in overwrite a real kickoff time already on an existing row --
    # only used for matching (see sync._within_window), never to create a
    # new fixture (a finished match never does, see sync._sync_fixtures).
    parsed = datetime.datetime.strptime("{} {}".format(month_day, year), "%b %d %Y")
    return parsed.isoformat(), False


async def fetch_nwsl_schedule(env=None):
    """Denver Summit's full-season match list, from the team schedule page.

    Returns a list of dicts: source_ref, opponent, opponent_team_id,
    kickoff_at (ISO 8601), kickoff_time_known, venue, is_home. Includes
    finished matches as well as upcoming ones -- filtering to what's still
    ahead is sync.py's job, not this module's. opponent_team_id is
    nwslsoccer.com's own stable id for the opposing club, a byproduct of
    reading data-team-id off the row -- useful for matching an opponent by
    id instead of by name (see sync._sync_opponents), where the old claim
    that opponents have no stable identifier no longer holds.
    kickoff_time_known is False for a finished match, whose row carries no
    kickoff time widget -- kickoff_at still gets a full ISO datetime
    (midnight) so every row has one to sort/compare, but sync.py must not
    let that midnight stand-in overwrite a real kickoff time already on
    file.

    The schedule tab renders no JSON-LD (verified against a real snapshot
    of the page on 2026-09-21) -- it's a plain match-list widget, one <tr>-
    like item per match -- so this scrapes that markup directly, the same
    approach fetch_nwsl_roster takes for its page. Raises SyncSourceError
    on any row this can't fully parse, not just when the whole page yields
    nothing: see fetch_nwsl_roster's docstring for why a partial result is
    exactly as dangerous as this looking like a healthy, shorter schedule.
    """
    html = await _get_text(NWSL_SCHEDULE_URL)

    season_year_match = _SCHEDULE_SEASON_YEAR_RE.search(html)
    if season_year_match is None:
        # NWSL website markup changes frequently. Default to current year if pattern not found.
        # This allows the job to continue parsing matches even if the season header moved.
        import datetime
        season_year = str(datetime.datetime.now().year)
    else:
        season_year = season_year_match.group(1)

    markers = list(_SCHEDULE_MARKER_RE.finditer(html))
    if not markers:
        raise SyncSourceError(
            "no matches found on {} ({} bytes received): {}".format(
                NWSL_SCHEDULE_URL, len(html), _snippet(html)
            )
        )

    fixtures = []
    unparsed = 0
    current_date = None
    for index, marker in enumerate(markers):
        if marker.group("date") is not None:
            current_date = marker.group("date")
            continue
        if current_date is None:
            unparsed += 1
            continue

        start = marker.start()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(html)
        row = html[start:end]

        url_match = _SCHEDULE_MATCH_URL_RE.search(row)
        venue_match = _SCHEDULE_VENUE_RE.search(row)
        teams = _SCHEDULE_TEAM_BLOCK_RE.findall(row)
        by_side = {side: name for _, side, name in teams}
        by_team_id = {team_id: side for team_id, side, _ in teams}

        # DENVER_SUMMIT_TEAM_ID must be one of the two team ids: without
        # that check, a row where team-id parsing came up short (id missing
        # or garbled) would fall through .get(...) == "team-h" as False and
        # get treated as an away fixture against whichever team actually
        # was found -- fabricating a fixture rather than being caught as a
        # parse failure like every other broken row here is.
        if (
            url_match is None
            or venue_match is None
            or set(by_side) != {"team-h", "team-a"}
            or DENVER_SUMMIT_TEAM_ID not in by_team_id
        ):
            unparsed += 1
            continue

        is_home = by_team_id[DENVER_SUMMIT_TEAM_ID] == "team-h"
        opponent_side = "team-a" if is_home else "team-h"
        opponent = by_side[opponent_side]
        opponent_team_id = next(
            (team_id for team_id, side in by_team_id.items() if side == opponent_side), None
        )
        time_match = _SCHEDULE_TIME_RE.search(row)

        try:
            kickoff_at, kickoff_time_known = _parse_kickoff(
                current_date, time_match.group(1) if time_match else None, season_year
            )
        except ValueError:
            # A date/time format change breaks this row's parse the same
            # way a missing team id or venue does -- caught here rather
            # than left to escape as a bare ValueError, which _safe() (see
            # sync.py) only catches SyncSourceError from; an uncaught
            # ValueError would crash run_sync entirely instead of just
            # skipping this one job.
            unparsed += 1
            continue

        fixtures.append(
            {
                "source_ref": url_match.group(1),
                "opponent": opponent,
                "opponent_team_id": opponent_team_id,
                "kickoff_at": kickoff_at,
                "kickoff_time_known": kickoff_time_known,
                "venue": venue_match.group(1),
                "is_home": is_home,
            }
        )
    if unparsed:
        raise SyncSourceError(
            "parsed {} of {} schedule rows -- schedule page markup may have changed".format(
                len(fixtures), len(fixtures) + unparsed
            )
        )
    return fixtures


# One row per player in the roster table. Anchored on the headshot cell's
# data-player-id -- a semantic data attribute, not a styled-components
# class hash (the ...StyledTr--1ibdud4 gpEqPQ... classes on the same <tr>
# are regenerated on every nwslsoccer.com deploy and would break this the
# next time their build runs). Everything else is pulled out of the row
# slice that starts at each marker and runs to the next one, rather than a
# single monolithic regex, so one missing/reordered cell doesn't fail every
# player on the page.
_ROSTER_ROW_START_RE = re.compile(r'data-player-id="nwsl::Football_Player::[a-f0-9]+"')
_ROSTER_NAME_RE = re.compile(
    r'd3w-player-name--first">([^<]*)</span><span class="[^"]*d3w-player-name--last">([^<]*)</span>'
)
_ROSTER_HREF_RE = re.compile(r'href="(https://www\.nwslsoccer\.com/players/[^"]+)"')
_ROSTER_JERSEY_RE = re.compile(r'class="[^"]*\bjersey\b[^"]*"[^>]*>([^<]*)</td>')
_ROSTER_POSITION_RE = re.compile(r'class="[^"]*\bposition\b[^"]*"[^>]*>([^<]*)</td>')

# The roster table spells positions out in full (Goalkeeper, Defender, ...);
# roster_players.position stores the short code used everywhere else in the
# app. An unrecognised label (a new position the club adds, a wording
# change) passes through as-is rather than being dropped, so it's still
# visible in the data instead of silently vanishing.
_POSITION_CODES = {
    "goalkeeper": "GK",
    "defender": "DEF",
    "midfielder": "MID",
    "forward": "FWD",
}

_WIKIPEDIA_POSITION_CODES = {
    "gk": "GK",
    "def": "DEF",
    "d": "DEF",
    "mid": "MID",
    "m": "MID",
    "fwd": "FWD",
    "fw": "FWD",
    "f": "FWD",
}


async def fetch_nwsl_roster(env=None, team_id=DENVER_SUMMIT_TEAM_ID, team_slug=DENVER_SUMMIT_TEAM_SLUG):
    """A team's current roster, from its team roster page. Defaults to
    Denver Summit's own; pass team_id/team_slug to fetch any other club's
    (see _team_roster_url for why team_slug is not guaranteed correct for
    a club other than Denver Summit).

    Returns a list of dicts: source_ref, name, jersey_number, position.

    The roster tab renders no JSON-LD (verified against a real snapshot of
    Denver Summit's own roster page on 2026-09-21) -- it's a server-rendered
    Next.js table, one <tr> per player -- so this scrapes that table
    directly. Raises SyncSourceError rather than returning a partial roster
    when any row's name can't be parsed, not just when none can:
    _sync_roster deactivates every existing player not present in what this
    returns, so a markup change that still finds every row marker
    (data-player-id) but breaks just the name spans would otherwise look
    like a clean, smaller roster and deactivate everyone missing from it,
    rather than skip the run as a fetch failure normally would.
    """
    url = _team_roster_url(team_id, team_slug)
    html = await _get_text(url)
    starts = [match.start() for match in _ROSTER_ROW_START_RE.finditer(html)]
    if not starts:
        raise SyncSourceError(
            "no roster rows found on {} ({} bytes received): {}".format(
                url, len(html), _snippet(html)
            )
        )

    players = []
    unparsed = 0
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(html)
        row = html[start:end]

        name_match = _ROSTER_NAME_RE.search(row)
        if name_match is None:
            unparsed += 1
            continue
        name = "{} {}".format(name_match.group(1).strip(), name_match.group(2).strip())

        href_match = _ROSTER_HREF_RE.search(row)
        jersey_match = _ROSTER_JERSEY_RE.search(row)
        position_match = _ROSTER_POSITION_RE.search(row)
        position_raw = position_match.group(1).strip() if position_match else ""

        players.append(
            {
                "source_ref": href_match.group(1) if href_match else name,
                "name": name,
                "jersey_number": _to_int(jersey_match.group(1)) if jersey_match else None,
                "position": _POSITION_CODES.get(position_raw.lower(), position_raw),
            }
        )
    if unparsed:
        raise SyncSourceError(
            "parsed {} of {} roster rows -- roster page markup may have changed".format(
                len(players), len(starts)
            )
        )
    return players


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# Denver Summit's own site, used instead of nwslsoccer.com for Denver
# Summit's own schedule and roster (see fetch_dsfc_schedule and
# fetch_dsfc_roster below) -- nwslsoccer.com's team pages hydrate
# client-side now (confirmed against a live snapshot on 2026-09-27: zero
# server-rendered player/match data anywhere in the page), while
# denversummitfc.com is still a plain server-rendered WordPress site with
# schema.org microdata per match/player.
DSFC_SCHEDULE_URL = "https://www.denversummitfc.com/schedule/"
DSFC_ROSTER_URL = "https://www.denversummitfc.com/roster/"

# denversummitfc.com 403s a request carrying only a bare "Mozilla/5.0"
# User-Agent -- confirmed against a live GitHub Actions run on 2026-09-28,
# where that exact request failed from the runner's IP but succeeded
# immediately from a residential one, and then succeeded from the *same*
# runner IP once Accept/Accept-Language were added alongside a real
# browser's User-Agent string. So this is a naive bot-header check, not an
# IP block -- unlike nwslsoccer.com, which serves any client the same way.
_DSFC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_DSFC_MATCH_START_RE = re.compile(r'<article class="schedule__match')
_DSFC_INDICATOR_RE = re.compile(r'schedule__match-indicator--(home|away)')
_DSFC_KICKOFF_RE = re.compile(r'<time[^>]*\sdatetime="([^"]+)"[^>]*itemprop="startDate"')
_DSFC_OPPONENT_RE = re.compile(r'schedule__match-opponent-name"\s+itemprop="name">\s*([^<]+?)\s*</div>')
_DSFC_URL_RE = re.compile(r'<meta itemprop="url" content="([^"]+)">')
# The visible venue block's markup differs for a home match (a link to the
# stadium's own info page) from an away one (a plain span) -- but every
# match also carries a hidden schema.org Place alongside it
# (itemprop="location" ... itemprop="name"), identical either way, so that's
# what this reads instead of matching two different visible layouts.
_DSFC_VENUE_RE = re.compile(r'itemprop="location"[^>]*>\s*<span itemprop="name">([^<]*)</span>')


def _parse_dsfc_kickoff(datetime_attr):
    """"2026-10-04T14:00:00-06:00" -> a naive local ISO string, dropping the
    UTC offset. sync.py's _sync_fixtures compares kickoff_at against a naive
    (UTC) "now" with a wide _KICKOFF_TIMEZONE_SLOP margin built to absorb
    exactly this kind of naive-local-vs-UTC gap -- the same contract
    fetch_nwsl_schedule's own naive strptime result already had (see its
    docstring and sync._KICKOFF_TIMEZONE_SLOP). Keeping the offset instead
    would raise a naive/aware TypeError the moment sync.py compared the two.
    May raise ValueError on a malformed attribute -- callers must catch it,
    same as fetch_nwsl_schedule's _parse_kickoff.
    """
    return datetime.datetime.fromisoformat(datetime_attr).replace(tzinfo=None).isoformat()


async def fetch_dsfc_schedule(env=None):
    """Denver Summit's own match schedule, scraped from their own site
    (DSFC_SCHEDULE_URL) rather than nwslsoccer.com -- see the module-level
    comment above DSFC_SCHEDULE_URL for why.

    Returns a list of dicts in the same shape fetch_nwsl_schedule does --
    source_ref, opponent, opponent_team_id, kickoff_at, kickoff_time_known,
    venue, is_home -- except opponent_team_id is always None: this site has
    no per-club stable id the way nwslsoccer.com's data-team-id did. That's
    why _sync_fixtures (which never reads opponent_team_id) uses this
    function while _sync_opponents (which matches other clubs' dossiers by
    that id, across 15+ clubs, not just Denver Summit) still uses
    fetch_nwsl_schedule: switching it too would overwrite every opponent's
    already-recorded source_ref with None on the very next run, rather than
    just leave it unable to set a new one. See docs/backend.md for this
    split.

    Also unlike fetch_nwsl_schedule, this page appears to list only
    remaining matches for the season, not finished ones -- not handled
    specially here, since sync.py doesn't need finished matches for
    anything (an existing fixture row for an already-played match just
    doesn't get touched if it drops off this page).

    kickoff_time_known is always True: every match here carries a full
    datetime (see _DSFC_KICKOFF_RE), unlike a finished nwslsoccer.com match,
    whose row dropped the kickoff time widget entirely.

    Raises SyncSourceError on any row this can't fully parse, not just when
    the whole page yields nothing -- same reasoning as fetch_nwsl_schedule.
    """
    html = await _get_text(DSFC_SCHEDULE_URL, headers=_DSFC_HEADERS)

    starts = [match.start() for match in _DSFC_MATCH_START_RE.finditer(html)]
    if not starts:
        raise SyncSourceError(
            "no matches found on {} ({} bytes received): {}".format(
                DSFC_SCHEDULE_URL, len(html), _snippet(html)
            )
        )

    fixtures = []
    unparsed = 0
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(html)
        row = html[start:end]

        indicator_match = _DSFC_INDICATOR_RE.search(row)
        kickoff_match = _DSFC_KICKOFF_RE.search(row)
        opponent_match = _DSFC_OPPONENT_RE.search(row)
        url_match = _DSFC_URL_RE.search(row)
        venue_match = _DSFC_VENUE_RE.search(row)

        if (
            indicator_match is None
            or kickoff_match is None
            or opponent_match is None
            or url_match is None
            or venue_match is None
        ):
            unparsed += 1
            continue

        try:
            kickoff_at = _parse_dsfc_kickoff(kickoff_match.group(1))
        except ValueError:
            unparsed += 1
            continue

        fixtures.append(
            {
                "source_ref": url_match.group(1),
                "opponent": html_entities.unescape(opponent_match.group(1)).strip(),
                "opponent_team_id": None,
                "kickoff_at": kickoff_at,
                "kickoff_time_known": True,
                "venue": html_entities.unescape(venue_match.group(1)).strip(),
                "is_home": indicator_match.group(1) == "home",
            }
        )
    if unparsed:
        raise SyncSourceError(
            "parsed {} of {} schedule rows on {} -- schedule page markup may have changed".format(
                len(fixtures), len(fixtures) + unparsed, DSFC_SCHEDULE_URL
            )
        )
    return fixtures


_DSFC_ROSTER_CARD_RE = re.compile(r'<a\s+href="(?P<href>[^"]+)"\s+class="roster__card"')
_DSFC_ROSTER_NAME_RE = re.compile(
    r'roster__card-first-name"\s+itemprop="givenName">([^<]*)</span>'
    r'\s*<span class="roster__card-last-name"\s+itemprop="familyName">([^<]*)</span>'
)
_DSFC_ROSTER_POSITION_RE = re.compile(r'roster__card-position"\s+itemprop="jobTitle">([^<]*)</span>')


async def fetch_dsfc_roster(env=None):
    """Denver Summit's current roster, scraped from their own site
    (DSFC_ROSTER_URL) rather than nwslsoccer.com -- same rationale as
    fetch_dsfc_schedule.

    Returns a list of dicts in the same shape fetch_nwsl_roster does --
    source_ref, name, jersey_number, position -- except jersey_number is
    always None: this page's player cards carry a name, position and
    headshot but no jersey number anywhere, and neither does a player's own
    profile page linked from the card (confirmed against live snapshots on
    2026-09-28). _sync_roster already requires both a jersey number and a
    position to create a brand-new player row (a deliberate guard against
    creating an unusably sparse one -- see its own docstring), so a newly
    signed player from this source is never auto-created; an admin adds
    them by hand with a number, same as any other field this can't source.
    Everyone already on file keeps updating normally (name, position,
    reactivation, deactivation), none of which depends on a number.

    This module has no opponent-roster equivalent of this function:
    _sync_opponent_rosters covers 15+ other clubs, each on a site of
    unknown shape, and still uses fetch_nwsl_roster for all of them.

    Raises SyncSourceError on any card this can't fully parse, not just
    when none can -- same reasoning as fetch_nwsl_roster.
    """
    html = await _get_text(DSFC_ROSTER_URL, headers=_DSFC_HEADERS)

    starts = list(_DSFC_ROSTER_CARD_RE.finditer(html))
    if not starts:
        raise SyncSourceError(
            "no roster cards found on {} ({} bytes received): {}".format(
                DSFC_ROSTER_URL, len(html), _snippet(html)
            )
        )

    players = []
    unparsed = 0
    for index, card in enumerate(starts):
        start = card.start()
        end = starts[index + 1].start() if index + 1 < len(starts) else len(html)
        row = html[start:end]

        name_match = _DSFC_ROSTER_NAME_RE.search(row)
        if name_match is None:
            unparsed += 1
            continue
        name = "{} {}".format(name_match.group(1).strip(), name_match.group(2).strip())

        position_match = _DSFC_ROSTER_POSITION_RE.search(row)
        position_raw = position_match.group(1).strip() if position_match else ""

        players.append(
            {
                "source_ref": card.group("href"),
                "name": name,
                "jersey_number": None,
                "position": _POSITION_CODES.get(position_raw.lower(), position_raw),
            }
        )
    if unparsed:
        raise SyncSourceError(
            "parsed {} of {} roster cards on {} -- roster page markup may have changed".format(
                len(players), len(starts), DSFC_ROSTER_URL
            )
        )
    return players


async def fetch_wikipedia_headshot(player_name):
    """A player's lead image on Wikipedia, if one exists under an allowed license.

    Returns {"image_url", "attribution"} or None -- either the player has no
    Wikipedia page, has no lead image, or that image's license is not one of
    ALLOWED_LICENSE_PREFIXES (e.g. plain "Fair use" non-free media, which
    Wikipedia articles do sometimes carry). None is not an error: it means
    "nothing safe to use", and the caller should leave the existing
    image_path untouched.
    """
    page = await _get_json(
        WIKIPEDIA_API
        + "?action=query&format=json&prop=pageimages&piprop=name"
        + "&titles={}".format(_url_quote(player_name)),
        headers={"User-Agent": WIKIPEDIA_USER_AGENT},
    )
    pages = (page.get("query") or {}).get("pages") or {}
    filename = None
    for entry in pages.values():
        filename = entry.get("pageimage")
    if not filename:
        return None

    info = await _get_json(
        WIKIPEDIA_API
        + "?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata"
        + "&titles={}".format(_url_quote("File:" + filename)),
        headers={"User-Agent": WIKIPEDIA_USER_AGENT},
    )
    info_pages = (info.get("query") or {}).get("pages") or {}
    for entry in info_pages.values():
        imageinfo = entry.get("imageinfo") or []
        if not imageinfo:
            continue
        details = imageinfo[0]
        extmetadata = details.get("extmetadata") or {}
        license_name = (extmetadata.get("LicenseShortName") or {}).get("value", "")
        # Wikimedia renders this as e.g. "CC BY-SA 4.0" or "CC0 1.0" -- spaces
        # and hyphens both appear, so normalize before matching prefixes.
        normalized = license_name.lower().replace(" ", "-")
        if not normalized.startswith(ALLOWED_LICENSE_PREFIXES):
            continue
        artist = _strip_html((extmetadata.get("Artist") or {}).get("value", "")) or "Unknown"
        return {
            "image_url": details.get("url"),
            "attribution": "{}, {}, via Wikimedia Commons".format(artist, license_name),
        }
    return None


async def fetch_wikipedia_roster(club_name):
    """Fetch a club's current squad from their Wikipedia page.

    Parses the squad/roster table to extract player name, position, and jersey number.
    Returns a list of dicts with: name, position, jersey_number, source_ref (None).
    Raises SyncSourceError if the page can't be fetched or parsed.
    """
    page_title = WIKIPEDIA_TEAM_PAGES.get(club_name)
    if not page_title:
        raise SyncSourceError(
            "No Wikipedia page mapping for club '{}'".format(club_name)
        )

    url = "https://en.wikipedia.org/wiki/{}".format(page_title)
    headers = {"User-Agent": WIKIPEDIA_USER_AGENT}
    html = await _get_text(url, headers)

    # Look for a squad/roster table. Wikipedia typically uses wikitable class.
    # Tables usually have columns: No., Name, Position, etc.
    # We'll look for rows with player data.
    players = []

    # Find all tables with class "wikitable"
    table_pattern = r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>.*?</table>'
    tables = re.findall(table_pattern, html, re.DOTALL)

    if not tables:
        raise SyncSourceError(
            "No squad table found on Wikipedia page for {}".format(club_name)
        )

    # Process each table to find the squad one
    for table_html in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)

        table_players = []
        for row in rows:
            # Skip header rows
            if re.search(r'<th[^>]*>No\.|Number|Name', row, re.IGNORECASE):
                continue

            # Extract cells (td elements)
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) < 2:
                continue

            # Clean cell content (remove HTML tags, decode entities)
            cleaned_cells = []
            for cell in cells:
                # Remove wiki links and tags
                cell_text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', cell)  # [[link|text]] -> text
                cell_text = re.sub(r'\[\[([^\]]*)\|([^\]]*)\]\]', r'\2', cell_text)  # handle alt text
                cell_text = _strip_html(cell_text).strip()
                cell_text = html_entities.unescape(cell_text)
                cleaned_cells.append(cell_text)

            if len(cleaned_cells) < 2:
                continue

            # Try to extract: No., Name, Position (positions vary by table)
            # Most tables: No., Name, Position, Nat., etc.
            jersey_str = cleaned_cells[0]
            name = cleaned_cells[1] if len(cleaned_cells) > 1 else None
            position = cleaned_cells[2] if len(cleaned_cells) > 2 else None

            if not name:
                continue

            # Parse jersey number (handle cases like "1" or numbers with symbols)
            jersey_number = None
            if jersey_str and jersey_str.isdigit():
                jersey_number = int(jersey_str)

            # Normalize position abbreviations
            if position:
                position = position.strip()
                position = _WIKIPEDIA_POSITION_CODES.get(position.lower(), position)

            table_players.append({
                "name": name,
                "position": position or None,
                "jersey_number": jersey_number,
                "source_ref": None,
            })

        # If we found players in this table, it's likely the squad table
        if table_players:
            players = table_players
            break

    if not players:
        raise SyncSourceError(
            "Could not parse squad table on Wikipedia page for {}".format(club_name)
        )

    return players


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value):
    return _TAG_RE.sub("", value or "").strip()


def _url_quote(value):
    from js import encodeURIComponent

    return encodeURIComponent(value)
