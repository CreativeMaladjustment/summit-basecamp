"""Shared seat markup. A claimable seat (currently on the bench or listed)
is pre-rendered in both states it can reach — open and claimed by you — and
src/app.js flips which one shows, wherever that seat appears. This is the
one bit of cross-view plumbing every screen that shows a seat shares."""
from __future__ import annotations

from markup import h
from components import avatar
from data import MEMBERS, ME


def seat_key(fixture_id, seat_number):
    return f"{fixture_id}-{seat_number}"


def is_claimable(seat):
    return seat["status"] in ("bench", "listed")


def claim_button(label, key, cls="btn btn--primary", style=None, extra=None):
    attrs = {"cls": cls, "type": "button", "data-claim-seat": key}
    if style:
        attrs["style"] = style
    if extra:
        attrs.update(extra)
    return h("button", attrs, label)


def _seat_line(fixture, seat, lg, label_style, mute_style, name):
    return h(
        "div", {"style": {"display": "flex", "alignItems": "center", "gap": "8px"}},
        avatar(seat["holder"], lg=lg),
        h("div", None,
          h("p", {"style": {"margin": "0", "fontSize": "13px", "fontWeight": "600", **label_style}}, name),
          h("p", {"style": {"margin": "0", "fontSize": "11px", "fontFamily": "var(--font-mono)", **mute_style}},
            f'Seat {seat["number"]}')),
    )


def seat_pair(fixture, seat, lg=False, on_dark=False):
    """The hero's roster display.

    A seat held by you is pre-rendered in every state a Call a Sub
    submission can reach: held (current), plus one released variant per
    outcome — released to the bench, gifted, or listed outside — so the
    hero's wording actually matches what happened rather than collapsing
    every outcome into a generic "on the bench". The outer key (held vs.
    vacated) stays shared with the Pitch avatar strip and action row, which
    only care whether the seat is still held; the outcome-specific text is
    a nested toggle on its own `{key}:reason` key so those simpler widgets
    aren't forced to grow three states of their own.
    Any other seat shows its current, non-interactive status only.
    """
    label_style = {"color": "#fff"} if on_dark else {}
    mute_style = {"color": "rgba(255,255,255,.62)"} if on_dark else {"color": "var(--ink-mute)"}

    if seat["holder"] == ME:
        key = seat_key(fixture["id"], seat["number"])
        reason_key = f'{key}:reason'
        vacated_seat = {**seat, "holder": None}
        held = h("span", {"data-seat": key, "data-state": "held"},
                 _seat_line(fixture, seat, lg, label_style, mute_style, MEMBERS[ME]["name"]))
        reasons = h(
            "span", None,
            h("span", {"data-seat": reason_key, "data-state": "released"},
              _seat_line(fixture, vacated_seat, lg, label_style, mute_style, "On the bench")),
            h("span", {"data-seat": reason_key, "data-state": "gifted", "hidden": True},
              _seat_line(fixture, vacated_seat, lg, label_style, mute_style, "Sent to a guest")),
            h("span", {"data-seat": reason_key, "data-state": "listed", "hidden": True},
              _seat_line(fixture, vacated_seat, lg, label_style, mute_style, "Listed outside")),
        )
        released = h("span", {"data-seat": key, "data-state": "released", "hidden": True}, reasons)
        return h("span", None, held, released)

    name = (
        MEMBERS[seat["holder"]]["name"] if seat["holder"]
        else (seat.get("guest_name") or "Guest") if seat["status"] == "gifted"
        else "Listed outside" if seat["status"] == "listed"
        else "On the bench"
    )
    return _seat_line(fixture, seat, lg, label_style, mute_style, name)


def seat_avatar_toggle(fixture, seat):
    """Pitch's avatar strip entry: open (dashed +) vs claimed (You), both
    pre-rendered and keyed to the same data-seat so a claim anywhere updates
    every occurrence of this seat. A seat currently held by you gets the
    same held/released pair Matchday's hero uses (seat_pair), so releasing
    it from Call a Sub updates the Pitch avatar too."""
    key = seat_key(fixture["id"], seat["number"])
    if seat["holder"] == ME:
        return h(
            "span", None,
            h("span", {"data-seat": key, "data-state": "held"}, avatar(ME)),
            h("span", {"data-seat": key, "data-state": "released", "hidden": True}, avatar(None)),
        )
    if not is_claimable(seat):
        return avatar(seat["holder"])
    return h(
        "span", None,
        h("span", {"data-seat": key, "data-state": "open"}, avatar(None)),
        h("span", {"data-seat": key, "data-state": "claimed", "hidden": True}, avatar(ME)),
    )
