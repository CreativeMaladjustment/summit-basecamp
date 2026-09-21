"""Matchday: the next-fixture hero, Hearthside Notes carousel, bench-note
threads and the balance strip. Every seat state that a claim/release can
reach is pre-rendered here; src/app.js only toggles which one shows.
"""
from __future__ import annotations

from markup import h, Raw
from icons import svg
from components import avatar, badge
from fmt import money, match_date, match_time, relative
from data import MEMBERS, ME, HEARTHSIDE_NOTES, QUICK_REPLIES
from seats import seat_pair, claim_button


def render(fixture, bench_notes, my_balance_cents):
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "matchday"},
        h("div", {"cls": "grid-auto", "style": {"gridTemplateColumns": "repeat(auto-fit, minmax(320px, 1fr))"}},
          hero_card(fixture) if fixture else h("div", {"cls": "card"}, "No fixtures left this season."),
          hearthside_notes_card()),
        h("section", {"style": {"marginTop": "12px"}, "id": "bench-notes-section",
                       "hidden": not bench_notes},
          h("h2", {"style": {"fontSize": "15px", "margin": "0 0 8px"}}, "Bench notes"),
          h("div", {"cls": "grid-auto", "id": "bench-notes-list"},
            [note_thread(n, bench_notes) for n in bench_notes])),
        balance_strip(my_balance_cents),
    )


def hero_card(f):
    my_seat = next((s for s in f["seats"] if s["holder"] == ME), None)

    roster = h(
        "div", {"style": {"display": "flex", "alignItems": "center", "gap": "10px", "flexWrap": "wrap", "marginTop": "14px"}},
        [seat_pair(f, seat, lg=True, on_dark=True) for seat in f["seats"]],
    )

    return h(
        "article", {"style": {
            "borderRadius": "var(--radius-lg)", "overflow": "hidden", "background": "#134E48", "color": "#fff",
            "borderTop": "3px solid #C84B31", "padding": "18px 16px", "animation": "ssUp .3s ease both"}},
        h("div", {"style": {"display": "flex", "justifyContent": "space-between", "gap": "10px", "alignItems": "flex-start"}},
          h("div", None,
            h("p", {"cls": "eyebrow", "style": {"color": "rgba(255,255,255,.66)"}}, "Next match"),
            h("h2", {"style": {"fontSize": "24px", "fontWeight": "800", "marginTop": "4px", "color": "#fff"}},
              f'Summit vs {f["opponent"]}'),
            h("p", {"style": {"margin": "6px 0 0", "fontSize": "14px", "color": "rgba(255,255,255,.8)"}},
              f'{match_date(f["kickoff"])} · {match_time(f["kickoff"])} · {f["venue"]}')),
          badge("Rivalry", "gold") if f["tier"] == "rivalry" else None),
        h("p", {"cls": "eyebrow", "style": {"color": "rgba(255,255,255,.66)", "marginTop": "16px"}}, "Taking the pitch"),
        roster,
        h("div", {"style": {"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginTop": "16px"}},
          h("button", {"cls": "btn btn--ember", "type": "button", "data-open-sheet": f'sheet-callasub-{f["id"]}-{my_seat["number"]}'},
            "Call a Sub") if my_seat else None,
          h("a", {"cls": "btn btn--on-dark", "href": "https://www.ticketmaster.com/", "target": "_blank",
                   "rel": "noopener noreferrer"}, Raw(svg("external", size=16)), "Open Official Ticketing App")),
    )


def hearthside_notes_card():
    slides = []
    for i, note in enumerate(HEARTHSIDE_NOTES):
        slides.append(h(
            "div", {"style": {"animation": "ssPop .2s ease both"}, "data-carousel-slide": str(i),
                     "hidden": i != 0}, _note_body(note)),
        )

    dots = h(
        "div", {"style": {"display": "flex", "gap": "6px"}, "data-role": "carousel-dots"},
        [h("span", {"aria-hidden": "true", "data-carousel-dot": str(i), "style": {
            "width": "18px" if i == 0 else "6px", "height": "6px", "borderRadius": "999px",
            "background": "var(--summit-green)" if i == 0 else "var(--hairline-strong)",
            "transition": "width .2s ease"}}) for i in range(len(HEARTHSIDE_NOTES))],
    )

    return h(
        "article", {"cls": "card", "style": {"display": "flex", "flexDirection": "column"},
                     "data-role": "hearthside-carousel", "data-count": str(len(HEARTHSIDE_NOTES))},
        h("div", {"style": {"display": "flex", "alignItems": "center", "gap": "8px"}},
          Raw(svg("flame", size=16, stroke="var(--summit-sandstone)")),
          h("p", {"cls": "eyebrow"}, "Hearthside Notes")),
        h("div", {"style": {"flex": "1", "marginTop": "10px"}}, slides),
        h("div", {"style": {"display": "flex", "alignItems": "center", "justifyContent": "space-between",
                             "marginTop": "14px", "gap": "10px"}},
          dots,
          h("div", {"style": {"display": "flex", "gap": "6px"}},
            h("button", {"cls": "btn btn--ghost", "type": "button", "style": {"minHeight": "36px", "padding": "0 12px"},
                         "aria-label": "Previous note", "data-carousel": "prev"}, "‹"),
            h("button", {"cls": "btn btn--ghost", "type": "button", "style": {"minHeight": "36px", "padding": "0 12px"},
                         "aria-label": "Next note", "data-carousel": "next"}, "›"))),
    )


