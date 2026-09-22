"""Unit tests for the Python view/build layer, run with:

    python3 -m unittest discover -s web/tests -v

No wrangler, no browser — these call the render functions directly with
plain CPython, the same bar the backend's own tests hold to (see
tests/fake_workers.py at the repo root) since wrangler dev cannot start in
a sandbox that blocks the Pyodide runtime fetch.
"""
from __future__ import annotations

import html.parser
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_ROOT = os.path.dirname(HERE)
BUILD_SRC = os.path.join(WEB_ROOT, "build_src")
sys.path.insert(0, BUILD_SRC)
sys.path.insert(0, os.path.join(BUILD_SRC, "views"))

import build as build_mod  # noqa: E402
import data as D  # noqa: E402
import matchday, pitch, bench, hearth, hometeam, visitors, settings, landing  # noqa: E402


LEAK_RE = re.compile(r">None<|>null<|>undefined<|>NaN<")


VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class StrictParser(html.parser.HTMLParser):
    """HTMLParser's own error() hook is dead code — its "strict" mode was
    removed in Python 3.5, and error() has never been called since, so
    subclassing it alone (as this used to) validates nothing regardless of
    how malformed the markup is. This adds the check the test actually
    wants: every non-void tag opened must be closed, in order, with nothing
    left open when the document ends."""

    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_ELEMENTS:
            return
        if not self.stack or self.stack[-1] != tag:
            raise AssertionError(f"mismatched closing tag </{tag}>; open tags were {self.stack}")
        self.stack.pop()

    def close(self):
        super().close()
        if self.stack:
            raise AssertionError(f"unclosed tags at end of document: {self.stack}")


class ViewsRenderCleanly(unittest.TestCase):
    """Each view, called with the same data the build script uses, must be
    free of leaked Python placeholder text — the exact bug class the old JS
    version hit once (a literal 'null' rendered under every player card)."""

    def setUp(self):
        self.fixtures = [f for f in D.FIXTURES if f["season"] == 2026]
        self.notes_by_id = {n["id"]: n for n in D.BENCH_NOTES}
        nxt = build_mod.next_fixture(self.fixtures)
        self.pieces = {
            "matchday": matchday.render(nxt, D.BENCH_NOTES, 4500),
            "pitch": pitch.render(self.fixtures),
            "bench": bench.render(self.fixtures, self.notes_by_id),
            "hearth": hearth.render(),
            "hometeam": hometeam.render(),
            "visitors": visitors.render(),
            "settings": settings.render(),
            "landing": landing.landing(),
            "syndicate": landing.syndicate(),
        }

    def test_no_placeholder_leaks(self):
        for name, node in self.pieces.items():
            with self.subTest(view=name):
                self.assertNotRegex(str(node), LEAK_RE)

    def test_every_view_has_expected_heading(self):
        expectations = {
            "matchday": "Summit vs",
            "pitch": "The Pitch",
            "bench": "The Bench",
            "hearth": "The Hearth",
            "hometeam": "The Locker Room",
            "visitors": "The Visiting Club",
            "settings": "Campfire Settings",
            "landing": "Two seats",
            "syndicate": "Find your syndicate",
        }
        for name, needle in expectations.items():
            with self.subTest(view=name):
                self.assertIn(needle, str(self.pieces[name]))

    def test_visitor_room_tilts_stay_under_design_limit(self):
        """The design brief: tilts stay under 0.6deg, so the dishevelment
        reads as cosmetic rather than actually crooked."""
        s = str(self.pieces["visitors"])
        tilts = [abs(float(t)) for t in re.findall(r"rotate\(([-\d.]+)deg\)", s)]
        self.assertTrue(tilts, "expected at least one tilted element")
        self.assertTrue(all(t <= 0.6 for t in tilts), tilts)

    def test_visitors_shows_an_honest_note_when_a_club_has_no_players_listed(self):
        # OPPONENTS carries no invented players (or "danger" tags -- that
        # was scouting-style commentary nowhere public to verify, same as
        # form/shape/quick_stats); every dossier's players list is empty
        # until real ones sync in from D1, so the empty state should say so
        # rather than the section just vanishing.
        s = str(self.pieces["visitors"])
        self.assertNotIn("DANGER", s)
        self.assertIn("Full team sheet not published here yet", s)


