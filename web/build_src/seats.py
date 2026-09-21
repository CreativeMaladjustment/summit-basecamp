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

    A seat held by you is pre-rendered in both states a Call a Sub
    submission can reach: held (current) and released (generic "on the
    bench" — the note itself is dynamic and lives in the bench-note card
    instead, so the hero doesn't need three separate release-path variants).
    Any other seat shows its current, non-interactive status only.
    """
    label_style = {"color": "#fff"} if on_dark else {}
    mute_style = {"color": "rgba(255,255,255,.62)"} if on_dark else {"color": "var(--ink-mute)"}

    if seat["holder"] == ME:
        key = seat_key(fixture["id"], seat["number"])
        held = h("span", {"data-seat": key, "data-state": "held"},
                 _seat_line(fixture, seat, lg, label_style, mute_style, MEMBERS[ME]["name"]))
        released = h("span", {"data-seat": key, "data-state": "released", "hidden": True},
                      _seat_line(fixture, {**seat, "holder": None}, lg, label_style, mute_style, "On the bench"))
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
    every occurrence of this seat."""
    key = seat_key(fixture["id"], seat["number"])
    if not is_claimable(seat):
        return avatar(seat["holder"])
    return h(
        "span", None,
        h("span", {"data-seat": key, "data-state": "open"}, avatar(None)),
        h("span", {"data-seat": key, "data-state": "claimed", "hidden": True}, avatar(ME)),
    )
