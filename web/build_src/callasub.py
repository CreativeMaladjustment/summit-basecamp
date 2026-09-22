"""Call a Sub sheet templates: the three pathways, plus their forms.

Note text, guest name and list price are free-form user input, so those
forms' *submission* is the one place src/app.js builds new DOM at runtime —
everything here is the static shell around that.
"""
from __future__ import annotations

from markup import h, Raw
from icons import svg
from layout import sheet_template
from fmt import money
from data import ME


def sheet_ids(fixture_id, seat_number):
    key = f"{fixture_id}-{seat_number}"
    return {
        "root": f"sheet-callasub-{key}",
        "release": f"sheet-release-{key}",
        "guest": f"sheet-guest-{key}",
        "list": f"sheet-list-{key}",
    }


def _path(icon, tint, name, help_text, open_sheet_id):
    return h(
        "button", {"cls": "path", "type": "button", "data-open-sheet": open_sheet_id},
        h("div", {"cls": "path__icon", "style": {"background": tint}}, Raw(svg(icon, size=19, stroke="#fff"))),
        h("div", None,
          h("p", {"cls": "path__name", "style": {"margin": "0"}}, name),
          h("p", {"cls": "path__help"}, help_text)),
    )


def build(fixture):
    """Returns (ids, [sheet_template nodes...]) for one held seat's Call a Sub flow."""
    seat = next(s for s in fixture["seats"] if s["holder"] == ME)
    ids = sheet_ids(fixture["id"], seat["number"])
    face = fixture["value_cents"]
    seat_key = f'{fixture["id"]}-{seat["number"]}'

    root = sheet_template(ids["root"], [
        h("p", {"cls": "eyebrow"}, f'{fixture["opponent"]} · Seat {seat["number"]}'),
        h("h2", {"cls": "sheet__title"}, "Call a sub"),
        h("p", {"cls": "sheet__sub"}, "Pick how the seat leaves your hands. Nothing moves on the tab until you confirm."),
        _path("users", "#134E48", "Release to the Bench",
              "Pings the circle to see who wants to step onto the pitch.", ids["release"]),
        _path("gift", "#1D6960", "Send to Guest",
              "Direct transfer to someone outside the circle. The seat stays accounted for.", ids["guest"]),
        _path("tag", "#C84B31", "List Outside the 14ers",
              "Flag it for SeatGeek or Ticketmaster at a target face value.", ids["list"]),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "data-close-sheet": "true"}, "Never mind"),
    ])

    def cost_choice(value, title, help_text, checked):
        return h(
            "button", {"cls": "path", "type": "button", "data-cost-choice": value,
                       "aria-pressed": "true" if checked else "false",
                       "style": {"borderColor": "var(--summit-green)", "background": "var(--surface-sunk)"} if checked else {}},
            h("div", None, h("p", {"cls": "path__name", "style": {"margin": "0"}}, title),
              h("p", {"cls": "path__help"}, help_text)),
        )

    release = sheet_template(ids["release"], [
        h("p", {"cls": "eyebrow"}, f'{fixture["opponent"]} · Seat {seat["number"]}'),
        h("h2", {"cls": "sheet__title"}, "Release to the Bench"),
        h("p", {"cls": "sheet__sub"}, "Leave a note for the circle. Anyone can reply, and whoever takes it steps onto the pitch."),
        h("label", {"cls": "field__label", "for": f'release-note-{seat_key}'}, "Note to the circle"),
        h("textarea", {"cls": "textarea", "id": f'release-note-{seat_key}',
                        "placeholder": "Out of town that weekend — seat's free if anyone wants it."}),
        h("p", {"cls": "field__label", "style": {"marginTop": "10px"}}, "Cost"),
        h("div", {"role": "group", "aria-label": "Cost", "data-role": "cost-group"},
          cost_choice("repay", f"Get paid back · {money(face)}", "Face value moves to whoever takes the seat.", True),
          cost_choice("free", "On the house · no cost", "You eat it. Nobody's tab moves.", False)),
        h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "6px"},
                     "data-role": "post-release", "data-fixture": fixture["id"], "data-seat": str(seat["number"]),
                     "data-opponent": fixture["opponent"], "data-short": fixture["short"], "data-face-cents": str(face)},
          "Post to the Bench"),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-open-sheet": ids["root"]}, "Back"),
    ])

    guest = sheet_template(ids["guest"], [
        h("p", {"cls": "eyebrow"}, f'{fixture["opponent"]} · Seat {seat["number"]}'),
        h("h2", {"cls": "sheet__title"}, "Send to Guest"),
        h("p", {"cls": "sheet__sub"}, "A straight gift. The seat stays accounted for and nobody's tab moves."),
        h("label", {"cls": "field__label", "for": f'guest-name-{seat_key}'}, "Who is taking it"),
        h("input", {"cls": "input", "id": f'guest-name-{seat_key}', "placeholder": "Name or email"}),
        h("button", {"cls": "btn btn--primary btn--block", "type": "button", "style": {"marginTop": "12px"},
                     "data-role": "post-guest", "data-seat": seat_key}, "Send the seat"),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-open-sheet": ids["root"]}, "Back"),
    ])

    list_ = sheet_template(ids["list"], [
        h("p", {"cls": "eyebrow"}, f'{fixture["opponent"]} · Seat {seat["number"]}'),
        h("h2", {"cls": "sheet__title"}, "List Outside the 14ers"),
        h("p", {"cls": "sheet__sub"}, "Flags the seat as listed on an external exchange. You still handle the listing there."),
        h("label", {"cls": "field__label", "for": f'ask-{seat_key}'}, "Target face value (USD)"),
        h("input", {"cls": "input", "id": f'ask-{seat_key}', "type": "number", "min": "0", "step": "1",
                     "value": str(round(face / 100))}),
        h("button", {"cls": "btn btn--ember btn--block", "type": "button", "style": {"marginTop": "12px"},
                     "data-role": "post-list", "data-seat": seat_key}, "Mark as listed"),
        h("button", {"cls": "btn btn--ghost btn--block", "type": "button", "style": {"marginTop": "8px"},
                     "data-open-sheet": ids["root"]}, "Back"),
    ])

    return ids, [root, release, guest, list_]
