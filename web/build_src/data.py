"""Placeholder syndicate and fixture data, plus the real Denver Summit FC squad.

Syndicate/fixture data (members, seats, ledger) is still invented -- ported
from the original src/data/mock.js. SQUAD is transcribed from the official
roster at nwslsoccer.com/teams/cbfcacbef5bc4a278442c00926ac9ebc/denver-summit-fc/roster
(2026-09-21 snapshot): jersey number, position and nationality only -- the
site does not publish season stats or scouting-style bios, so `stats` and
`note` stay factual rather than invented. No headshots are stored here;
`photo_slot()` stays an empty drop target, and any photo added later should
come from a source with a redistribution licence (e.g. Wikimedia Commons)
rather than the NWSL site's own images, which is what src/sync_sources.py
already restricts itself to via ALLOWED_LICENSE_PREFIXES.
"""
from __future__ import annotations

ME = "u_you"

MEMBERS = {
    "u_you":   {"id": "u_you",   "name": "You",   "initials": "YO", "colour": "#134E48"},
    "u_jason": {"id": "u_jason", "name": "Jason",  "initials": "JM", "colour": "#1D6960"},
    "u_sarah": {"id": "u_sarah", "name": "Sarah",  "initials": "SK", "colour": "#C84B31"},
    "u_alice": {"id": "u_alice", "name": "Alice",  "initials": "AR", "colour": "#8A6D1F"},
    "u_bob":   {"id": "u_bob",   "name": "Bob",    "initials": "BT", "colour": "#3F5C58"},
}

SYNDICATES = [
    {
        "id": "syn_north", "name": "North Stand Syndicate",
        "seats": [{"number": 3, "section": "114", "row": "8"}, {"number": 4, "section": "114", "row": "8"}],
        "member_ids": ["u_you", "u_jason", "u_sarah", "u_alice", "u_bob"],
        "invited_by": "Jason M.", "holds": "2 seats · Sec 114, Row 8",
    },
    {
        "id": "syn_rail", "name": "Rail Line Collective",
        "seats": [{"number": 11, "section": "102", "row": "3"}],
        "member_ids": ["u_you", "u_bob"],
        "invited_by": "Bob T.", "holds": "1 seat · Sec 102, Row 3",
    },
]

# Tickets are tracked by year. Only the current season is real -- a
# `groups` row is a single season's package, with no year-over-year link to
# any other one, so there is no real "season history" to show yet (see
# web/src/app.js's paintRealSyndicateDetail). The second, prior-season entry
# this used to carry was demo flavor only and never corresponded to
# anything a real syndicate could have.
SEASONS = [
    {"year": 2026, "label": "2026 Season", "package_cents": 248000, "current": True},
]

# Weighted price distribution: a rivalry weekend match carries more of the
# package than a standard midweek one.
TIERS = {
    "rivalry":  {"label": "Rivalry", "weight": 1.6},
    "standard": {"label": "Standard", "weight": 1.0},
    "cup":      {"label": "Cup", "weight": 1.3},
}


# Denver Summit's real remaining 2026 home schedule (transcribed from the
# official schedule at nwslsoccer.com/teams/cbfcacbef5bc4a278442c00926ac9ebc/
# denver-summit-fc/schedule, 2026-09-22 snapshot -- src/sync_sources.py
# fetch_nwsl_schedule reads the same page for the live app). Only two home
# matches are left this season; every away leg is left out on purpose --
# this app tracks a season-ticket package at the home venue, and there is
# no seat package to sell for a match played somewhere else. Kickoff,
# opponent and venue are real; which syndicate member holds which seat, and
# what it cost, are still invented -- there is no public source for either,
# and both are the whole point of the demo.
FIXTURES = [
    {"id": "fx_acf", "season": 2026, "opponent": "Angel City", "short": "Angel City",
     "kickoff": "2026-10-17T18:45:00", "venue": "Centennial Stadium", "tier": "rivalry", "value_cents": 18000,
     "seats": [{"number": 3, "holder": "u_you", "status": "confirmed"},
               {"number": 4, "holder": None, "status": "listed", "ask_cents": 9500}]},
    {"id": "fx_rl", "season": 2026, "opponent": "Racing Louisville", "short": "Louisville",
     "kickoff": "2026-10-24T16:30:00", "venue": "Centennial Stadium", "tier": "standard", "value_cents": 11000,
     "seats": [{"number": 3, "holder": "u_jason", "status": "confirmed"},
               {"number": 4, "holder": None, "status": "bench", "bench_note_id": "bn_rl"}]},
]

