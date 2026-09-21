"""Tests for the roster/fixture/headshot sync job (src/sync.py).

External HTTP is stubbed at the js.fetch layer (see fake_workers.FakeFetch)
so these exercise the real parsing in sync_sources.py and the real diff/
write logic in sync.py against the in-memory D1 double -- nothing here talks
to the network.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from fake_workers import FakeFetchResponse, install_runtime_stubs, make_env  # noqa: E402

install_runtime_stubs()

import sync  # noqa: E402
from sync_sources import NWSL_ROSTER_URL, NWSL_SCHEDULE_URL, WIKIPEDIA_API  # noqa: E402
import js  # noqa: E402

SCHEMA = [
    os.path.join(ROOT, "migrations", "0001_initial.sql"),
    os.path.join(ROOT, "migrations", "0002_roster.sql"),
    os.path.join(ROOT, "migrations", "0003_national_team.sql"),
    os.path.join(ROOT, "migrations", "0004_sync_metadata.sql"),
]

SCHEDULE_HTML = """
<html><body>
<script type="application/ld+json">
{"@type": "SportsEvent", "startDate": "2026-10-04T19:00:00-06:00",
 "homeTeam": {"name": "Denver Summit FC"}, "awayTeam": {"name": "Seattle Reign FC"},
 "location": {"name": "Sunrise Stadium"}, "url": "https://www.nwslsoccer.com/match/1"}
</script>
</body></html>
"""

ROSTER_HTML = """
<html><body>
<script type="application/ld+json">
{"@type": "ItemList", "itemListElement": [
  {"item": {"@type": "Person", "name": "Ada Okafor", "jobTitle": "9", "roleName": "FWD",
            "url": "https://www.nwslsoccer.com/players/ada-okafor"}},
  {"item": {"@type": "Person", "name": "New Signing", "jobTitle": "14", "roleName": "MID",
            "url": "https://www.nwslsoccer.com/players/new-signing"}}
]}
</script>
</body></html>
"""


def _wiki_pageimages_url(name):
    return WIKIPEDIA_API + "?action=query&format=json&prop=pageimages&piprop=name&titles=" + name.replace(" ", "%20")


def _wiki_imageinfo_url(filename):
    return (
        WIKIPEDIA_API
        + "?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata&titles=File%3A"
        + filename
    )


class SyncTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = make_env(SCHEMA)
        js.fetch._responses = {}

    async def _seed_player(self, name="Ada Okafor", jersey=7, position="MID"):
        await sync_exec(
            self.env,
            "INSERT INTO roster_players (id, jersey_number, name, position) VALUES ('plr_1', ?, ?, ?)",
            jersey,
            name,
            position,
        )

    async def test_roster_sync_inserts_new_and_updates_drifted(self):
        await self._seed_player()
        js.fetch.install(
            {NWSL_ROSTER_URL: FakeFetchResponse(ROSTER_HTML)}
        )

        result = await sync._sync_roster(self.env)

        self.assertEqual(result["inserted"], 1)
        self.assertEqual(result["updated"], 1)
        rows = await sync_query(self.env, "SELECT jersey_number, position, source_ref FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["jersey_number"], 9)
        self.assertEqual(rows[0]["position"], "FWD")
        self.assertEqual(rows[0]["source_ref"], "https://www.nwslsoccer.com/players/ada-okafor")

    async def test_roster_sync_preserves_hand_curated_fields(self):
        await self._seed_player()
        await sync_exec(
            self.env,
            "UPDATE roster_players SET scouting_note = 'Left-footed set-piece taker' WHERE id = 'plr_1'",
        )
        js.fetch.install({NWSL_ROSTER_URL: FakeFetchResponse(ROSTER_HTML)})

        await sync._sync_roster(self.env)

        rows = await sync_query(self.env, "SELECT scouting_note FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["scouting_note"], "Left-footed set-piece taker")

    async def test_fixture_sync_updates_but_never_inserts(self):
        await sync_exec(
            self.env,
            """
            INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, weighted_value_cents)
            VALUES ('fix_1', NULL, 'Seattle Reign FC', '2026-10-04T18:00:00-06:00', 'Old Venue', 5000)
            """,
        )
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(SCHEDULE_HTML)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["updated"], 1)
        rows = await sync_query(self.env, "SELECT venue, kickoff_at FROM fixtures WHERE id = 'fix_1'")
        self.assertEqual(rows[0]["venue"], "Sunrise Stadium")
        self.assertEqual(rows[0]["kickoff_at"], "2026-10-04T19:00:00-06:00")

        remaining = await sync_query(self.env, "SELECT COUNT(*) AS n FROM fixtures")
        self.assertEqual(remaining[0]["n"], 1)  # no fixture was inserted

    async def test_headshot_sync_applies_allowed_license(self):
        await self._seed_player(name="Ada Okafor")
        js.fetch.install(
            {
                _wiki_pageimages_url("Ada Okafor"): FakeFetchResponse(
                    json.dumps({"query": {"pages": {"1": {"pageimage": "AdaOkafor.jpg"}}}})
                ),
                _wiki_imageinfo_url("AdaOkafor.jpg"): FakeFetchResponse(
                    json.dumps(
                        {
                            "query": {
                                "pages": {
                                    "2": {
                                        "imageinfo": [
                                            {
                                                "url": "https://upload.wikimedia.org/AdaOkafor.jpg",
                                                "extmetadata": {
                                                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                                    "Artist": {"value": "Jane Photographer"},
                                                },
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    )
                ),
            }
        )

        result = await sync._sync_headshots(self.env)

        self.assertEqual(result["updated"], 1)
        rows = await sync_query(self.env, "SELECT image_path, image_attribution FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["image_path"], "https://upload.wikimedia.org/AdaOkafor.jpg")
        self.assertIn("CC BY-SA", rows[0]["image_attribution"])

    async def test_headshot_sync_skips_disallowed_license(self):
        await self._seed_player(name="Ada Okafor")
        js.fetch.install(
            {
                _wiki_pageimages_url("Ada Okafor"): FakeFetchResponse(
                    json.dumps({"query": {"pages": {"1": {"pageimage": "AdaOkafor.jpg"}}}})
                ),
                _wiki_imageinfo_url("AdaOkafor.jpg"): FakeFetchResponse(
                    json.dumps(
                        {
                            "query": {
                                "pages": {
                                    "2": {
                                        "imageinfo": [
                                            {
                                                "url": "https://upload.wikimedia.org/AdaOkafor.jpg",
                                                "extmetadata": {
                                                    "LicenseShortName": {"value": "Fair use"},
                                                },
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    )
                ),
            }
        )

        result = await sync._sync_headshots(self.env)

        self.assertEqual(result["updated"], 0)
        rows = await sync_query(self.env, "SELECT image_path FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["image_path"], "/assets/images/players/placeholder-avatar.webp")

    async def test_run_sync_survives_one_source_failing(self):
        # No fetch responses installed at all -- roster/fixtures/opponents
        # each call fetch and get FetchNotStubbed, wrapped as
        # SyncSourceError; headshots has no roster rows to look up in this
        # empty env, so it succeeds trivially rather than failing.
        summary = await sync.run_sync(self.env)
        for job_name in ("roster", "fixtures", "opponents"):
            self.assertIn("error", summary[job_name])
        self.assertNotIn("error", summary["headshots"])


async def sync_exec(env, sql, *params):
    from db import execute

    return await execute(env, sql, *params)


async def sync_query(env, sql, *params):
    from db import query

    return await query(env, sql, *params)


if __name__ == "__main__":
    unittest.main()
