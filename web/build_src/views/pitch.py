"""The 14er Pass: every home fixture, filtered by All / My Matches / On the
Bench.

Which fixtures exist, and who holds which seat, is real per-syndicate data
that does not exist at build time -- web/src/app.js's paintRealFixtures()
builds each row into #pitch-rows from GET /api/groups/{id}/fixtures and
.../fixtures/{id}/seats, carrying the same data-fixture-row/data-mine/
data-bench attributes the filter chips below already look for, so the
existing pitch-filter click handler in app.js needs no changes. This module
only emits the filter chips and the empty shell those rows fill.
"""
from __future__ import annotations

from markup import h

FILTERS = [("all", "All Fixtures"), ("mine", "My Matches"), ("bench", "On the Bench")]


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "pitch"},
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800"}}, "The 14er Pass"),
        h("p", {"style": {"margin": "4px 0 12px", "fontSize": "14px", "color": "var(--ink-mute)"}},
          "Every home fixture in the season package, in order."),
        h("div", {"cls": "scroll-row", "role": "tablist"},
          [h("button", {"cls": "chip", "type": "button", "role": "tab",
                        "aria-selected": "true" if v == "all" else "false",
                        "data-role": "pitch-filter", "data-value": v}, label) for v, label in FILTERS]),
        h("div", {"cls": "grid-auto", "style": {"marginTop": "12px"}, "id": "pitch-rows"}),
        h("p", {"cls": "card", "style": {"marginTop": "12px", "color": "var(--ink-mute)"}, "id": "pitch-empty"},
          "No fixtures logged for this syndicate yet."),
    )