# Thread on a released seat: a note plus replies, not a full chat.
BENCH_NOTES = [
    {"id": "bn_rl", "fixture_id": "fx_rl", "seat_number": 4, "author_id": "u_sarah",
     "posted_at": "2026-09-19T09:12:00", "cost_path": "repay", "amount_cents": 5500,
     "body": "Out of town for the Louisville match — seat 4 is free if anyone wants it.",
     "replies": [{"id": "r1", "author_id": "u_jason", "at": "2026-09-19T09:40:00",
                  "body": "We'll miss you — I'll ask my sister."}]},
]

QUICK_REPLIES = ["I'll take them", "We'll miss you", "Anyone else in?"]

# Simplified debts: the ledger nets the circle down to the fewest transfers.
# Who actually paid what and who owes whom is invented, same as which member
# holds which seat above -- there is no real transaction history behind this
# demo syndicate. Unlike the seat/price mocks, a specific per-member debt is
# not left invented here: each member's paid/owed is their even share of the
# package (which *is* real, from SEASONS), so debts nets to empty rather
# than fabricating who owes whom and how much.
LEDGER = {
    2026: {
        "package_cents": 248000,
        "paid": {k: 49600 for k in MEMBERS},
        "owed": {k: 49600 for k in MEMBERS},
        "debts": [],
    },
}

SETTLE_APPS = [
    {"id": "venmo", "name": "Venmo",
     "link": lambda amount, memo: f"https://venmo.com/?txn=pay&amount={amount}&note={_urlenc(memo)}"},
    {"id": "cashapp", "name": "Cash App", "link": lambda amount, memo: "https://cash.app/$/summitbasecamp"},
    {"id": "zelle", "name": "Zelle", "link": lambda amount, memo: "https://www.zellepay.com/"},
]


def _urlenc(text):
    from urllib.parse import quote
    return quote(text)


# ---------- Home Team (the Locker Room) ----------
# The real, verified roster page src/sync_sources.py reads (see
# NWSL_ROSTER_URL there) -- used as the "Club bio" link for every Home Team
# player, replacing a guessed denversummitfc.com URL that was never
# confirmed to be real.
DENVER_ROSTER_URL = "https://www.nwslsoccer.com/teams/cbfcacbef5bc4a278442c00926ac9ebc/denver-summit-fc/roster"

