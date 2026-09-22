"""Landing and 'find your syndicate' — the two-step entry flow ahead of the
app. Both are always in the DOM; src/app.js shows exactly one of the three
stages (landing / syndicate / app) based on a localStorage flag.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markup import h, Raw
from icons import svg
from layout import lockup
from components import badge
from data import SYNDICATES, TOUCHLINE_NOTES


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
          h("div", {"style": {"marginTop": "24px"}},
            h("button", {"cls": "btn btn--primary btn--block", "type": "button", "data-role": "sign-in", "data-provider": "google"},
              "Continue with Google"),
            h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "10px"},
                         "data-role": "sign-in", "data-provider": "apple"}, "Continue with Apple"),
            h("p", {"style": {"margin": "14px 0 0", "fontSize": "13px", "color": "var(--ink-mute)", "textAlign": "center"}},
              "Sign-in runs on OIDC through Google and Apple. No passwords, and nothing for us to lose."))),
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
                         "data-role": "join-syndicate", "data-syndicate": SYNDICATES[0]["id"]}, "Join with code")),
          h("p", {"cls": "eyebrow", "style": {"marginTop": "22px"}}, "You've been invited to"),
          h("div", {"style": {"marginTop": "10px"}},
            [h("button", {"cls": "path", "type": "button", "data-role": "join-syndicate", "data-syndicate": s["id"]},
               h("div", {"cls": "path__icon", "style": {"background": "#134E48"}}, Raw(svg("users", size=19, stroke="#fff"))),
               h("div", None, h("p", {"cls": "path__name", "style": {"margin": "0"}}, s["name"]),
                 h("p", {"cls": "path__help"}, f'{s["holds"]} · invited by {s["invited_by"]}')))
             for s in SYNDICATES]),
          h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "10px"},
                       "data-role": "start-new-syndicate"}, "Start a new syndicate")),
    )
