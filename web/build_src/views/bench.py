"""The Bench: seats waiting for a sub, and anything listed outside.

Which seats are open, and any note posted about them, is real per-syndicate
data that does not exist at build time -- web/src/app.js's
paintRealFixtures() fills #bench-waiting and #bench-listed from
GET /api/groups/{id}/listings and .../bench-notes. This module only emits
the empty section shells and the empty-bench message.
"""
from __future__ import annotations

from markup import h


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "bench"},
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800"}}, "The Bench"),
        h("p", {"style": {"margin": "4px 0 14px", "fontSize": "14px", "color": "var(--ink-mute)"}},
          "Seats nobody is holding, and anything the circle has listed outside."),
        h("section", {"style": {"marginBottom": "18px"}, "id": "bench-waiting", "hidden": True},
          h("h2", {"style": {"fontSize": "15px", "margin": "0 0 8px"}}, "Waiting for a sub"),
          h("div", {"cls": "grid-auto", "id": "bench-waiting-list"})),
        h("section", {"style": {"marginBottom": "18px"}, "id": "bench-listed", "hidden": True},
          h("h2", {"style": {"fontSize": "15px", "margin": "0 0 8px"}}, "Listed outside the 14ers"),
          h("div", {"cls": "grid-auto", "id": "bench-listed-list"})),
        h("p", {"cls": "card", "style": {"color": "var(--ink-mute)"}, "id": "bench-empty"},
          "The bench is empty — every seat has someone on it."),
    )
