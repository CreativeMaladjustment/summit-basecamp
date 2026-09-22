"""The 14ers: package cost, weighted tier split, simplified debts, season
history, and the Settle Up sheet. Both seasons' content are pre-rendered
side by side; src/app.js toggles which season's block is visible.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h, Raw
from icons import svg
from components import avatar
from fmt import money
from layout import sheet_template
from data import MEMBERS, SEASONS, TIERS, LEDGER, FIXTURES, SYNDICATES, ME, SETTLE_APPS


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "hearth"},
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800"}}, "The 14ers"),
        h("p", {"style": {"margin": "4px 0 12px", "fontSize": "14px", "color": "var(--ink-mute)"}},
          "What the season costs, who is carrying it, and how to square up."),
        [season_block(y) for y in SEASONS],
        # History lists every season at once, so unlike the block above it
        # renders once rather than once per season.
        h("div", {"cls": "grid-auto", "style": {"marginTop": "12px"}}, history_card()),
    )


def season_block(year_row):
    year = year_row["year"]
    ledger = LEDGER[year]
    mine = (ledger["paid"].get(ME, 0) - ledger["owed"].get(ME, 0))

    return h(
        "div", {"data-season-block": str(year), "hidden": not year_row["current"]},
        balance_line(mine, year),
        h("div", {"cls": "grid-auto", "style": {"marginTop": "12px"}},
          package_card(ledger, year), debts_card(ledger)),
    )


def balance_line(cents, year):
    text = "All square with the 14ers." if cents == 0 else (
        f"The circle holds your {money(cents)}." if cents > 0 else f"You hold the tab ({money(abs(cents))})."
    )
    return h(
        "div", {"cls": "card", "style": {"border": "1px solid var(--summit-sunshine)", "background": "rgba(246,190,0,.08)"}},
        h("p", {"style": {"margin": "0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "18px"}}, text),
        h("button", {"cls": "btn btn--primary", "type": "button", "style": {"marginTop": "12px"},
                     "data-open-sheet": "sheet-settleup", "data-settle-amount": str(abs(cents)),
                     "data-settle-owed": "true" if cents > 0 else "false"}, "Settle Up") if cents != 0 else None,
    )


def package_card(ledger, year):
    fixtures = [f for f in FIXTURES if f["season"] == year]
    by_tier = {}
    for f in fixtures:
        by_tier[f["tier"]] = by_tier.get(f["tier"], 0) + f["value_cents"] * len(f["seats"])
    total = sum(by_tier.values()) or 1

    bars = []
    for tier, cents in by_tier.items():
        pct = round(cents / total * 100)
        bars.append(h(
            "div", {"style": {"marginBottom": "10px"}},
            h("div", {"style": {"display": "flex", "justifyContent": "space-between", "fontSize": "13px"}},
              h("span", None, f'{TIERS[tier]["label"]} · ×{TIERS[tier]["weight"]}'),
              h("span", {"style": {"fontFamily": "var(--font-mono)"}}, f'{money(cents)} · {pct}%')),
            h("div", {"style": {"height": "6px", "borderRadius": "999px", "background": "var(--surface-sunk)", "marginTop": "5px"}},
              h("div", {"style": {"width": f"{pct}%", "height": "100%", "borderRadius": "999px",
                                   "background": "var(--summit-sunshine)" if tier == "rivalry" else "var(--summit-green)"}})),
        ))

    syn = SYNDICATES[0]
    return h(
        "article", {"cls": "card"},
        h("h2", {"cls": "card__title"}, f"{year} package"),
        h("p", {"style": {"margin": "0", "fontFamily": "var(--font-display)", "fontWeight": "800", "fontSize": "28px"}},
          money(ledger["package_cents"])),
        h("p", {"style": {"margin": "2px 0 14px", "fontSize": "13px", "color": "var(--ink-mute)"}},
          f'{len(syn["seats"])} seats · {len(syn["member_ids"])} in the circle'),
        h("p", {"cls": "eyebrow"}, "Weighted by tier"),
        h("div", {"style": {"marginTop": "8px"}}, bars) if bars else
        h("p", {"style": {"fontSize": "13px", "color": "var(--ink-mute)"}}, "No fixtures this season."),
    )


def debts_card(ledger):
    debts = ledger["debts"]
    rows = [
        h("div", {"style": {"display": "flex", "alignItems": "center", "gap": "10px", "padding": "10px 0",
                             "borderBottom": "1px solid var(--hairline)"}},
          avatar(d["from"]),
          h("p", {"style": {"margin": "0", "flex": "1", "fontSize": "14px"}},
            h("strong", None, MEMBERS[d["from"]]["name"]), " owes ", h("strong", None, MEMBERS[d["to"]]["name"])),
          h("span", {"style": {"fontFamily": "var(--font-mono)", "fontWeight": "500"}}, money(d["cents"])))
        for d in debts
    ]
    squared = [m for m in MEMBERS if not any(d["from"] == m or d["to"] == m for d in debts)]

    return h(
        "article", {"cls": "card"},
        h("h2", {"cls": "card__title"}, "Who holds the tab"),
        h("div", None, rows) if debts else
        h("p", {"style": {"margin": "0", "fontSize": "14px", "color": "var(--ink-mute)"}}, "All square."),
        h("p", {"cls": "eyebrow", "style": {"marginTop": "14px"}}, "Everyone else"),
        h("div", {"style": {"marginTop": "8px"}},
          [h("p", {"style": {"margin": "0 0 6px", "fontSize": "14px", "color": "var(--ink-mute)"}},
             f'{MEMBERS[m]["name"]} is all square.') for m in squared]),
    )


def history_card():
    rows = []
    for y in SEASONS:
        l = LEDGER[y["year"]]
        rows.append(h(
            "button", {"cls": "setting-row", "type": "button", "style": {
                "width": "100%", "textAlign": "left", "alignItems": "center", "background": "none", "border": "none",
                "borderBottom": "1px solid var(--hairline)", "cursor": "pointer", "font": "inherit", "color": "inherit"},
                "data-role": "season", "data-value": str(y["year"])},
            h("div", {"cls": "setting-row__body"},
              h("p", {"cls": "setting-row__label"}, y["label"]),
              h("p", {"cls": "setting-row__help"},
                f'{len(l["debts"])} open transfer{"s" if len(l["debts"]) > 1 else ""}' if l["debts"] else "Settled")),
            h("span", {"style": {"fontFamily": "var(--font-mono)", "fontSize": "14px"}}, money(l["package_cents"])),
        ))
    return h("article", {"cls": "card"}, h("h2", {"cls": "card__title"}, "Season history"), rows)


def settle_sheet():
    apps = h(
        "div", {"id": "settle-apps"},
        [h("a", {"cls": "btn btn--ghost btn--block", "style": {"marginBottom": "8px"}, "data-settle-app": a["id"],
                 "target": "_blank", "rel": "noopener noreferrer", "href": "#"},
           a["name"], Raw(svg("external", size=15))) for a in SETTLE_APPS],
    )
    return sheet_template("sheet-settleup", [
        h("p", {"cls": "eyebrow"}, "Settle up"),
        h("h2", {"cls": "sheet__title", "id": "settle-amount"}, "$0"),
        h("p", {"cls": "sheet__sub", "id": "settle-sub"}, ""),
        h("div", {"cls": "card card--sunk", "style": {"marginBottom": "14px"}},
          h("p", {"cls": "eyebrow"}, "Memo"),
          h("p", {"style": {"margin": "4px 0 0", "fontFamily": "var(--font-mono)", "fontSize": "13px"}, "id": "settle-memo"}, "")),
        apps,
        h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "6px"},
                     "data-close-sheet": "true"}, "Done"),
    ])
