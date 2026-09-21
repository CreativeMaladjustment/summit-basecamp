"""The Bench: seats waiting for a sub, and anything listed outside. A card
disappears from its list the moment its seat is claimed elsewhere — handled
by hiding, keyed off the same data-seat attribute Pitch uses.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h, Raw
from icons import svg
from components import badge
from fmt import money, match_date, match_time
from data import MEMBERS, ME
from seats import seat_key, claim_button


def open_seats(fixtures):
    out = []
    for f in fixtures:
        for s in f["seats"]:
            if s["status"] in ("bench", "listed"):
                out.append((f, s))
    return out


def render(fixtures, bench_notes_by_id):
    on_bench = [(f, s) for f, s in open_seats(fixtures) if s["status"] == "bench"]
    listed = [(f, s) for f, s in open_seats(fixtures) if s["status"] == "listed"]
    held_by_me = [(f, s) for f in fixtures for s in f["seats"] if s["holder"] == ME]

    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "bench"},
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800"}}, "The Bench"),
        h("p", {"style": {"margin": "4px 0 14px", "fontSize": "14px", "color": "var(--ink-mute)"}},
          "Seats nobody is holding, and anything the circle has listed outside."),
        _section("Waiting for a sub", on_bench, bench_notes_by_id, claimable=True, sid="bench-waiting",
                  extra_cards=[held_seat_listing_card(f, s) for f, s in held_by_me]),
        _section("Listed outside the Hearth", listed, bench_notes_by_id, claimable=False, sid="bench-listed"),
        h("p", {"cls": "card", "style": {"color": "var(--ink-mute)"}, "id": "bench-empty",
                "hidden": bool(on_bench or listed)},
          "The bench is empty — every seat has someone on it."),
    )


def _section(title, rows, notes_by_id, claimable, sid, extra_cards=None):
    cards = [seat_card(f, s, notes_by_id, claimable) for f, s in rows] + (extra_cards or [])
    return h(
        "section", {"style": {"marginBottom": "18px"}, "id": sid, "hidden": not rows},
        h("h2", {"style": {"fontSize": "15px", "margin": "0 0 8px"}}, title),
        h("div", {"cls": "grid-auto"}, cards),
    )


def held_seat_listing_card(fixture, seat):
    """A hidden Bench card for a seat you currently hold, pre-rendered so
    "Release to the Bench" can reveal it instantly. Keyed with a distinct
    `:listing` suffix, separate from the seat's own held/released toggle
    (seats.py), so gifting or listing the seat externally — which also
    flips the seat to "released" everywhere else — does not wrongly make
    it claimable here too."""
    return seat_card(fixture, seat, {}, claimable=True,
                      key_override=f'{seat_key(fixture["id"], seat["number"])}:listing', hidden=True)


def seat_card(fixture, seat, notes_by_id, claimable, key_override=None, hidden=False):
    note = notes_by_id.get(seat.get("bench_note_id")) if seat.get("bench_note_id") else None
    free = note is not None and note["cost_path"] == "free"
    key = key_override or seat_key(fixture["id"], seat["number"])
    from data import SYNDICATES
    home_seat = SYNDICATES[0]["seats"][0]

    body = [
        h("div", {"style": {"display": "flex", "justifyContent": "space-between", "gap": "10px", "alignItems": "flex-start"}},
          h("div", None,
            h("p", {"cls": "eyebrow"}, f'{match_date(fixture["kickoff"])} · {match_time(fixture["kickoff"])}'),
            h("p", {"style": {"margin": "4px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "17px"}},
              f'vs {fixture["opponent"]}'),
            h("p", {"style": {"margin": "2px 0 0", "fontSize": "13px", "color": "var(--ink-mute)"}},
              f'Seat {seat["number"]} · Sec {home_seat["section"]}, Row {home_seat["row"]}')),
          badge("Rivalry", "gold") if fixture["tier"] == "rivalry" else None),
    ]
    if note:
        body.append(h("p", {"style": {"margin": "10px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}},
                       f'“{note["body"]}” — {MEMBERS.get(note["author_id"], {}).get("name", "Someone")}'))

    body.append(h(
        "div", {"style": {"display": "flex", "alignItems": "center", "gap": "8px", "marginTop": "12px", "flexWrap": "wrap"}},
        (badge("On the house", "gold") if free else badge(f'{money((note or {}).get("amount_cents", fixture["value_cents"]))} to take it', "green"))
        if claimable else badge(f'Asking {money(seat.get("ask_cents", fixture["value_cents"]))}', "ember"),
    ))

    if claimable:
        body.append(claim_button("Claim from Bench", key, cls="btn btn--primary btn--block", style={"marginTop": "12px"}))
    else:
        body.append(h(
            "div", {"style": {"display": "flex", "gap": "8px", "marginTop": "12px", "flexWrap": "wrap"}},
            h("a", {"cls": "btn btn--ghost", "href": "https://seatgeek.com/", "target": "_blank", "rel": "noopener noreferrer"},
              Raw(svg("external", size=16)), "View listing"),
            claim_button("Pull it back", key, cls="btn btn--ghost"),
        ))

    return h(
        "article", {"cls": "card", "style": {"borderLeft": f'3px solid {"var(--summit-sandstone)" if claimable else "var(--hairline-strong)"}'},
                     "data-seat": key, "data-state": "open", "data-bench-card": "true", "hidden": hidden},
        body,
    )
