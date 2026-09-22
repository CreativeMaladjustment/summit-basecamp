"""Visitors: the visiting club's dressing room. Every opponent's dossier and
roster is pre-rendered; switching the chip just shows/hides which one is
visible. Tilts stay under 0.6deg and nothing animates, per the design brief.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h
from components import badge, photo_slot, bio_links
from data import OPPONENTS

CONCRETE = "repeating-linear-gradient(180deg, rgba(120,113,108,.07) 0 38px, rgba(120,113,108,.12) 38px 39px)"


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "visitors"},
        room(),
        h("div", {"style": {"marginTop": "14px"}, "cls": "scroll-row", "role": "tablist"},
          [h("button", {"cls": "chip chip--stone", "type": "button", "role": "tab",
                        "aria-selected": "true" if i == 0 else "false",
                        "data-role": "opponent", "data-value": op["id"]}, op["chip"])
           for i, op in enumerate(OPPONENTS)]),
        [h("div", {"data-opponent-block": op["id"], "hidden": i != 0}, dossier(op))
         for i, op in enumerate(OPPONENTS)],
    )


def room():
    rows = [h("div", {"style": {"display": "flex", "justifyContent": "space-between", "gap": "10px",
                                  "padding": "7px 0", "borderBottom": "1px solid var(--hairline)", "fontSize": "13px"}},
              h("span", {"style": {"fontWeight": "600"}}, op["club"]),
              h("span", {"style": {"fontFamily": "var(--font-mono)", "color": "var(--ink-mute)", "textAlign": "right"}},
                f'HOME {op["home_date"]} · AWAY {op["away_date"]}'))
             for op in OPPONENTS]

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
                             "border": "1px solid var(--hairline-strong)", "padding": "14px", "borderRadius": "4px"}},
          h("p", {"cls": "eyebrow"}, "Team sheet"),
          h("div", {"style": {"marginTop": "8px"}}, rows),
          h("p", {"style": {"margin": "10px 0 0", "fontSize": "12px", "color": "var(--ink-mute)"}},
            "Away dates are for travel planning only — they sit outside the season package.")),
    )


def dossier(op):
    empty_players_note = h(
        "p", {"style": {"margin": "0", "fontSize": "14px", "color": "var(--ink-mute)"}},
        "Full team sheet not published here yet — see the ",
        h("a", {"href": op["match_url"], "target": "_blank", "rel": "noopener noreferrer"},
          "latest meeting"),
        " for who played.",
    )
    return h(
        "section", {"style": {"marginTop": "14px"}},
        h("article", {"cls": "card"},
          h("div", None,
            h("h2", {"style": {"fontSize": "19px", "fontWeight": "800"}}, op["club"]),
            h("p", {"style": {"margin": "4px 0 0", "fontFamily": "var(--font-mono)", "fontSize": "12px", "color": "var(--ink-mute)"}},
              f'HOME {op["home_date"]} · AWAY {op["away_date"]}'),
            h("p", {"style": {"margin": "2px 0 0", "fontSize": "13px", "color": "var(--ink-mute)"}},
              f'Away leg at {op["away_venue"]} — outside the package.')),
          h("div", {"style": {"marginTop": "14px", "padding": "12px 14px", "borderRadius": "10px",
                               "background": "rgba(200,75,49,.1)", "borderLeft": "3px solid var(--summit-sandstone)"}},
            h("p", {"cls": "eyebrow", "style": {"color": "var(--summit-sandstone)"}}, "This season"),
            h("p", {"style": {"margin": "5px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}}, op["recent_result"]))),
        h("p", {"cls": "eyebrow", "style": {"margin": "16px 0 8px"}}, "Dressing room occupants"),
        h("div", {"cls": "grid-auto", "style": {"alignItems": "start"}}, [peg_card(p, op) for p in op["players"]])
        if op["players"] else empty_players_note,
    )


def peg_card(p, op):
    tilt = -0.35 if p["num"] % 2 else 0.3
    return h(
        "article", {"cls": "card", "style": {"transform": f"rotate({tilt}deg)"}},
        h("div", {"style": {"display": "flex", "gap": "12px"}},
          photo_slot(p["id"], 84),
          h("div", {"style": {"flex": "1", "minWidth": "0"}},
            h("p", {"style": {"margin": "0", "display": "flex", "alignItems": "center", "gap": "8px", "flexWrap": "wrap"}},
              badge(f'#{p["num"]}', "gold"),
              h("a", {"href": f'https://en.wikipedia.org/w/index.php?search={_urlenc(p["name"])}',
                       "target": "_blank", "rel": "noopener noreferrer",
                       "style": {"fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "15px"}}, p["name"]),
              badge("DANGER", "ember") if p["danger"] else None),
            h("p", {"style": {"margin": "3px 0 0", "fontFamily": "var(--font-mono)", "fontSize": "12px", "color": "var(--ink-mute)"}}, p["pos"]),
            bio_links(p["name"], op["match_url"], club_label="Latest meeting"))),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "10px"},
                     "aria-expanded": "false", "data-role": "expand", "data-target": f'peg-detail-{p["id"]}',
                     "data-label-open": "Pull it off the hook", "data-label-close": "Back on the hook"},
          "Pull it off the hook"),
        h("p", {"style": {"margin": "10px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}, "id": f'peg-detail-{p["id"]}', "hidden": True},
          p["note"]),
    )


def _urlenc(text):
    from urllib.parse import quote
    return quote(text)