def _note_body(note):
    if note["kind"] == "player":
        return h(
            "div", {"style": {"display": "flex", "gap": "12px"}},
            h("div", {"aria-hidden": "true", "style": {
                "width": "64px", "height": "64px", "borderRadius": "12px", "flex": "none",
                "background": "repeating-linear-gradient(135deg, var(--surface-sunk) 0 8px, var(--hairline) 8px 16px)"}}),
            h("div", None,
              h("p", {"cls": "eyebrow"}, note["eyebrow"]),
              h("p", {"style": {"margin": "4px 0 0", "display": "flex", "alignItems": "center", "gap": "8px"}},
                badge(f'#{note["num"]}', "gold"),
                h("strong", {"style": {"fontFamily": "var(--font-display)", "fontSize": "16px"}}, note["name"])),
              h("p", {"style": {"margin": "2px 0 0", "fontSize": "12px", "color": "var(--ink-mute)"}}, note["pos"]),
              h("p", {"style": {"margin": "8px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}}, note["body"])),
        )
    if note["kind"] == "tactics":
        return h(
            "div", None,
            h("p", {"cls": "eyebrow"}, note["eyebrow"]),
            h("p", {"style": {"margin": "6px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "16px"}}, note["name"]),
            h("p", {"style": {"margin": "8px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}}, note["body"]),
        )
    # Trivia: both reveal states pre-rendered, toggled by app.js.
    return h(
        "div", None,
        h("p", {"cls": "eyebrow"}, note["eyebrow"]),
        h("p", {"style": {"margin": "6px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "16px"}}, note["question"]),
        h("p", {"style": {"margin": "10px 0 0", "fontSize": "14px", "color": "var(--ink-soft)"}, "hidden": True,
                "data-role": "trivia-answer"}, note["answer"]),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "10px"},
                     "aria-expanded": "false", "data-role": "trivia-toggle"}, "Tap to reveal"),
    )


def note_thread(note, all_notes):
    from data import FIXTURES
    fixture = next((f for f in FIXTURES if f["id"] == note["fixture_id"]), None)
    seat = next((s for s in fixture["seats"] if s["number"] == note["seat_number"]), None) if fixture else None
    author = MEMBERS[note["author_id"]]
    taken = seat is not None and seat["status"] == "confirmed"
    seat_key = f'{note["fixture_id"]}-{note["seat_number"]}'

    replies_block = h(
        "div", {"style": {"marginTop": "12px", "borderLeft": "2px solid var(--hairline)", "paddingLeft": "10px"},
                 "id": f'replies-{note["id"]}', "hidden": not note["replies"]},
        [h("p", {"style": {"margin": "0 0 6px", "fontSize": "14px"}},
           h("strong", None, f'{MEMBERS.get(r["author_id"], {}).get("name", "Someone")}: '), r["body"])
         for r in note["replies"]],
    )

    taken_line = h(
        "p", {"style": {"margin": "12px 0 0", "fontSize": "14px", "color": "var(--summit-green)", "fontWeight": "600"},
              "id": f'taken-line-{note["id"]}', "hidden": not taken},
        f'{MEMBERS.get(seat["holder"], {}).get("name", "Someone") if taken else ""} took the seat.',
    )

    active_controls = h(
        "div", {"id": f'active-controls-{note["id"]}', "hidden": taken},
        h("div", {"cls": "scroll-row", "style": {"marginTop": "12px"}},
          [h("button", {"cls": "chip", "type": "button", "data-quick-reply": note["id"], "data-text": q}, q)
           for q in QUICK_REPLIES]),
        h("div", {"style": {"display": "flex", "gap": "8px", "marginTop": "10px"}},
          h("input", {"cls": "input", "placeholder": "Reply to the circle", "aria-label": "Reply",
                       "id": f'reply-input-{note["id"]}'}),
          h("button", {"cls": "btn btn--ghost", "type": "button", "style": {"flex": "none"},
                       "data-role": "send-reply", "data-note": note["id"]}, "Send")),
        claim_button(
            "Take the Pitch · " + (money(note["amount_cents"]) if note["cost_path"] == "repay" else "no cost"),
            seat_key, cls="btn btn--primary btn--block", style={"marginTop": "10px"},
            extra={"data-hand-off": note["id"]},
        ),
    )

    return h(
        "article", {"cls": "card", "id": f'note-{note["id"]}', "data-note-card": note["id"]},
        h("div", {"style": {"display": "flex", "justifyContent": "space-between", "gap": "8px", "alignItems": "flex-start"}},
          h("div", {"style": {"display": "flex", "gap": "10px"}},
            avatar(note["author_id"]),
            h("div", None,
              h("p", {"style": {"margin": "0", "fontWeight": "600", "fontSize": "14px"}},
                f'{author["name"]} · {fixture["short"] if fixture else ""} · Seat {note["seat_number"]}'),
              h("p", {"cls": "eyebrow", "style": {"marginTop": "2px"}}, relative(note["posted_at"]))),
            ),
          badge(f'Get paid back · {money(note["amount_cents"])}', "green") if note["cost_path"] == "repay" else badge("On the house", "gold")),
        h("p", {"style": {"margin": "10px 0 0", "fontSize": "15px"}}, note["body"]),
        replies_block, taken_line, active_controls,
    )


def balance_strip(cents):
    line = "All warm at the Hearth." if cents == 0 else (
        f"The circle holds your {money(cents)}." if cents > 0 else f"You hold the tab ({money(abs(cents))})."
    )
    return h(
        "button", {"cls": "card", "type": "button", "style": {
            "marginTop": "12px", "width": "100%", "textAlign": "left", "cursor": "pointer",
            "borderLeft": "3px solid var(--summit-sunshine)", "display": "flex", "alignItems": "center",
            "justifyContent": "space-between", "gap": "12px"}, "data-role": "goto-hearth"},
        h("div", None, h("p", {"cls": "eyebrow"}, "The Hearth"),
          h("p", {"style": {"margin": "4px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "16px"}}, line)),
        Raw(svg("arrowRight", size=18)),
    )
