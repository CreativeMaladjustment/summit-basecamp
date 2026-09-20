"""Shared markup: avatars, badges, chips, toggle switches, photo slots.

Everything a screen can be in is enumerable here at build time; the two
things that genuinely can't be pre-rendered — a dropped photo and typed
reply text — are left to the small runtime in src/app.js.
"""
from __future__ import annotations

from markup import h, Raw
from icons import svg
from data import MEMBERS


def avatar(member_id, lg=False, empty_label="Open seat"):
    cls = "avatar avatar--lg" if lg else "avatar"
    if member_id is None:
        return h("div", {"cls": f"{cls} avatar--empty", "title": empty_label}, "+")
    m = MEMBERS[member_id]
    return h("div", {"cls": cls, "style": {"background": m["colour"]}, "title": m["name"],
                      "aria-label": m["name"]}, m["initials"])


def badge(text, kind="mute"):
    return h("span", {"cls": f"badge badge--{kind}"}, text)


def chip(label, value, active, extra_cls="", data=None):
    attrs = {"cls": f"chip {extra_cls}".strip(), "type": "button", "role": "tab",
             "aria-selected": "true" if active else "false", "data-value": value}
    if data:
        attrs.update(data)
    return h("button", attrs, label)


def toggle(checked, label, name, ember=False):
    cls = "switch switch--ember" if ember else "switch"
    return h("button", {"cls": cls, "type": "button", "role": "switch",
                         "aria-checked": "true" if checked else "false",
                         "aria-label": label, "data-pref": name})


def photo_slot(player_id, size):
    """Empty state only — a dropped photo is filled in client-side."""
    return h(
        "div",
        {"cls": "photo-slot", "style": {"width": f"{size}px", "height": f"{size}px"},
         "role": "button", "tabindex": "0", "aria-label": "Drop a player photo here",
         "data-photo-slot": player_id},
        h("span", {"cls": "photo-slot__caption"}, "Photo"),
    )


def bio_links(name, wiki_query=None):
    q = wiki_query or name
    return h(
        "div", {"style": {"display": "flex", "gap": "10px", "marginTop": "6px", "flexWrap": "wrap"}},
        h("a", {"href": "https://www.denversummitfc.com/roster", "target": "_blank",
                "rel": "noopener noreferrer", "style": {"fontSize": "13px"}}, "Club bio ↗"),
        h("a", {"href": f"https://en.wikipedia.org/w/index.php?search={_urlenc(q)}",
                "target": "_blank", "rel": "noopener noreferrer", "style": {"fontSize": "13px"}},
          "Wikipedia ↗"),
    )


def _urlenc(text):
    from urllib.parse import quote
    return quote(text)
