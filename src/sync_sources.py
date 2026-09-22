"""Fetching and parsing for the roster/fixture/headshot sync job.

Kept separate from sync.py's diff-and-write logic so each source's endpoint,
selectors and licensing rules can be fixed or swapped without touching how a
parsed result gets reconciled against the database. Every function here
returns plain dicts/lists -- no D1, no js.Response objects past this module.
"""

import datetime
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
WIKIPEDIA_USER_AGENT = "SquadSeatsSyncBot/1.0 (https://github.com/CreativeMaladjustment/summit-hearth-and-bench)"

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
        raise SyncSourceError("no season year found on the schedule page")
    season_year = season_year_match.group(1)

    markers = list(_SCHEDULE_MARKER_RE.finditer(html))
    if not markers:
        raise SyncSourceError("no matches found on the schedule page")

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
    html = await _get_text(_team_roster_url(team_id, team_slug))
    starts = [match.start() for match in _ROSTER_ROW_START_RE.finditer(html)]
    if not starts:
        raise SyncSourceError("no roster rows found on the roster page")

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


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value):
    return _TAG_RE.sub("", value or "").strip()


def _url_quote(value):
    from js import encodeURIComponent

    return encodeURIComponent(value)
