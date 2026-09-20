"""A tiny, safe HTML builder — the Python analogue of the old ui.js `h()`.

Named markup.py rather than html.py so it cannot shadow the standard
library's html package (same reasoning as the backend's responses.py).
Kept dependency-free (no Jinja2, no markupsafe) so it needs nothing beyond
the standard library to run.
"""
from __future__ import annotations

from html import escape as _escape

VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "area", "source"}

# Attribute keys that take a dict of camelCase/kebab style sub-values are not
# needed here — everything is built as plain style strings, same as the JS
# version's `style: {...}` usage translated to a dict of CSS properties.


class El:
    """A node in the tree. `str(el)` renders it; children may be strings,
    other El nodes, None (dropped), or lists (flattened)."""

    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag, attrs=None, children=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = children or []

    def __str__(self):
        return render(self)


def h(tag, attrs=None, *children):
    return El(tag, attrs, list(children))


def render(node):
    if node is None or node is False:
        return ""
    if isinstance(node, (list, tuple)):
        return "".join(render(c) for c in node)
    if isinstance(node, El):
        return _render_el(node)
    # Raw markup wrapper lets a view splice pre-built HTML in verbatim.
    if isinstance(node, Raw):
        return node.markup
    # Text content only needs &<> escaped; quotes matter in attribute
    # values, not here, so an apostrophe stays a literal apostrophe.
    return _escape(str(node), quote=False)


def _render_el(el):
    attr_str = _render_attrs(el.attrs)
    open_tag = f"<{el.tag}{attr_str}>"
    if el.tag in VOID_TAGS:
        return open_tag
    inner = "".join(render(c) for c in el.children)
    return f"{open_tag}{inner}</{el.tag}>"


def _render_attrs(attrs):
    parts = []
    for key, value in attrs.items():
        if value is None or value is False:
            continue
        if key == "style" and isinstance(value, dict):
            value = style(value)
        if key == "cls":
            key = "class"
        key = key.replace("_", "-")
        if value is True:
            parts.append(f" {key}")
        else:
            parts.append(f' {key}="{_escape(str(value), quote=True)}"')
    return "".join(parts)


def style(props):
    """dict[str, str] -> a `key: value; key: value` CSS string, kebab-casing
    camelCase keys the way the old JS `Object.assign(el.style, ...)` did."""
    out = []
    for k, v in props.items():
        if v is None:
            continue
        kebab = "".join(f"-{c.lower()}" if c.isupper() else c for c in k)
        out.append(f"{kebab}: {v}")
    return "; ".join(out)


class Raw:
    """Wrap markup that is already-escaped HTML, to splice verbatim."""

    __slots__ = ("markup",)

    def __init__(self, markup):
        self.markup = markup

    def __str__(self):
        return self.markup


def esc(text):
    return _escape(str(text), quote=True)
