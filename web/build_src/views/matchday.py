"""Matchday: the next-fixture hero, Summit Touchline carousel, bench-note
threads and the balance strip.

The hero, bench notes and balance strip are real per-syndicate data (which
fixture is next, who holds which seat, real bench notes) that does not
exist until a real syndicate does, so none of it can be pre-rendered at
build time the way the rest of this static site is -- web/src/app.js's
paintRealFixtures() builds it at runtime from GET /api/groups/{id}/fixtures,
.../bench-notes and the seat/ledger data paintRealSyndicateDetail already
fetched. This module only emits the empty shell those functions fill in.
The Summit Touchline carousel is unrelated daily content (trivia/player/
tactics notes), not fixture data, and stays fully pre-rendered.
"""
from __future__ import annotations

from markup import h, Raw
from icons import svg
from components import badge
from data import TOUCHLINE_NOTES


def render():
    return h(
        "div", {"cls": "view shell", "style": {"paddingTop": "16px"}, "data-tab": "matchday"},
        h("div", {"cls": "grid-auto", "style": {"gridTemplateColumns": "repeat(auto-fit, minmax(320px, 1fr))"}},
          h("article", {"id": "matchday-hero", "cls": "card"},
            h("p", {"style": {"margin": "0", "color": "var(--ink-mute)"}}, "Loading your next match…")),
          touchline_notes_card()),
        h("section", {"style": {"marginTop": "12px"}, "id": "bench-notes-section", "hidden": True},
          h("h2", {"style": {"fontSize": "15px", "margin": "0 0 8px"}}, "Bench notes"),
          h("div", {"cls": "grid-auto", "id": "bench-notes-list"})),
        h("button", {"cls": "card", "type": "button", "id": "matchday-balance-strip", "style": {
            "marginTop": "12px", "width": "100%", "textAlign": "left", "cursor": "pointer",
            "borderLeft": "3px solid var(--summit-sunshine)", "display": "flex", "alignItems": "center",
            "justifyContent": "space-between", "gap": "12px"}, "data-role": "goto-hearth", "hidden": True},
          h("div", None, h("p", {"cls": "eyebrow"}, "The 14ers"),
            h("p", {"data-role": "matchday-balance-text", "style": {
                "margin": "4px 0 0", "fontFamily": "var(--font-display)", "fontWeight": "700", "fontSize": "16px"}})),
          Raw(svg("arrowRight", size=18))),
    )


def touchline_notes_card():
    slides = []
    for i, note in enumerate(TOUCHLINE_NOTES):
        slides.append(h(
            "div", {"style": {"animation": "ssPop .2s ease both"}, "data-carousel-slide": str(i),
                     "hidden": i != 0}, _note_body(note)),
        )

    dots = h(
        "div", {"style": {"display": "flex", "gap": "6px"}, "data-role": "carousel-dots"},
        [h("span", {"aria-hidden": "true", "data-carousel-dot": str(i), "style": {
            "width": "18px" if i == 0 else "6px", "height": "6px", "borderRadius": "999px",
            "background": "var(--summit-green)" if i == 0 else "var(--hairline-strong)",
            "transition": "width .2s ease"}}) for i in range(len(TOUCHLINE_NOTES))],
    )

    return h(
        "article", {"cls": "card", "style": {"display": "flex", "flexDirection": "column"},
                     "data-role": "touchline-carousel", "data-count": str(len(TOUCHLINE_NOTES))},
        h("div", {"style": {"display": "flex", "alignItems": "center", "gap": "8px"}},
          Raw(svg("flame", size=16, stroke="var(--summit-sandstone)")),
          h("p", {"cls": "eyebrow"}, "Summit Touchline")),
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
