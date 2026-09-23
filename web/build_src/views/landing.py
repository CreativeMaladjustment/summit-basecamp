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
          # Shown only when the GET /api/groups membership check itself
          # failed (network error, non-2xx) -- landing here with no
          # syndicate listed otherwise looks identical whether someone
          # really has none yet or the check just couldn't run, which is
          # unanswerable from a bug report alone without this.
          h("p", {"id": "syndicate-check-error", "role": "alert", "hidden": True, "style": {
              "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)"}},
            "Couldn't check whether you're already in a syndicate -- showing join/create instead."),
          # Populated by app.js right after sign-in from GET /api/groups --
          # a syndicate someone already belongs to (e.g. one another member
          # created) so they can jump straight back in instead of always
          # being offered create/join again. Hidden here; app.js only shows
          # it (and skips this whole screen entirely) when that call finds
          # one or more real memberships.
          h("div", {"id": "my-syndicates", "hidden": True, "style": {"marginTop": "20px"}},
            h("p", {"cls": "field__label"}, "Your syndicates"),
            h("div", {"id": "my-syndicate-list", "style": {
                "marginTop": "8px", "display": "flex", "flexDirection": "column", "gap": "8px"}})),
          h("div", {"cls": "card", "style": {"marginTop": "20px"}},
            h("label", {"cls": "field__label", "for": "invite"}, "Invite code"),
            h("input", {"cls": "input", "id": "invite", "placeholder": "e.g. amber-canyon"}),
            h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "10px"},
                         "data-role": "join-syndicate"}, "Join with code"),
            h("p", {"id": "join-syndicate-error", "role": "alert", "hidden": True, "style": {
                "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)", "textAlign": "center"}})),
          h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "10px"},
                       "data-open-sheet": "sheet-new-syndicate"}, "Start a new syndicate"),
          # An escape hatch for whoever lands here by mistake -- the wrong
          # guest slot, or GET /api/groups not finding the membership they
          # expected -- same sign-out as Settings', not a dead end forcing
          # a real join/create just to get back to the guest picker.
          h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {
              "marginTop": "24px", "color": "var(--ink-mute)"},
                       "data-role": "sign-out"}, "Sign out")),
    )


def new_syndicate_sheet():
    """Submits to the real POST /api/groups -- name, season, total seats,
    package cost, section/row/seat numbers and the creator's own seat all
    land in D1, same as everything else Matchday/Pitch/Bench/The 14ers
    render for whichever syndicate is currently active (settleIntoSyndicate
    in app.js just repaints everything against the new group's id). A brand
    new syndicate simply starts with no fixtures -- add one via Settings/an
    admin action to see it show up there."""
    return sheet_template("sheet-new-syndicate", [
        h("p", {"cls": "eyebrow"}, "New syndicate"),
        h("h2", {"cls": "sheet__title"}, "Start a new syndicate"),
        h("p", {"cls": "sheet__sub"},
          "Creates a real syndicate you're the admin of, and switches this device to it. "
          "It starts with no fixtures -- add its first match once you're in."),
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
          h("div", {"style": {"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "10px"}},
            h("label", {"cls": "field"},
              h("span", {"cls": "field__label"}, "Section"),
              h("input", {"cls": "input", "id": "new-syn-section", "placeholder": "e.g. 114"})),
            h("label", {"cls": "field"},
              h("span", {"cls": "field__label"}, "Row"),
              h("input", {"cls": "input", "id": "new-syn-row", "placeholder": "e.g. 8"}))),
          h("label", {"cls": "field"},
            h("span", {"cls": "field__label"}, "Seat numbers"),
            h("input", {"cls": "input", "id": "new-syn-seat-labels", "placeholder": "e.g. 3, 4"})),
          h("label", {"cls": "field"},
            h("span", {"cls": "field__label"}, "Your seat number"),
            h("input", {"cls": "input", "id": "new-syn-my-seat", "placeholder": "e.g. 3"})),
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


def join_syndicate_sheet():
    """A second entry point onto the same POST /api/groups/join joinSyndicate()
    already drives from Find-your-syndicate -- opened from Campfire Settings
    so switching which syndicate this device is in doesn't first require
    signing out. Its own ids (join-syndicate-code / join-syndicate-error) are
    deliberately distinct from the #invite / #join-syndicate-error pair on
    that screen, since both sheets sit in the DOM at once."""
    return sheet_template("sheet-join-syndicate", [
        h("p", {"cls": "eyebrow"}, "Switch syndicate"),
        h("h2", {"cls": "sheet__title"}, "Join a different syndicate"),
        h("p", {"cls": "sheet__sub"},
          "Switches this device to whichever syndicate the code belongs to. "
          "Your current one isn't affected -- rejoin it anytime with its own code."),
        h("label", {"cls": "field"},
          h("span", {"cls": "field__label"}, "Invite code"),
          h("input", {"cls": "input", "id": "join-syndicate-code", "placeholder": "e.g. amber-canyon"})),
        h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "6px"},
                     "data-role": "post-join-syndicate"}, "Join"),
        h("p", {"id": "join-syndicate-sheet-error", "role": "alert", "hidden": True, "style": {
            "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)", "textAlign": "center"}}),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-close-sheet": "true"}, "Never mind"),
    ])


def leave_syndicate_sheet():
    """POSTs to POST /api/groups/{id}/leave. Blocked server-side (409) if
    this device is the syndicate's only admin -- leaveSyndicate() in app.js
    surfaces that 409's own message rather than guessing at the reason here,
    since promoting someone else first is a Members action this sheet
    doesn't have a path to."""
    return sheet_template("sheet-leave-syndicate", [
        h("p", {"cls": "eyebrow"}, "Leave syndicate"),
        h("h2", {"cls": "sheet__title"}, "Leave this syndicate?"),
        h("p", {"cls": "sheet__sub"},
          "You'll lose access to ", h("strong", {"data-role": "syndicate-name"}, "this syndicate"),
          ". Any seat you're currently holding on an upcoming match goes back to the "
          "bench for someone else to claim."),
        h("button", {"cls": "btn btn--primary btn--block", "type": "button",
                     "style": {"marginTop": "6px", "background": "var(--summit-sandstone)"},
                     "data-role": "post-leave-syndicate"}, "Leave syndicate"),
        h("p", {"id": "leave-syndicate-error", "role": "alert", "hidden": True, "style": {
            "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)", "textAlign": "center"}}),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-close-sheet": "true"}, "Never mind"),
    ])