class FullPageIntegrity(unittest.TestCase):
    """The assembled page: valid markup, every referenced sheet exists,
    every tab section exists exactly once."""

    @classmethod
    def setUpClass(cls):
        _, cls.page = build_mod.build()

    def test_page_parses_as_html(self):
        parser = StrictParser()
        parser.feed(self.page)
        parser.close()  # raises on any tag left unclosed or mismatched

    def test_head_renders_markup_not_a_python_repr(self):
        # Regression: layout.head() returns a bare Raw(...); build.py joins
        # it with str(), and Raw had no __str__, so this silently degraded
        # to "<markup.Raw object at 0x...>" spliced into <head> as a literal
        # tag. That corrupted the whole DOM (the browser nested <body> under
        # it), which only ever showed up as scattered, hard-to-place
        # visibility timeouts in the browser suite, never in a unit test.
        self.assertNotIn("object at 0x", self.page)
        self.assertIn('<meta charset="utf-8">', self.page)
        self.assertIn("<title>Summit Hearth &amp; Bench</title>", self.page)

    def test_no_placeholder_leaks_anywhere(self):
        self.assertNotRegex(self.page, LEAK_RE)

    def test_three_stages_present_once_each(self):
        for stage_id in ("stage-landing", "stage-syndicate", "stage-app"):
            self.assertEqual(self.page.count(f'id="{stage_id}"'), 1, stage_id)

    def test_every_tab_section_present_once(self):
        for tab in ("matchday", "pitch", "bench", "hearth", "hometeam", "visitors", "settings"):
            self.assertEqual(self.page.count(f'data-tab="{tab}"'), 1, tab)

    def test_every_open_sheet_target_exists(self):
        wanted = set(re.findall(r'data-open-sheet="([^"]+)"', self.page))
        self.assertTrue(wanted, "expected at least one data-open-sheet reference")
        for sheet_id in wanted:
            with self.subTest(sheet=sheet_id):
                self.assertIn(f'id="{sheet_id}"', self.page)

    def test_every_expand_target_exists(self):
        wanted = set(re.findall(r'data-target="([^"]+)"', self.page))
        self.assertTrue(wanted)
        for target_id in wanted:
            with self.subTest(target=target_id):
                self.assertIn(f'id="{target_id}"', self.page)

    def test_seat_pairs_have_exactly_one_visible_variant(self):
        """Every [data-seat] toggle group should show exactly one non-hidden
        state — never zero (invisible seat) or more than one. A seat's key
        intentionally repeats across independent widgets (Matchday's hero,
        the Pitch avatar strip, the Pitch action row, ...) so that src/app.js
        can flip all of them at once, and a group's own state set can vary
        in size (a plain held/released pair vs. the hero's three-way
        released/gifted/listed reason) — so this infers each group's size
        from its own distinct states and checks every consecutive group of
        that size, rather than assuming pairs or summing hidden globally."""
        seat_keys = set(re.findall(r'data-seat="([^"]+)"', self.page))
        for key in seat_keys:
            with self.subTest(seat=key):
                entries = re.findall(
                    rf'<span data-seat="{re.escape(key)}" data-state="([a-z]+)"( hidden)?>', self.page,
                )
                if not entries:
                    continue
                distinct_states = sorted({state for state, _ in entries})
                group_size = len(distinct_states)
                self.assertEqual(len(entries) % group_size, 0, (key, entries))
                for i in range(0, len(entries), group_size):
                    group = entries[i:i + group_size]
                    self.assertEqual(sorted(state for state, _ in group), distinct_states, (key, i, entries))
                    hidden_count = sum(1 for _, hidden in group if hidden)
                    self.assertEqual(hidden_count, group_size - 1, (key, i, entries))


if __name__ == "__main__":
    unittest.main()
