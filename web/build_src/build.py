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


def build():
    # Bench/Pitch/Matchday's real fixture and seat content doesn't exist at
    # build time -- it's a specific syndicate's real schedule, fetched and
    # rendered at runtime by web/src/app.js's paintRealFixtures(). The bench
    # badge in the header starts at 0 for the same reason and is repainted
    # alongside it, rather than trying to precompute a real count here.
    bench_count = 0

    sheets = callasub.build()
    sheets.append(hearth.settle_sheet())
    sheets.append(landing.new_syndicate_sheet())
    sheets.append(landing.join_syndicate_sheet())
    sheets.append(landing.leave_syndicate_sheet())

    app_stage = h(
        "div", {"id": "stage-app", "hidden": True},
        layout.header(bench_count),
        h("main", None,
          matchday.render(),
          pitch.render(),
          bench.render(),
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
