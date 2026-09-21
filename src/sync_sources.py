"""Fetching and parsing for the roster/fixture/headshot sync job.

Kept separate from sync.py's diff-and-write logic so each source's endpoint,
selectors and licensing rules can be fixed or swapped without touching how a
parsed result gets reconciled against the database. Every function here
returns plain dicts/lists -- no D1, no js.Response objects past this module.
"""

import json
import re

from js import fetch

# Denver Summit's team page on nwslsoccer.com. The schedule tab renders a
# per-match schema.org SportsEvent block (JSON-LD) for each fixture; that is
# the only structured data the page exposes, so this scrapes that block
# rather than the surrounding HTML. If nwslsoccer.com changes its markup and
# stops emitting JSON-LD, `_extract_json_ld` below returns an empty list and
# the sync logs a warning instead of failing the whole job -- selectors here
# are expected to need revisiting; see docs/requirements.md.
#
# The roster tab (fetch_nwsl_roster below) is different: verified against a
# real snapshot of the page on 2026-09-21, it renders no JSON-LD at all --
# it's a plain Next.js table -- so that one scrapes the table markup
# directly instead. The slug also used to be missing "-fc"
# (.../denver-summit/... 404s; the real path is .../denver-summit-fc/...).
NWSL_TEAM_SLUG = "cbfcacbef5bc4a278442c00926ac9ebc/denver-summit-fc"
NWSL_SCHEDULE_URL = "https://www.nwslsoccer.com/teams/{}/schedule".format(NWSL_TEAM_SLUG)
NWSL_ROSTER_URL = "https://www.nwslsoccer.com/teams/{}/roster".format(NWSL_TEAM_SLUG)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
# A descriptive User-Agent, as Wikimedia's API etiquette asks for.
WIKIPEDIA_USER_AGENT = "SquadSeatsSyncBot/1.0 (https://github.com/CreativeMaladjustment/summit-hearth-and-bench)"

# Licenses permissive enough to redistribute an image without further
# clearance. Anything else (including plain "Fair use") is skipped -- public
# data only, nothing copyrighted, per floutenvy's 2026-09-21 instruction.
ALLOWED_LICENSE_PREFIXES = ("cc0", "cc-by", "public-domain")

_JSON_LD_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


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


def _extract_json_ld(html):
    blocks = []
    for raw in _JSON_LD_RE.findall(html):
        try:
            parsed = json.loads(raw.strip())
        except ValueError:
            continue
        blocks.extend(parsed if isinstance(parsed, list) else [parsed])
    return blocks


async def fetch_nwsl_schedule(env=None):
    """Denver Summit's upcoming/recent fixtures, from the team schedule page.

    Returns a list of dicts: source_ref, opponent, kickoff_at (ISO 8601),
    venue, is_home.
    """
    html = await _get_text(NWSL_SCHEDULE_URL)
    fixtures = []
    for block in _extract_json_ld(html):
        if block.get("@type") != "SportsEvent":
            continue
        home = (block.get("homeTeam") or {}).get("name", "")
        away = (block.get("awayTeam") or {}).get("name", "")
        is_home = "denver" in home.lower() or "summit" in home.lower()
        opponent = away if is_home else home
        if not opponent or not block.get("startDate"):
            continue
        venue = (block.get("location") or {}).get("name", "")
        fixtures.append(
            {
                "source_ref": block.get("url") or "{}-{}".format(opponent, block["startDate"]),
                "opponent": opponent,
                "kickoff_at": block["startDate"],
                "venue": venue,
                "is_home": is_home,
            }
        )
    if not fixtures:
        raise SyncSourceError("no SportsEvent blocks found on the schedule page")
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


async def fetch_nwsl_roster(env=None):
    """Denver Summit's current roster, from the team roster page.

    Returns a list of dicts: source_ref, name, jersey_number, position.

    The roster tab renders no JSON-LD (verified against a real snapshot of
    the page on 2026-09-21) -- it's a server-rendered Next.js table, one
    <tr> per player -- so this scrapes that table directly. Falls back to
    raising SyncSourceError when no player rows are found at all, so a
    markup change degrades to a skipped roster sync rather than corrupting
    existing rows.
    """
    html = await _get_text(NWSL_ROSTER_URL)
    starts = [match.start() for match in _ROSTER_ROW_START_RE.finditer(html)]
    players = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(html)
        row = html[start:end]

        name_match = _ROSTER_NAME_RE.search(row)
        if name_match is None:
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
    if not players:
        raise SyncSourceError("no roster rows found on the roster page")
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
