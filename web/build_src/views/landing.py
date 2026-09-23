"""Landing and 'find your syndicate' — the two-step entry flow ahead of the
app. Both are always in the DOM; src/app.js shows exactly one of the three
stages (landing / syndicate / app) based on a localStorage flag.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h
from layout import lockup, sheet_template
from components import badge
from data import TOUCHLINE_NOTES


def landing():
    return h(
        "div", {"cls": "view", "id": "stage-landing", "style": {
            "minHeight": "100vh", "display": "flex", "flexDirection": "column",
            "alignItems": "center", "padding": "28px 16px 40px"}},
        h("div", {"style": {"width": "min(100%, 520px)"}},
          lockup(size=46, icon_size=23),
          h("h1", {"style": {"margin": "26px 0 0", "fontSize": "34px", "fontWeight": "800",
                              "lineHeight": "1.08", "letterSpacing": "-.025em"}},
            "Two seats. Five friends. One ledger nobody argues about."),
          h("p", {"style": {"margin": "12px 0 0", "fontSize": "16px", "color": "var(--ink-soft)"}},
            "Share a season ticket package without the group chat arithmetic. Claim a match, call a sub, and settle up when the season ends."),
          h("p", {"cls": "eyebrow", "style": {"marginTop": "28px"}}, "Tonight on the Touchline"),
          h("div", {"style": {"marginTop": "10px"}}, [teaser(n) for n in TOUCHLINE_NOTES]),
          h("div", {"cls": "card", "style": {"marginTop": "24px"}},
            h("div", {"id": "password-field"},
              h("label", {"cls": "field"},
                h("span", {"cls": "field__label"}, "Site password"),
                h("input", {"cls": "input", "type": "password", "id": "site-password",
                            "placeholder": "Ask whoever runs the syndicate", "autocomplete": "current-password"}))),
            h("p", {"cls": "field__label", "style": {"marginTop": "16px"}}, "Pick your login"),
            h("div", {"id": "guest-slots", "style": {
                "marginTop": "8px", "display": "grid",
                "gridTemplateColumns": "repeat(3, 1fr)", "gap": "8px"}},
              [h("button", {"cls": "btn btn--ghost btn--block", "type": "button",
                            "data-role": "guest-login", "data-guest-id": f"usr_guest{n}"},
                 f"Guest {n}") for n in range(1, 7)]),
            h("p", {"id": "sign-in-error", "role": "alert", "hidden": True, "style": {
                "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)", "textAlign": "center"}})),
          h("p", {"style": {"margin": "14px 0 0", "fontSize": "13px", "color": "var(--ink-mute)", "textAlign": "center"}},
            "Six shared logins, one password -- remembered on this device after the first time. "
            "Pick yours below; set your name from Campfire Settings once you're in.")),
    )


def teaser(note):
    if note["kind"] == "trivia":
        return h(
            "article", {"cls": "card", "style": {"marginBottom": "10px"}},
            h("p", {"cls": "eyebrow"}, "Trivia"),
            h("p", {"style": {"margin": "6px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "16px"}}, note["question"]),
            h("p", {"style": {"margin": "8px 0 0", "fontSize": "13px", "color": "var(--ink-mute)"}}, "Sign in to flip the card."),
        )
    return h(
        "article", {"cls": "card", "style": {"marginBottom": "10px"}},
        h("p", {"cls": "eyebrow"}, note["eyebrow"]),
        h("p", {"style": {"margin": "6px 0 0", "display": "flex", "alignItems": "center", "gap": "8px"}},
          badge(f'#{note["num"]}', "gold") if note.get("num") else None,
          h("strong", {"style": {"fontFamily": "var(--font-display)", "fontSize": "16px"}}, note["name"])),
        h("p", {"style": {"margin": "8px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}}, note["body"]),
    )


def syndicate():
    return h(
        "div", {"cls": "view", "id": "stage-syndicate", "hidden": True, "style": {
            "minHeight": "100vh", "display": "flex", "flexDirection": "column",
            "alignItems": "center", "padding": "28px 16px 40px"}},
        h("div", {"style": {"width": "min(100%, 520px)"}},
          lockup(size=46, icon_size=23),
          h("h1", {"style": {"margin": "26px 0 0", "fontSize": "28px", "fontWeight": "800", "letterSpacing": "-.02em"}},
            "Find your syndicate"),
          h("p", {"style": {"margin": "10px 0 0", "fontSize": "15px", "color": "var(--ink-soft)"}},
            "Join the circle that holds the seats, or start one and invite the rest."),
          h("div", {"cls": "card", "style": {"marginTop": "20px"}},
            h("label", {"cls": "field__label", "for": "invite"}, "Invite code"),
            h("input", {"cls": "input", "id": "invite", "placeholder": "e.g. NORTH-114"}),
            h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "10px"},
                         "data-role": "join-syndicate"}, "Join with code"),
            h("p", {"id": "join-syndicate-error", "role": "alert", "hidden": True, "style": {
                "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)", "textAlign": "center"}})),
          h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "10px"},
                       "data-open-sheet": "sheet-new-syndicate"}, "Start a new syndicate")),
    )


def new_syndicate_sheet():
    """Submits to the real POST /api/groups -- name, season, total seats and
    package cost all land in D1, same as everything else this sheet's own
    fields take. What doesn't follow: every fixture, seat and ledger figure
    shown elsewhere in this static build is still fixed mock data keyed to
    a specific seat count and price (web/build_src/data.py), unconnected to
    whatever group this creates -- resizing those for real is its own,
    larger piece of work. Said plainly in the sheet's own copy rather than
    quietly implying more than lands."""
    return sheet_template("sheet-new-syndicate", [
        h("p", {"cls": "eyebrow"}, "Find your syndicate"),
        h("h2", {"cls": "sheet__title"}, "Start a new syndicate"),
        h("p", {"cls": "sheet__sub"},
          "Creates a real syndicate you're the admin of. The demo schedule "
          "and ledger elsewhere in this app don't resize to match it yet -- "
          "only the name, season, seats and cost themselves are real."),
        h("form", {"id": "new-syndicate-form"},
          h("label", {"cls": "field"},
            h("span", {"cls": "field__label"}, "Syndicate name"),
            h("input", {"cls": "input", "id": "new-syn-name", "required": True,
                        "placeholder": "e.g. North Stand Syndicate"})),
          h("label", {"cls": "field"},
            h("span", {"cls": "field__label"}, "Season"),
            h("input", {"cls": "input", "type": "number", "id": "new-syn-season", "value": "2026", "min": "1900"})),
          h("label", {"cls": "field"},
            h("span", {"cls": "field__label"}, "Total seats"),
            h("input", {"cls": "input", "type": "number", "id": "new-syn-seats", "value": "2", "min": "1"})),
          h("label", {"cls": "field"},
            h("span", {"cls": "field__label"}, "Package cost"),
            h("input", {"cls": "input", "type": "number", "id": "new-syn-cost", "placeholder": "2480.00", "min": "0", "step": "0.01"})),
          h("button", {"cls": "btn btn--primary btn--block", "type": "submit", "style": {"marginTop": "6px"}},
            "Create syndicate"),
          h("p", {"id": "new-syndicate-error", "role": "alert", "hidden": True, "style": {
              "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)", "textAlign": "center"}})),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-close-sheet": "true"}, "Never mind"),
    ])
