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
from sync_sources import NWSL_ROSTER_URL, NWSL_SCHEDULE_URL, SyncSourceError, WIKIPEDIA_API  # noqa: E402
import js  # noqa: E402

SCHEMA = [
    os.path.join(ROOT, "migrations", "0001_initial.sql"),
    os.path.join(ROOT, "migrations", "0002_roster.sql"),
    os.path.join(ROOT, "migrations", "0003_national_team.sql"),
    os.path.join(ROOT, "migrations", "0004_sync_metadata.sql"),
    os.path.join(ROOT, "migrations", "0005_roster_jersey_nullable.sql"),
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

def _roster_row(player_id, first, last, slug, jersey, position_label):
    """One <tr> of the real roster table (nwslsoccer.com renders no JSON-LD
    on this page -- see sync_sources.fetch_nwsl_roster), trimmed to the bits
    the parser reads: the data-player-id marker, the name spans, the profile
    link, and the jersey/position cells."""
    jersey_text = "" if jersey is None else str(jersey)
    return """
    <tr class="StyledTr--1ibdud4 gpEqPQ d3w-table__row d3w-tr">
      <td class="StyledTd--qyr8y8 gJBcUR d3w-table__cell d3w-td headShots -sticky-column" role="cell">
        <div class="d3w-player-image-wrap" data-player-id="nwsl::Football_Player::{player_id}">
          <picture><img alt="{first} {last}"></picture>
        </div>
      </td>
      <td class="StyledTd--qyr8y8 gJBcUR d3w-table__cell d3w-td player -sticky-column" role="cell">
        <div class="d3w-player-info-wrapper">
          <a class="StyledPlayerNameLink d3w-player-name d3w-entity-link"
             href="https://www.nwslsoccer.com/players/{player_id}/{slug}">
            <span class="d3w-player-name--first">{first}</span><span class="d3w-player-name--last">{last}</span>
          </a>
        </div>
      </td>
      <td class="StyledTd--qyr8y8 gJBcUR d3w-table__cell d3w-td   jersey " role="cell">{jersey}</td>
      <td class="StyledTd--qyr8y8 gJBcUR d3w-table__cell d3w-td   position " role="cell">{position}</td>
    </tr>
    """.format(
        player_id=player_id, first=first, last=last, slug=slug,
        jersey=jersey_text, position=position_label,
    )


ROSTER_HTML = (
    "<html><body><table><tbody>"
    + _roster_row("aaaa1111aaaa1111aaaa1111aaaa1111", "Ada", "Okafor", "ada-okafor", 9, "Forward")
    + _roster_row("bbbb2222bbbb2222bbbb2222bbbb2222", "New", "Signing", "new-signing", 14, "Midfielder")
    + "</tbody></table></body></html>"
)


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
        self.assertEqual(
            rows[0]["source_ref"],
            "https://www.nwslsoccer.com/players/aaaa1111aaaa1111aaaa1111aaaa1111/ada-okafor",
        )

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

    async def test_roster_sync_deactivates_players_not_on_remote_roster(self):
        await self._seed_player(name="Departed Player", jersey=99, position="DEF")
        js.fetch.install({NWSL_ROSTER_URL: FakeFetchResponse(ROSTER_HTML)})

        result = await sync._sync_roster(self.env)

        self.assertEqual(result["deactivated"], 1)
        rows = await sync_query(self.env, "SELECT active FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["active"], 0)

    async def test_roster_sync_reactivates_a_returning_player(self):
        await self._seed_player(name="Ada Okafor")
        await sync_exec(self.env, "UPDATE roster_players SET active = FALSE WHERE id = 'plr_1'")
        js.fetch.install({NWSL_ROSTER_URL: FakeFetchResponse(ROSTER_HTML)})

        await sync._sync_roster(self.env)

        rows = await sync_query(self.env, "SELECT active FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["active"], 1)

    async def test_roster_sync_skips_insert_with_no_position_and_preserves_existing(self):
        await self._seed_player(name="Ada Okafor", position="MID")
        html = (
            "<html><body><table><tbody>"
            + _roster_row("aaaa1111aaaa1111aaaa1111aaaa1111", "Ada", "Okafor", "ada-okafor", 9, "")
            + _roster_row("cccc3333cccc3333cccc3333cccc3333", "No", "Position Yet", "no-position", 21, "")
            + "</tbody></table></body></html>"
        )
        js.fetch.install({NWSL_ROSTER_URL: FakeFetchResponse(html)})

        result = await sync._sync_roster(self.env)

        self.assertEqual(result["skipped"], 1)  # "No Position Yet" never inserted
        rows = await sync_query(self.env, "SELECT position FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["position"], "MID")  # blank remote position didn't overwrite it

    async def test_fetch_nwsl_roster_rejects_a_partial_parse(self):
        # A row whose data-player-id marker is found but whose name spans
        # aren't (a markup change breaking just the name, not the marker)
        # must fail the whole fetch, not silently return a shorter roster --
        # _sync_roster would otherwise deactivate every real player missing
        # from that shorter list.
        import sync_sources

        html = (
            "<html><body><table><tbody>"
            + _roster_row("aaaa1111aaaa1111aaaa1111aaaa1111", "Ada", "Okafor", "ada-okafor", 9, "Forward")
            + '<tr><td><div data-player-id="nwsl::Football_Player::dddd4444dddd4444dddd4444dddd4444">'
            + "</div></td></tr>"
            + "</tbody></table></body></html>"
        )
        js.fetch.install({NWSL_ROSTER_URL: FakeFetchResponse(html)})

        with self.assertRaises(SyncSourceError):
            await sync_sources.fetch_nwsl_roster(self.env)

    async def test_roster_sync_picks_up_a_name_change(self):
        await self._seed_player(name="Ada Okafor")
        await sync_exec(self.env, "UPDATE roster_players SET source_ref = 'https://www.nwslsoccer.com/players/ada-okafor' WHERE id = 'plr_1'")
        js.fetch.install({NWSL_ROSTER_URL: FakeFetchResponse(ROSTER_HTML)})

        await sync._sync_roster(self.env)

        rows = await sync_query(self.env, "SELECT name FROM roster_players WHERE id = 'plr_1'")
        self.assertEqual(rows[0]["name"], "Ada Okafor")  # unchanged here, but the column is now part of drift detection

    async def test_fixture_sync_updates_every_group_sharing_a_match(self):
        await sync_exec(
            self.env,
            """
            INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, weighted_value_cents)
            VALUES ('fix_a', 'grp_a', 'Seattle Reign FC', '2026-10-04T18:00:00-06:00', 'Old Venue', 5000),
                   ('fix_b', 'grp_b', 'Seattle Reign FC', '2026-10-04T18:00:00-06:00', 'Old Venue', 6000)
            """,
        )
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(SCHEDULE_HTML)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["matched"], 2)
        rows = await sync_query(self.env, "SELECT id, venue FROM fixtures ORDER BY id")
        self.assertEqual([r["venue"] for r in rows], ["Sunrise Stadium", "Sunrise Stadium"])

    async def test_fixture_sync_matches_a_rescheduled_kickoff_via_window(self):
        # Existing row's kickoff (the stale, pre-reschedule date) is 10 days
        # off the remote's new date -- inside the rematch window, so this
        # must still resolve to the same fixture rather than being skipped.
        await sync_exec(
            self.env,
            """
            INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, weighted_value_cents)
            VALUES ('fix_1', NULL, 'Seattle Reign FC', '2026-09-24T18:00:00-06:00', 'Old Venue', 5000)
            """,
        )
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(SCHEDULE_HTML)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["matched"], 1)
        rows = await sync_query(self.env, "SELECT kickoff_at FROM fixtures WHERE id = 'fix_1'")
        self.assertEqual(rows[0]["kickoff_at"], "2026-10-04T19:00:00-06:00")

    async def test_fixture_sync_preserves_venue_when_remote_omits_it(self):
        await sync_exec(
            self.env,
            """
            INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, weighted_value_cents)
            VALUES ('fix_1', NULL, 'Seattle Reign FC', '2026-10-04T18:00:00-06:00', 'Admin-entered Venue', 5000)
            """,
        )
        html = """
        <html><body><script type="application/ld+json">
        {"@type": "SportsEvent", "startDate": "2026-10-04T19:00:00-06:00",
         "homeTeam": {"name": "Denver Summit FC"}, "awayTeam": {"name": "Seattle Reign FC"},
         "location": {"name": ""}, "url": "https://www.nwslsoccer.com/match/1"}
        </script></body></html>
        """
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        await sync._sync_fixtures(self.env)

        rows = await sync_query(self.env, "SELECT venue FROM fixtures WHERE id = 'fix_1'")
        self.assertEqual(rows[0]["venue"], "Admin-entered Venue")

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
