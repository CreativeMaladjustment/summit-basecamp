"""Page shell: <head>, header/nav, and the sheet chrome every sheet template
shares. Nav sections and sheets are toggled by `hidden` in src/app.js — this
module only emits markup, never picks what's currently visible."""
from __future__ import annotations

from markup import h, Raw, El
from icons import svg
from data import SYNDICATES, SEASONS

TABS = [
    ("matchday", "Matchday"),
    ("pitch", "The 14er Pass"),
    ("bench", "The Bench"),
    ("hearth", "The 14ers"),
    ("hometeam", "Home Team"),
    ("visitors", "Visitors"),
]


def head():
    return Raw(
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '<title>Summit Basecamp</title>'
        '<meta name="description" content="Collaborative season-ticket sharing, seat liquidity and expense splitting for supporter syndicates.">'
        '<meta name="theme-color" content="#134E48" media="(prefers-color-scheme: light)">'
        '<meta name="theme-color" content="#0A1413" media="(prefers-color-scheme: dark)">'
        '<link rel="manifest" href="./manifest.webmanifest">'
        '<link rel="icon" href="./icon.svg" type="image/svg+xml">'
        '<link rel="apple-touch-icon" href="./icon.svg">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-title" content="Summit Basecamp">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">'
        '<link rel="stylesheet" href="./src/styles/tokens.css">'
        '<link rel="stylesheet" href="./src/styles/base.css">'
        '<link rel="stylesheet" href="./src/styles/components.css">'
    )


def lockup(size=40, icon_size=21):
    return h(
        "div", {"style": {"display": "flex", "alignItems": "center", "gap": "12px", "minWidth": "0"}},
        h("div", {"aria-hidden": "true", "style": {
            "width": f"{size}px", "height": f"{size}px", "borderRadius": "12px",
            "background": "#134E48", "flex": "none", "display": "grid", "placeItems": "center"}},
          Raw(svg("mark", size=icon_size, stroke="#F6BE00"))),
        h("div", {"style": {"minWidth": "0"}},
          h("p", {"style": {"margin": "0", "fontFamily": "var(--font-display)", "fontWeight": "800",
                             "fontSize": "17px", "letterSpacing": "-.015em"}}, "Summit Basecamp"),
          h("p", {"cls": "eyebrow", "style": {"marginTop": "1px"}}, "Season tickets, shared")),
    )


def header(open_seats_count):
    # Every screen is pre-rendered from SYNDICATES[0]'s fixtures, seats and
    # members only, so picking another syndicate here has nothing to switch
    # to yet — disable rather than leave a control that silently does
    # nothing. Multi-syndicate rendering is a build_src change, not
    # something src/app.js can fake at runtime. Only SYNDICATES[0] gets an
    # option, not the rest of SYNDICATES -- those are placeholder data for a
    # switcher that doesn't work yet, not real syndicates this member
    # belongs to, and listing them here would show them as if they were.
    syn = SYNDICATES[0]
    switcher = h(
        "select", {"id": "syn-switch", "cls": "select",
                   "style": {"maxWidth": "100%", "fontWeight": "600", "minHeight": "40px"},
                   "data-role": "syndicate-switch", "disabled": True,
                   "title": "Switching syndicates is coming soon"},
        h("option", {"value": syn["id"], "selected": True}, f'{syn["name"]} — {syn["holds"]}'),
    )

    # Only the 14ers ledger is pre-rendered per-season (Matchday/Pitch/Bench
    # show the current season's fixtures only), so this only does anything
    # there — src/app.js hides it outside the 14ers screen rather than
    # implying a global season switch. Matchday is the default tab, so start
    # hidden.
    season_row = h(
        "div", {"id": "season-row", "cls": "scroll-row", "style": {"marginTop": "8px"}, "hidden": True,
                 "role": "tablist", "aria-label": "Season"},
        [h("button", {"cls": "chip", "type": "button", "role": "tab",
                      "aria-selected": "true" if y["current"] else "false",
                      "data-role": "season", "data-value": str(y["year"])}, y["label"]) for y in SEASONS],
    )

    tabs = h(
        "nav", {"cls": "scroll-row", "style": {"marginTop": "10px"}, "aria-label": "Sections"},
        [h("button", {"cls": "chip", "type": "button", "role": "tab",
                      "aria-selected": "true" if tid == "matchday" else "false",
                      "data-role": "tab", "data-value": tid},
           label,
           h("span", {"cls": "badge badge--ember", "style": {"marginLeft": "6px"}, "data-bench-count": "true"},
             str(open_seats_count)) if tid == "bench" and open_seats_count else None)
         for tid, label in TABS],
    )

    bell = h(
        "button", {"cls": "btn btn--ghost", "type": "button",
                   "style": {"minHeight": "40px", "padding": "0 12px", "position": "relative"},
                   "aria-label": f"{open_seats_count} seats need attention" if open_seats_count else "No pending requests",
                   "data-role": "goto-bench"},
        Raw(svg("bell", size=18)),
        h("span", {"cls": "badge badge--ember", "data-bench-count": "true"}, str(open_seats_count)) if open_seats_count else None,
    )

    gear = h(
        "button", {"cls": "btn btn--ghost", "type": "button", "style": {"minHeight": "40px", "padding": "0 12px"},
                   "aria-label": "Campfire settings", "data-role": "tab-toggle-settings"},
        Raw(svg("settings", size=18)),
    )

    return h(
        "header", {"style": {"borderBottom": "1px solid var(--hairline)", "background": "var(--surface)",
                              "position": "sticky", "top": "0", "zIndex": "20",
                              "paddingTop": "12px", "paddingBottom": "10px"}},
        h("div", {"cls": "shell"},
          h("div", {"style": {"display": "flex", "alignItems": "center", "justifyContent": "space-between", "gap": "12px"}},
            lockup(),
            h("div", {"style": {"display": "flex", "gap": "6px", "flex": "none"}}, bell, gear)),
          h("div", {"style": {"marginTop": "10px"}},
            h("label", {"cls": "sr-only", "for": "syn-switch"}, "Syndicate"), switcher),
          season_row, tabs),
    )


def sheet_template(sheet_id, body_children):
    """A backdrop+sheet pair, hidden until src/app.js clears `hidden`. Every
    sheet carries an `<h2 class="sheet__title">` somewhere in its body — give
    it an id and point the dialog's `aria-labelledby` at it, so screen
    readers announce the sheet by name instead of as an unlabeled dialog."""
    heading_id = f"{sheet_id}-heading"
    for child in body_children:
        if isinstance(child, El) and child.tag == "h2":
            # The settle-up sheet's heading already carries an id app.js
            # updates by textContent — keep it rather than overwrite it.
            heading_id = child.attrs.get("id") or heading_id
            child.attrs["id"] = heading_id
            break

    return h(
        "div", {"id": sheet_id, "cls": "sheet-backdrop", "hidden": True, "data-role": "sheet"},
        h("div", {"cls": "sheet", "role": "dialog", "aria-modal": "true", "aria-labelledby": heading_id},
          h("div", {"cls": "sheet__handle"}),
          h("div", {"data-role": "sheet-body"}, *body_children)),
    )
