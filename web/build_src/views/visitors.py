"""Visitors: the visiting club's dressing room. Opponent dossiers and
rosters are fetched dynamically from the API at runtime, so they always stay
current with the synced data. Switching the chip shows/hides opponent blocks.
Tilts stay under 0.6deg and nothing animates, per the design brief.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h
from components import badge, photo_slot, bio_links

CONCRETE = "repeating-linear-gradient(180deg, rgba(120,113,108,.07) 0 38px, rgba(120,113,108,.12) 38px 39px)"


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "visitors"},
        room(),
        h("div", {"style": {"marginTop": "14px"}, "cls": "scroll-row", "role": "tablist",
                  "id": "opponent-chips", "data-role": "opponent-chips"}),
        h("div", {"id": "opponent-dossiers", "data-role": "opponent-dossiers"}),
    )


def room():
    return h(
        "section", {"style": {"borderRadius": "var(--radius-lg)", "border": "1px solid var(--hairline-strong)",
                               "background": f"{CONCRETE}, var(--surface-sunk)", "padding": "18px 16px", "position": "relative"}},
        h("div", {"style": {"display": "inline-block", "transform": "rotate(-0.5deg)", "background": "#E7E2D4",
                             "color": "#1C1917", "border": "1px solid #C9C2AE", "padding": "6px 14px",
                             "fontFamily": "var(--font-mono)", "fontSize": "11px", "letterSpacing": ".14em", "fontWeight": "500"}},
          "AWAY · 5,280 FT"),
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800", "marginTop": "12px"}}, "The Visiting Club's Dressing Room"),
        h("p", {"style": {"margin": "8px 0 0", "fontSize": "14px", "color": "var(--ink-soft)", "maxWidth": "58ch"}},
          "Down the tunnel from Basecamp: bare block walls, a bench an inch out of true, and a team sheet taped over last week's. Everything you need on whoever is in town."),
        h("div", {"style": {"marginTop": "16px", "transform": "rotate(0.4deg)", "background": "var(--surface)",
                             "border": "1px solid var(--surface)", "padding": "14px", "borderRadius": "4px"}},
          h("p", {"cls": "eyebrow"}, "Team sheet"),
          h("div", {"style": {"marginTop": "8px"}, "id": "opponent-schedule"}),
          h("p", {"style": {"margin": "10px 0 0", "fontSize": "12px", "color": "var(--ink-mute)"}},
            "Away dates are for travel planning only — they sit outside the season package.")),
    )


