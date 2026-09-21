"""Money and date formatting, matching the old ui.js helpers' output exactly
so the visual result doesn't shift under the rewrite."""
from __future__ import annotations

from datetime import datetime

_WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTH = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def money(cents):
    dollars = cents / 100
    whole = cents % 100 == 0
    if whole:
        return f"${dollars:,.0f}"
    return f"${dollars:,.2f}"


def _parse(iso):
    return datetime.fromisoformat(iso)


def match_date(iso):
    d = _parse(iso)
    return f"{_WEEKDAY[d.weekday()]}, {_MONTH[d.month - 1]} {d.day}"


def match_time(iso):
    d = _parse(iso)
    hour = d.hour % 12 or 12
    suffix = "AM" if d.hour < 12 else "PM"
    return f"{hour}:{d.minute:02d} {suffix}"


def short_date(iso):
    d = _parse(iso)
    return f"{d.month}/{d.day}"


def relative(iso):
    # Fixed "now" so the generated page is reproducible — matches the JS
    # store's own hard-coded "now" used for is_past()/next_fixture().
    now = _parse(NOW_ISO)
    mins = round((now - _parse(iso)).total_seconds() / 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    hrs = round(mins / 60)
    if hrs < 24:
        return f"{hrs}h ago"
    return f"{round(hrs / 24)}d ago"


def label12(hhmm):
    h24, m = (int(x) for x in hhmm.split(":"))
    suffix = "AM" if h24 < 12 else "PM"
    hr = h24 % 12 or 12
    return f"{hr}:{m:02d} {suffix}"


NOW_ISO = "2026-09-20T15:00:00"