SQUAD = [
    {"id": "p1", "num": 1, "name": "Abby Smith", "pos": "GK",
     "stats": [("Position", "Goalkeeper"), ("Nationality", "USA")],
     "note": "Denver Summit FC goalkeeper. See the club's official roster for 2026 season statistics."},
    {"id": "p2", "num": 17, "name": "Jordan Nytes", "pos": "GK",
     "stats": [("Position", "Goalkeeper"), ("Nationality", "USA")],
     "note": "Denver Summit FC goalkeeper. See the club's official roster for 2026 season statistics."},
    {"id": "p3", "num": 36, "name": "Kat Asman", "pos": "GK",
     "stats": [("Position", "Goalkeeper"), ("Nationality", "USA")],
     "note": "Denver Summit FC goalkeeper. See the club's official roster for 2026 season statistics."},
    {"id": "p4", "num": 2, "name": "Megan Reid", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "CAN")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p5", "num": 3, "name": "Kaleigh Kurtz", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "USA")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p6", "num": 4, "name": "Natalie Means", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "USA")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p7", "num": 7, "name": "Ayo Oke", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "USA")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p8", "num": 13, "name": "Gemma Bonner", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "ENG")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p9", "num": 16, "name": "Carson Pickett", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "USA")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p10", "num": 23, "name": "Eva Gaetino", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "USA")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p11", "num": 30, "name": "Camryn Biegalski", "pos": "DEF",
     "stats": [("Position", "Defender"), ("Nationality", "USA")],
     "note": "Denver Summit FC defender. See the club's official roster for 2026 season statistics."},
    {"id": "p12", "num": 5, "name": "Devin Lynch", "pos": "MID",
     "stats": [("Position", "Midfielder"), ("Nationality", "USA")],
     "note": "Denver Summit FC midfielder. See the club's official roster for 2026 season statistics."},
    {"id": "p13", "num": 8, "name": "Emma Regan", "pos": "MID",
     "stats": [("Position", "Midfielder"), ("Nationality", "CAN")],
     "note": "Denver Summit FC midfielder. See the club's official roster for 2026 season statistics."},
    {"id": "p14", "num": 10, "name": "Lindsey Heaps", "pos": "MID",
     "stats": [("Position", "Midfielder"), ("Nationality", "USA")],
     "note": "Denver Summit FC midfielder. See the club's official roster for 2026 season statistics."},
    {"id": "p15", "num": 14, "name": "Yuna McCormack", "pos": "MID",
     "stats": [("Position", "Midfielder"), ("Nationality", "USA")],
     "note": "Denver Summit FC midfielder. See the club's official roster for 2026 season statistics."},
    {"id": "p16", "num": 15, "name": "Jordan Baggett", "pos": "MID",
     "stats": [("Position", "Midfielder"), ("Nationality", "USA")],
     "note": "Denver Summit FC midfielder. See the club's official roster for 2026 season statistics."},
    {"id": "p17", "num": 24, "name": "Delanie Sheehan", "pos": "MID",
     "stats": [("Position", "Midfielder"), ("Nationality", "USA")],
     "note": "Denver Summit FC midfielder. See the club's official roster for 2026 season statistics."},
    {"id": "p18", "num": 34, "name": "Meg Boade", "pos": "MID",
     "stats": [("Position", "Midfielder"), ("Nationality", "USA")],
     "note": "Denver Summit FC midfielder. See the club's official roster for 2026 season statistics."},
    {"id": "p19", "num": 6, "name": "Janine Sonis", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "CAN")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p20", "num": 9, "name": "Yazmeen Ryan", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "USA")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p21", "num": 11, "name": "Ally Brazier", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "USA")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p22", "num": 12, "name": "Jasmine Aikey", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "USA")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p23", "num": 18, "name": "Yuzuki Yamamoto", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "JPN")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p24", "num": 25, "name": "Melissa Kössler", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "DEU")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p25", "num": 26, "name": "Natasha Flint", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "ENG")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p26", "num": 33, "name": "Olivia Thomas", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "USA")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p27", "num": 79, "name": "Nahikari García", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "ESP")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
    {"id": "p28", "num": None, "name": "Faith Webber", "pos": "FWD",
     "stats": [("Position", "Forward"), ("Nationality", "USA")],
     "note": "Denver Summit FC forward. See the club's official roster for 2026 season statistics."},
]

POSITIONS = ["Whole squad", "GK", "DEF", "MID", "FWD"]

