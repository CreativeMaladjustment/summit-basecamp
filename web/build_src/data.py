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

# Tickets are tracked by year, from the first season to the next.
SEASONS = [
    {"year": 2026, "label": "2026 Season", "package_cents": 248000, "current": True},
    {"year": 2025, "label": "2025 Season", "package_cents": 231000, "current": False},
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
LEDGER = {
    2026: {
        "package_cents": 248000,
        "paid": {"u_you": 52000, "u_jason": 45500, "u_sarah": 50000, "u_alice": 46500, "u_bob": 54000},
        "owed": {"u_you": 47500, "u_jason": 50500, "u_sarah": 49500, "u_alice": 50500, "u_bob": 50000},
        "debts": [{"from": "u_jason", "to": "u_you", "cents": 4500},
                  {"from": "u_jason", "to": "u_sarah", "cents": 500},
                  {"from": "u_alice", "to": "u_bob", "cents": 4000}],
    },
    2025: {
        "package_cents": 231000,
        "paid": {k: 46200 for k in MEMBERS},
        "owed": {k: 46200 for k in MEMBERS},
        "debts": [],
    },
}

SETTLE_APPS = [
    {"id": "venmo", "name": "Venmo",
     "link": lambda amount, memo: f"https://venmo.com/?txn=pay&amount={amount}&note={_urlenc(memo)}"},
    {"id": "cashapp", "name": "Cash App", "link": lambda amount, memo: "https://cash.app/$/summithearthbench"},
    {"id": "zelle", "name": "Zelle", "link": lambda amount, memo: "https://www.zellepay.com/"},
]


def _urlenc(text):
    from urllib.parse import quote
    return quote(text)


# ---------- Home Team (the Locker Room) ----------
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
OPPONENTS = [
    {"id": "op_por", "club": "Portland Thorns", "chip": "Portland · 9/26",
     "home_date": "9/26", "away_date": "5/9", "away_venue": "Providence Park",
     "form": "W W D L W", "shape": "4-3-3, inverted right back, high line they will not drop.",
     "quick_stats": [("Goals for", "31"), ("Goals against", "19"), ("Away wins", "5")],
     "halftime": "They press the goal kick for twenty minutes and then stop. Play through the first twenty and the second half opens up.",
     "players": [
         {"id": "o1", "num": 9, "name": "Marisol Vega", "pos": "FWD", "danger": True,
          "note": "Every dangerous move starts with her drifting to the left half-space. Track it or lose the game."},
         {"id": "o2", "num": 6, "name": "Elin Sandberg", "pos": "MID", "danger": False,
          "note": "Screens the back four. Slow across the ground — go at her sideways, not through her."},
         {"id": "o3", "num": 2, "name": "Dara Whitfield", "pos": "DEF", "danger": False,
          "note": "Overlaps constantly and recovers late. The space behind her is the game."},
     ]},
    {"id": "op_bay", "club": "Bay FC", "chip": "Bay · 10/3",
     "home_date": "10/3", "away_date": "6/20", "away_venue": "PayPal Park",
     "form": "L D W L D", "shape": "4-4-2 block, counters through the left channel.",
     "quick_stats": [("Goals for", "22"), ("Goals against", "26"), ("Away wins", "2")],
     "halftime": "They sit, they absorb, and they break once. Keep a body on the counter and the afternoon is comfortable.",
     "players": [
         {"id": "o4", "num": 11, "name": "Noor Haddad", "pos": "FWD", "danger": True,
          "note": "The one who hurts you on the break. Nine of her twelve goals came inside four passes."},
         {"id": "o5", "num": 8, "name": "Robin Castellanos", "pos": "MID", "danger": False,
          "note": "Takes every set piece. Left foot, near post, in-swinging."},
         {"id": "o6", "num": 1, "name": "Ada Lindgren", "pos": "GK", "danger": False,
          "note": "Strong hands, hesitant feet. Press the back pass."},
     ]},
    {"id": "op_acf", "club": "Angel City FC", "chip": "Angel City · 10/18",
     "home_date": "10/18", "away_date": "7/11", "away_venue": "BMO Stadium",
     "form": "W W W D W", "shape": "3-4-3, wing-backs high, three at the back that can be turned.",
     "quick_stats": [("Goals for", "36"), ("Goals against", "17"), ("Away wins", "7")],
     "halftime": "The wing-backs are still up the pitch at 60 minutes. That is when the diagonal behind them is on.",
     "players": [
         {"id": "o7", "num": 7, "name": "Céline Abara", "pos": "FWD", "danger": True,
          "note": "Best player on either team most weeks. Double her the moment she faces up."},
         {"id": "o8", "num": 3, "name": "Wren Okonkwo", "pos": "DEF", "danger": False,
          "note": "Left of the three. Comfortable stepping in, uncomfortable turning."},
         {"id": "o9", "num": 16, "name": "Tamsin Reyes", "pos": "MID", "danger": False,
          "note": "Runs the whole game at one speed. Tires after 70."},
     ]},
]

# ---------- Hearthside Notes ----------
HEARTHSIDE_NOTES = [
    {"kind": "player", "eyebrow": "Key player to watch", "num": 9, "name": "Yazmeen Ryan",
     "pos": "Forward · Denver Summit FC",
     "body": "Wears the 9 up top for Summit this season. See the Locker Room tab for the full squad."},
    {"kind": "tactics", "eyebrow": "Rivalry note", "name": "Portland hold a high line",
     "body": "Portland have not dropped their line all season, and Summit have the two quickest forwards in the league. The game is decided in the twenty yards behind Dara Whitfield."},
    {"kind": "trivia", "eyebrow": "Tap to reveal", "question": "What home ground does Denver Summit play at?",
     "answer": "Centennial Stadium — out in Centennial, Colorado, in the thin air the away sign likes to remind visitors about."},
]
