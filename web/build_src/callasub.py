"""Call a Sub sheet templates: the three pathways, plus their forms.

One reusable sheet set for the whole app, not one baked per mock fixture --
which real seat a Call a Sub applies to varies per syndicate and isn't known
at build time, so web/src/app.js repaints this same set's context line,
face-value label and target seat right before opening it (the same pattern
Settle Up already uses for its amount/memo). The "post" buttons carry no
fixture/seat data of their own; app.js's own module-level state tracks
which seat is currently the target.
"""
from __future__ import annotations

from markup import h, Raw
from icons import svg
from layout import sheet_template


def _path(icon, tint, name, help_text, open_sheet_id):
    return h(
        "button", {"cls": "path", "type": "button", "data-open-sheet": open_sheet_id},
        h("div", {"cls": "path__icon", "style": {"background": tint}}, Raw(svg(icon, size=19, stroke="#fff"))),
        h("div", None,
          h("p", {"cls": "path__name", "style": {"margin": "0"}}, name),
          h("p", {"cls": "path__help"}, help_text)),
    )


def _cost_choice(value, title, help_text, checked, title_id=None):
    title_attrs = {"cls": "path__name", "style": {"margin": "0"}}
    if title_id:
        title_attrs["id"] = title_id
    return h(
        "button", {"cls": "path", "type": "button", "data-cost-choice": value,
                   "aria-pressed": "true" if checked else "false",
                   "style": {"borderColor": "var(--summit-green)", "background": "var(--surface-sunk)"} if checked else {}},
        h("div", None, h("p", title_attrs, title),
          h("p", {"cls": "path__help"}, help_text)),
    )


def build():
    """Returns the four sheet_template nodes -- root, release, guest, list."""
    root = sheet_template("sheet-callasub", [
        h("p", {"cls": "eyebrow", "id": "callasub-context"}, ""),
        h("h2", {"cls": "sheet__title"}, "Call a sub"),
        h("p", {"cls": "sheet__sub"}, "Pick how the seat leaves your hands. Nothing moves on the tab until you confirm."),
        _path("users", "#134E48", "Release to the Bench",
              "Pings the circle to see who wants to step onto the pitch.", "sheet-release"),
        _path("gift", "#1D6960", "Send to Guest",
              "Direct transfer to someone outside the circle. The seat stays accounted for.", "sheet-guest"),
        _path("tag", "#C84B31", "List Outside the 14ers",
              "Flag it for SeatGeek or Ticketmaster at a target face value.", "sheet-list"),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "data-close-sheet": "true"}, "Never mind"),
    ])

    release = sheet_template("sheet-release", [
        h("p", {"cls": "eyebrow", "id": "release-context"}, ""),
        h("h2", {"cls": "sheet__title"}, "Release to the Bench"),
        h("p", {"cls": "sheet__sub"}, "Leave a note for the circle. Anyone can reply, and whoever takes it steps onto the pitch."),
        h("label", {"cls": "field__label", "for": "release-note"}, "Note to the circle"),
        h("textarea", {"cls": "textarea", "id": "release-note",
                        "placeholder": "Out of town that weekend — seat's free if anyone wants it."}),
        h("p", {"cls": "field__label", "style": {"marginTop": "10px"}}, "Cost"),
        h("div", {"role": "group", "aria-label": "Cost", "data-role": "cost-group"},
          _cost_choice("repay", "Get paid back", "Face value moves to whoever takes the seat.", True, title_id="cost-repay-label"),
          _cost_choice("free", "On the house · no cost", "You eat it. Nobody's tab moves.", False)),
        h("p", {"id": "release-error", "role": "alert", "hidden": True, "style": {
            "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)"}}),
        h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "6px"},
                     "data-role": "post-release"}, "Post to the Bench"),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-open-sheet": "sheet-callasub"}, "Back"),
    ])

    guest = sheet_template("sheet-guest", [
        h("p", {"cls": "eyebrow", "id": "guest-context"}, ""),
        h("h2", {"cls": "sheet__title"}, "Send to Guest"),
        h("p", {"cls": "sheet__sub"}, "A straight gift. The seat stays accounted for and nobody's tab moves."),
        h("label", {"cls": "field__label", "for": "guest-name"}, "Who is taking it"),
        h("input", {"cls": "input", "id": "guest-name", "placeholder": "Name or email"}),
        h("p", {"id": "guest-error", "role": "alert", "hidden": True, "style": {
            "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)"}}),
        h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "12px"},
                     "data-role": "post-guest"}, "Send the seat"),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-open-sheet": "sheet-callasub"}, "Back"),
    ])

    list_ = sheet_template("sheet-list", [
        h("p", {"cls": "eyebrow", "id": "list-context"}, ""),
        h("h2", {"cls": "sheet__title"}, "List Outside the 14ers"),
        h("p", {"cls": "sheet__sub"}, "Flags the seat as listed on an external exchange. You still handle the listing there."),
        h("label", {"cls": "field__label", "for": "ask-price"}, "Target face value (USD)"),
        h("input", {"cls": "input", "id": "ask-price", "type": "number", "min": "0", "step": "1"}),
        h("p", {"id": "list-error", "role": "alert", "hidden": True, "style": {
            "margin": "10px 0 0", "fontSize": "13px", "color": "var(--summit-sandstone)"}}),
        h("button", {"cls": "btn btn--ember btn--block", "type": "button", "style": {"marginTop": "12px"},
                     "data-role": "post-list"}, "Mark as listed"),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-open-sheet": "sheet-callasub"}, "Back"),
    ])

    return [root, release, guest, list_]