# ---------- Visitors (the visiting club's dressing room) ----------
# Denver Summit's five remaining 2026 opponents (both home and away legs
# against every other club have already happened, except these five), from
# the same schedule snapshot FIXTURES above comes from. `recent_result` is
# the real final score from the meeting already played this season;
# `match_url` is that match's own real nwslsoccer.com page, used as the
# "Latest meeting" link on each player card. No invented scouting prose
# (form, tactical shape, "danger player" tags) and no invented players --
# none of that is published anywhere to verify, so both are left out rather
# than guessed. Real per-club rosters exist in D1 (opponent_players), kept
# current by src/sync.py's _sync_opponent_rosters using the same verified
# roster-page URLs for all 15 NWSL clubs (see seed/opponents_seed.sql) --
# this static build just doesn't read from D1 at all yet, the same
# frontend/backend gap noted for the roster and schedule.
OPPONENTS = [
    {"id": "op_kc", "club": "Kansas City Current", "chip": "Kansas City Current · 9/26",
     "home_date": "7/3", "away_date": "9/26", "away_venue": "CPKC Stadium",
     "recent_result": "Denver lost 0–3 at home on 7/3 — the only meeting so far this season.",
     "match_url": "https://www.nwslsoccer.com/match/ec7d28b04d3d4a9ca6d024c41a37702f/denver-summit-vs-kansas-city-current",
     "players": []},
    {"id": "op_chi", "club": "Chicago Stars", "chip": "Chicago Stars · 10/4",
     "home_date": "8/29", "away_date": "10/4", "away_venue": "Northwestern Medicine Field at Martin Stadium",
     "recent_result": "Denver won 6–1 at home on 8/29 — the only meeting so far this season.",
     "match_url": "https://www.nwslsoccer.com/match/2f72ffec33184cf09348bbc1481856a5/denver-summit-vs-chicago-stars",
     "players": []},
    {"id": "op_acf", "club": "Angel City", "chip": "Angel City · 10/17",
     "home_date": "10/17", "away_date": "9/11", "away_venue": "BMO Stadium",
     "recent_result": "Denver drew 3–3 away on 9/11 — the only meeting so far this season.",
     "match_url": "https://www.nwslsoccer.com/match/6917097b9b664560a221408c048d4257/angel-city-vs-denver-summit",
     "players": []},
    {"id": "op_rl", "club": "Racing Louisville", "chip": "Racing Louisville · 10/24",
     "home_date": "10/24", "away_date": "5/29", "away_venue": "Lynn Family Stadium",
     "recent_result": "Denver won 1–0 away on 5/29 — the only meeting so far this season.",
     "match_url": "https://www.nwslsoccer.com/match/3bd415d8b50c4025819575e1942de7db/racing-louisville-vs-denver-summit",
     "players": []},
    {"id": "op_ncc", "club": "North Carolina Courage", "chip": "North Carolina Courage · 11/1",
     "home_date": "8/5", "away_date": "11/1", "away_venue": "First Horizon Stadium at WakeMed Soccer Park",
     "recent_result": "Denver lost 0–2 at home on 8/5 — the only meeting so far this season.",
     "match_url": "https://www.nwslsoccer.com/match/b8beb36b96a94acd8f35d2cc14d7e7c1/denver-summit-vs-north-carolina-courage",
     "players": []},
]

# ---------- Summit Touchline Notes ----------
TOUCHLINE_NOTES = [
    {"kind": "player", "eyebrow": "Key player to watch", "num": 9, "name": "Yazmeen Ryan",
     "pos": "Forward · Denver Summit FC",
     "body": "Wears the 9 up top for Summit this season. See the Locker Room tab for the full squad."},
    {"kind": "tactics", "eyebrow": "Up next", "name": "Kansas City Current, on the road",
     "body": "Denver lost 0–3 to them at home back on 7/3 — the rematch is 9/26, away at CPKC Stadium. See the Visitors tab for the full dossier."},
    {"kind": "trivia", "eyebrow": "Tap to reveal", "question": "What home ground does Denver Summit play at?",
     "answer": "Centennial Stadium — out in Centennial, Colorado, in the thin air the away sign likes to remind visitors about."},
]
