#!/usr/bin/env python3
"""Generates web/index.html from the Python view modules.

Run from anywhere: `python3 web/build_src/build.py`. Needs nothing beyond
the standard library — no Node, no wrangler, no Pyodide. That matters in
this sandbox specifically: wrangler dev cannot start here because workerd's
fetch of the Pyodide runtime is blocked by the egress proxy, so this script
is also how the frontend's Python gets exercised at all locally.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "views"))
WEB_ROOT = os.path.dirname(HERE)

from markup import h
import layout
import callasub
import data as D

import matchday
import pitch
import bench
import hearth
import hometeam
import visitors
import settings
import landing


def next_fixture(fixtures):
    now = "2026-09-20T15:00:00"
    upcoming = [f for f in fixtures if f["kickoff"] > now]
    upcoming.sort(key=lambda f: f["kickoff"])
    return upcoming[0] if upcoming else (fixtures[-1] if fixtures else None)


def open_seats(fixtures):
    now = "2026-09-20T15:00:00"
    out = []
    for f in fixtures:
        if f["kickoff"] < now:
            continue
        for s in f["seats"]:
            if s["status"] in ("bench", "listed"):
                out.append((f, s))
    return out


def build():
    fixtures_2026 = sorted((f for f in D.FIXTURES if f["season"] == 2026), key=lambda f: f["kickoff"])
    # Matches refreshBenchCount() in app.js, which counts every visible Bench
    # card (waiting *and* listed), so the pre-rendered badge doesn't jump the
    # moment app.js repaints it.
    bench_count = len(open_seats(fixtures_2026))
    notes_by_id = {n["id"]: n for n in D.BENCH_NOTES}
    ledger_2026 = D.LEDGER[2026]
    my_balance = ledger_2026["paid"].get(D.ME, 0) - ledger_2026["owed"].get(D.ME, 0)
    nxt = next_fixture(fixtures_2026)

    # One Call a Sub sheet set per fixture holding a seat of yours. Every
    # "Call a Sub" button (pitch.py, matchday.py) only ever targets your
    # first held seat in a fixture, so sheets are generated to match —
    # once per fixture, not once per held seat (a fixture with two seats
    # of yours would otherwise get a duplicate, id-colliding sheet set).
    fixtures_held_by_me = [f for f in D.FIXTURES if any(s["holder"] == D.ME for s in f["seats"])]
    sheets = []
    for f in fixtures_held_by_me:
        _, nodes = callasub.build(f)
        sheets.extend(nodes)
    sheets.append(hearth.settle_sheet())
    sheets.append(landing.new_syndicate_sheet())

    app_stage = h(
        "div", {"id": "stage-app", "hidden": True},
        layout.header(bench_count),
        h("main", None,
          matchday.render(nxt, D.BENCH_NOTES, my_balance),
          pitch.render(fixtures_2026),
          bench.render(fixtures_2026, notes_by_id),
          hearth.render(),
          hometeam.render(),
          visitors.render(),
          settings.render()),
    )

    body = h(
        "body", None,
        # A plain container, not <main> — app_stage already has its own
        # <main> for the active screen, and HTML forbids nested main landmarks.
        h("div", {"id": "app"},
          landing.landing(),
          landing.syndicate(),
          app_stage,
          sheets),
        h("script", {"type": "module", "src": "./src/app.js"}),
    )

    page = "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n" + str(layout.head()) + "\n</head>\n" + str(body) + "\n</html>\n"

    out_path = os.path.join(WEB_ROOT, "index.html")
    with open(out_path, "w") as fh:
        fh.write(page)
    return out_path, page


if __name__ == "__main__":
    path, page = build()
    print(f"wrote {path} ({len(page)} bytes)")
