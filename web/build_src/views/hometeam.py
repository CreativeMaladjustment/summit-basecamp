"""The Locker Room: full squad, position filters. Every scouting note is
pre-rendered and just hidden/shown — matches the fix already made once in
the JS version, where a from-scratch repaint let a stray null leak through.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h
from components import badge, photo_slot, bio_links
from data import SQUAD, POSITIONS, DENVER_ROSTER_URL


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "hometeam"},
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800"}}, "The Locker Room"),
        h("p", {"style": {"margin": "4px 0 12px", "fontSize": "14px", "color": "var(--ink-mute)"}},
          "Denver Summit FC, top to bottom. Tap a player to pull their card off the peg."),
        h("div", {"cls": "scroll-row", "role": "tablist"},
          [h("button", {"cls": "chip", "type": "button", "role": "tab",
                        "aria-selected": "true" if p == "Whole squad" else "false",
                        "data-role": "hometeam-filter", "data-value": p}, p) for p in POSITIONS]),
        h("div", {"cls": "grid-auto", "style": {"marginTop": "12px", "alignItems": "start"}},
          [player_card(p) for p in SQUAD]),
    )


def player_card(p):
    stats = h(
        "div", {"style": {"display": "flex", "gap": "8px", "flexWrap": "wrap"}},
        [h("div", {"cls": "card card--sunk", "style": {"padding": "8px 12px", "borderRadius": "10px", "flex": "1 1 92px"}},
           h("p", {"cls": "eyebrow"}, k),
           h("p", {"style": {"margin": "2px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "17px"}}, v))
         for k, v in p["stats"]],
    )

    return h(
        "article", {"cls": "card", "data-position": p["pos"]},
        h("div", {"style": {"display": "flex", "gap": "12px"}},
          photo_slot(p["id"], 92),
          h("div", {"style": {"minWidth": "0", "flex": "1"}},
            h("p", {"style": {"margin": "0", "display": "flex", "alignItems": "center", "gap": "8px", "flexWrap": "wrap"}},
              badge(f'#{p["num"]}' if p["num"] else "No. TBD", "gold"),
              h("a", {"href": f'https://en.wikipedia.org/w/index.php?search={_urlenc(p["name"])}',
                       "target": "_blank", "rel": "noopener noreferrer",
                       "style": {"fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "16px"}}, p["name"])),
            h("p", {"style": {"margin": "3px 0 0", "fontSize": "12px", "fontFamily": "var(--font-mono)", "color": "var(--ink-mute)"}}, p["pos"]),
            bio_links(p["name"], DENVER_ROSTER_URL))),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "12px"},
                     "aria-expanded": "false", "data-role": "expand", "data-target": f'detail-{p["id"]}',
                     "data-label-open": "Scouting note", "data-label-close": "Close"}, "Scouting note"),
        h("div", {"style": {"marginTop": "12px"}, "id": f'detail-{p["id"]}', "hidden": True},
          stats, h("p", {"style": {"margin": "10px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}}, p["note"])),
    )


def _urlenc(text):
    from urllib.parse import quote
    return quote(text)
