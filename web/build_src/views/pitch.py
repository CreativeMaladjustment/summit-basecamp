"""The Pitch: every home fixture, filtered by All / My Matches / On the
Bench. Filtering hides pre-rendered rows by a data attribute — src/app.js
never rebuilds a row.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h
from components import badge
from fmt import money, match_date, match_time
from data import MEMBERS, TIERS, ME
from seats import seat_avatar_toggle, claim_button, seat_key, is_claimable

FILTERS = [("all", "All Fixtures"), ("mine", "My Matches"), ("bench", "On the Bench")]


def render(fixtures):
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "pitch"},
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800"}}, "The Pitch"),
        h("p", {"style": {"margin": "4px 0 12px", "fontSize": "14px", "color": "var(--ink-mute)"}},
          "Every home fixture in the season package, in order."),
        h("div", {"cls": "scroll-row", "role": "tablist"},
          [h("button", {"cls": "chip", "type": "button", "role": "tab",
                        "aria-selected": "true" if v == "all" else "false",
                        "data-role": "pitch-filter", "data-value": v}, label) for v, label in FILTERS]),
        h("div", {"cls": "grid-auto", "style": {"marginTop": "12px"}, "id": "pitch-rows"},
          [fixture_row(f) for f in fixtures]) if fixtures else
          h("p", {"cls": "card", "style": {"marginTop": "12px", "color": "var(--ink-mute)"}}, "No fixtures this season."),
        h("p", {"cls": "card", "style": {"marginTop": "12px", "color": "var(--ink-mute)"}, "id": "pitch-empty", "hidden": True},
          "Nothing here for this filter."),
    )


def status_pill(f):
    bench = [s for s in f["seats"] if s["status"] == "bench"]
    listed = [s for s in f["seats"] if s["status"] == "listed"]
    if bench:
        n = len(bench)
        return badge(f'{n} seat{"s" if n > 1 else ""} on the bench', "ember")
    if listed:
        return badge("Listed outside", "ember")
    names = " & ".join(
        MEMBERS[s["holder"]]["name"] if s["holder"] else s.get("guest_name")
        for s in f["seats"] if s["holder"] or s.get("guest_name")
    )
    return badge(f"Starting · {names}", "green")


def fixture_row(f):
    my_seat = next((s for s in f["seats"] if s["holder"] == ME), None)
    open_seat = next((s for s in f["seats"] if s["status"] == "bench"), None)
    is_mine = "true" if my_seat else "false"
    is_bench = "true" if any(is_claimable(s) for s in f["seats"]) else "false"

    actions = []
    if my_seat:
        actions.append(h("button", {"cls": "btn btn--ghost", "type": "button",
                                     "data-open-sheet": f'sheet-callasub-{f["id"]}-{my_seat["number"]}'}, "Call a Sub"))
    if open_seat:
        actions.append(claim_button("Take the Pitch", seat_key(f["id"], open_seat["number"]), cls="btn btn--primary"))

    return h(
        "article", {"cls": "card", "data-fixture-row": f["id"], "data-mine": is_mine, "data-bench": is_bench},
        h("div", {"style": {"display": "flex", "justifyContent": "space-between", "gap": "10px", "alignItems": "flex-start"}},
          h("div", None,
            h("p", {"cls": "eyebrow"}, f'{match_date(f["kickoff"])} · {match_time(f["kickoff"])}'),
            h("p", {"style": {"margin": "4px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "17px"}},
              f'vs {f["opponent"]}'),
            h("p", {"style": {"margin": "2px 0 0", "fontSize": "13px", "color": "var(--ink-mute)"}}, f["venue"])),
          h("div", {"style": {"display": "flex", "flexDirection": "column", "alignItems": "flex-end", "gap": "6px"}},
            badge("Rivalry", "gold") if f["tier"] == "rivalry" else badge(TIERS[f["tier"]]["label"], "mute"),
            h("span", {"style": {"fontFamily": "var(--font-mono)", "fontSize": "12px", "color": "var(--ink-mute)"}},
              f'{money(f["value_cents"])} / seat'))),
        h("div", {"style": {"display": "flex", "alignItems": "center", "gap": "8px", "marginTop": "12px", "flexWrap": "wrap"},
                   "id": f'pitch-status-{f["id"]}'},
          [seat_avatar_toggle(f, s) for s in f["seats"]], status_pill(f)),
        h("div", {"style": {"display": "flex", "gap": "8px", "marginTop": "12px", "flexWrap": "wrap"}}, actions)
          if actions else None,
    )
