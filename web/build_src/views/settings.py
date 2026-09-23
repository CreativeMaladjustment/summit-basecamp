"""Campfire Settings: all three device-banner variants, both toggle states,
all three bio-scope options and their preview text are pre-rendered here;
src/app.js only picks which is visible.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h, Raw
from icons import svg
from components import toggle
from fmt import label12
from data import SYNDICATES

SCOPES = [
    ("home_first", "Home Squad First",
     "Mostly Denver Summit FC starters and prospects, with marquee visiting stars leading up to matchday."),
    ("summit_only", "Summit FC Only", "Exclusively our home squad roster."),
    ("full_nwsl", "Full NWSL Circuit", "Equal mix across all league teams."),
]
TIMES = ["07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "17:00", "18:00"]


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "settings"},
        h("h1", {"style": {"fontSize": "22px", "fontWeight": "800"}}, "Campfire Settings"),
        h("p", {"style": {"margin": "4px 0 14px", "fontSize": "14px", "color": "var(--ink-mute)"}},
          "What reaches you, when, and on which device."),
        device_banners(),
        h("div", {"cls": "grid-auto", "style": {"alignItems": "start"}},
          matchday_section(), notes_section(), profile_section(), invite_section(), preview_section()),
    )


def device_banners():
    ios = h(
        "div", {"cls": "card", "style": {"borderLeft": "3px solid var(--summit-sandstone)",
                                          "background": "rgba(200,75,49,.08)", "marginBottom": "12px"},
                 "data-device-banner": "ios-safari", "hidden": True},
        h("div", {"style": {"display": "flex", "gap": "10px"}},
          Raw(svg("share", size=20, stroke="var(--summit-sandstone)")),
          h("p", {"style": {"margin": "0", "fontSize": "14px", "color": "var(--ink-soft)"}},
            "To get instant alerts on iPhone, tap ", h("strong", None, "Share"),
            " (box with arrow) and select ", h("strong", None, "Add to Home Screen"),
            ", then open the app from your home screen to enable push notifications.")),
    )
    # `paintDeviceBanner()` in app.js swaps the visible banner once it can
    # check the device and `state.prefs.pushEnabled` (default false), so
    # pre-render "prompt" visible to match that default rather than "active"
    # — otherwise a user without JS, or in the instant before it runs, sees
    # "Notifications Active" when nothing is actually enabled yet.
    prompt = h(
        "div", {"cls": "card", "style": {"marginBottom": "12px"}, "data-device-banner": "prompt", "hidden": False},
        h("button", {"cls": "btn btn--primary btn--block", "type": "button", "data-role": "enable-push"},
          "Enable Push Notifications"),
    )
    active = h(
        "div", {"cls": "card", "style": {"marginBottom": "12px"}, "data-device-banner": "active", "hidden": True},
        h("div", {"style": {"display": "flex", "alignItems": "center", "gap": "10px"}},
          h("span", {"aria-hidden": "true", "style": {"width": "10px", "height": "10px", "borderRadius": "50%",
                                                        "background": "#16A34A", "flex": "none"}}),
          h("p", {"style": {"margin": "0", "fontWeight": "600"}}, "Notifications Active")),
    )
    return h("div", None, ios, prompt, active)


def matchday_section():
    return h(
        "section", {"cls": "card"},
        h("h2", {"cls": "card__title"}, "Matchday & roster alerts"),
        h("div", {"cls": "setting-row"},
          h("div", {"cls": "setting-row__body"},
            h("p", {"cls": "setting-row__label"}, "3-Day Roster Check-in"),
            h("p", {"cls": "setting-row__help"},
              "Get a notification 72 hours before kickoff to confirm you're attending or call a sub before the Bench fills up."),
            h("div", {"id": "checkin-time-row"},
              h("label", {"style": {"display": "block", "marginTop": "10px"}},
                h("span", {"cls": "field__label"}, "Delivered at"),
                h("select", {"cls": "select", "style": {"maxWidth": "160px"}, "id": "checkin-time"},
                  [h("option", {"value": t, "selected": t == "10:00"}, label12(t)) for t in TIMES])))),
          toggle(True, "3-Day Roster Check-in", "checkin3Day")),
        h("div", {"cls": "setting-row"},
          h("div", {"cls": "setting-row__body"},
            h("p", {"cls": "setting-row__label"}, "Emergency Bench Alerts"),
            h("p", {"cls": "setting-row__help"},
              "Immediate ping whenever a syndicate member calls a sub or lists a ticket in the Firepit.")),
          toggle(True, "Emergency Bench Alerts", "benchAlerts", ember=True)),
    )


def notes_section():
    radios = [
        h("button", {"cls": "path", "type": "button", "role": "radio",
                      "aria-checked": "true" if v == "home_first" else "false",
                      "data-role": "bio-scope", "data-value": v,
                      "style": {"borderColor": "var(--summit-green)", "background": "var(--surface-sunk)"} if v == "home_first" else {}},
           h("div", None, h("p", {"cls": "path__name", "style": {"margin": "0"}}, label),
             h("p", {"cls": "path__help"}, help_text)))
        for v, label, help_text in SCOPES
    ]
    return h(
        "section", {"cls": "card"},
        h("h2", {"cls": "card__title"}, "Summit Touchline"),
        h("div", {"cls": "setting-row"},
          h("div", {"cls": "setting-row__body"},
            h("p", {"cls": "setting-row__label"}, "Daily Player Bio & Lore"),
            h("p", {"cls": "setting-row__help"}, "Receive one daily flashcard profile to learn league players and tactical matchups.")),
          toggle(True, "Daily Player Bio and Lore", "dailyBio")),
        h("div", {"id": "bio-scope-block"},
          h("div", {"role": "radiogroup", "aria-label": "Which players you see", "style": {"marginTop": "12px"}}, radios),
          h("label", {"style": {"display": "block", "marginTop": "6px"}},
            h("span", {"cls": "field__label"}, "Preferred delivery time"),
            h("select", {"cls": "select", "style": {"maxWidth": "160px"}, "id": "bio-time"},
              [h("option", {"value": t, "selected": t == "08:00"}, label12(t)) for t in TIMES]))),
    )


def profile_section():
    syn = SYNDICATES[0]
    seat = syn["seats"][0]
    return h(
        "section", {"cls": "card"},
        h("h2", {"cls": "card__title"}, "Group & profile"),
        h("label", {"cls": "field"},
          h("span", {"cls": "field__label"}, "Display name"),
          h("input", {"cls": "input", "value": "You", "id": "display-name"})),
        h("div", {"cls": "card card--sunk", "style": {"marginBottom": "12px"}},
          h("p", {"cls": "eyebrow"}, "Seat assignment"),
          h("p", {"data-role": "seat-assignment", "style": {"margin": "4px 0 0", "fontWeight": "600"}},
            f'Sec {seat["section"]}, Row {seat["row"]}, Seat {seat["number"]}'),
          h("p", {"data-role": "syndicate-name",
                  "style": {"margin": "2px 0 0", "fontSize": "13px", "color": "var(--ink-mute)",
                            "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"}}, syn["name"])),
        h("p", {"style": {"margin": "0 0 10px", "fontSize": "13px", "color": "var(--ink-mute)"}},
          "Fallback contacts, used only for critical ticket transfers."),
        h("label", {"cls": "field"}, h("span", {"cls": "field__label"}, "Phone"),
          h("input", {"cls": "input", "type": "tel", "placeholder": "(303) 555-0142", "id": "phone"})),
        h("label", {"cls": "field"}, h("span", {"cls": "field__label"}, "Email"),
          h("input", {"cls": "input", "type": "email", "placeholder": "you@example.com", "id": "email"})),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "data-role": "sign-out"}, "Sign out"),
    )


def invite_section():
    """The code itself and the copy button are useful to any member; only an
    admin can actually generate a new one (rotate_invite_code is admin-only
    server-side), so that button starts hidden and app.js's
    paintRealSyndicateDetail() reveals it once it knows this device's role in
    the real syndicate. The code text starts as a placeholder for the same
    reason the rest of this app does -- it's real, per-syndicate data that
    doesn't exist until the API answers."""
    return h(
        "section", {"cls": "card"},
        h("h2", {"cls": "card__title"}, "Invite your circle"),
        h("p", {"style": {"margin": "0 0 12px", "fontSize": "13px", "color": "var(--ink-mute)"}},
          "Share this code so someone can join on Find-your-syndicate. Anyone who knows the "
          "site password and this code can get in -- treat it like a shared key, not a public link."),
        h("div", {"cls": "card card--sunk", "style": {
            "display": "flex", "alignItems": "center", "justifyContent": "space-between",
            "gap": "10px", "marginBottom": "10px"}},
          h("span", {"id": "invite-code-display", "style": {
              "fontFamily": "var(--font-mono)", "fontWeight": "700", "fontSize": "18px",
              "letterSpacing": ".02em"}}, "Loading…"),
          h("button", {"cls": "btn btn--ghost", "type": "button", "data-role": "copy-invite-code"}, "Copy")),
        h("p", {"id": "invite-code-status", "role": "status", "hidden": True, "style": {
            "margin": "0 0 10px", "fontSize": "13px", "color": "var(--summit-green)"}}),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button",
                     "id": "rotate-invite-code", "data-role": "rotate-invite-code", "hidden": True},
          "Generate a new code"),
        h("p", {"style": {"margin": "8px 0 0", "fontSize": "12px", "color": "var(--ink-mute)"}},
          "Generating a new code immediately stops the old one from working."),
    )


def preview_section():
    def lock_card(title, body, when_id):
        return h(
            "div", {"cls": "card card--sunk", "style": {"marginBottom": "10px", "borderRadius": "14px"}},
            h("div", {"style": {"display": "flex", "justifyContent": "space-between", "gap": "8px"}},
              h("p", {"style": {"margin": "0", "fontWeight": "700", "fontSize": "14px"}}, title),
              h("span", {"cls": "eyebrow", "id": when_id}, "")),
            h("p", {"style": {"margin": "6px 0 0", "fontSize": "13px", "color": "var(--ink-soft)"}}, body),
        )
    return h(
        "section", {"cls": "card"},
        h("h2", {"cls": "card__title"}, "Sample alert preview"),
        lock_card("🏔️ Match Check-in",
                   "Denver Summit FC vs. Portland Thorns is in 3 days. Are you taking the pitch? [ Confirm Seat ] or [ Call a Sub ]",
                   "preview-checkin-time"),
        lock_card("⚽ Touchline Scout",
                   "Meet visiting forward Marisol Vega (Portland Thorns) — 3 key stats & tactical tendencies ahead of Saturday's clash.",
                   "preview-bio-time"),
        h("p", {"style": {"margin": "4px 0 0", "fontSize": "12px", "color": "var(--ink-mute)"}, "id": "preview-scope-label"}, ""),
    )
