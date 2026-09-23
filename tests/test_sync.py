"""Tests for the roster/fixture/headshot sync job (src/sync.py).

External HTTP is stubbed at the js.fetch layer (see fake_workers.FakeFetch)
so these exercise the real parsing in sync_sources.py and the real diff/
write logic in sync.py against the in-memory D1 double -- nothing here talks
to the network.
"""

import datetime
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
from sync_sources import (  # noqa: E402
    DENVER_SUMMIT_TEAM_ID,
    NWSL_ROSTER_URL,
    NWSL_SCHEDULE_URL,
    SyncSourceError,
    WIKIPEDIA_API,
    fetch_nwsl_roster,
    fetch_nwsl_schedule,
)
import js  # noqa: E402

SCHEMA = [
    os.path.join(ROOT, "migrations", "0001_initial.sql"),
    os.path.join(ROOT, "migrations", "0002_roster.sql"),
    os.path.join(ROOT, "migrations", "0003_national_team.sql"),
    os.path.join(ROOT, "migrations", "0004_sync_metadata.sql"),
    os.path.join(ROOT, "migrations", "0005_roster_jersey_nullable.sql"),
    os.path.join(ROOT, "migrations", "0006_opponent_sync.sql"),
    os.path.join(ROOT, "migrations", "0007_fixture_source_ref_unique.sql"),
    os.path.join(ROOT, "migrations", "0008_group_invite_codes.sql"),
    os.path.join(ROOT, "migrations", "0009_user_contact_info.sql"),
    os.path.join(ROOT, "migrations", "0010_guest_password_auth.sql"),
    os.path.join(ROOT, "migrations", "0011_syndicate_seat_labels.sql"),
    os.path.join(ROOT, "migrations", "0012_bench_notes.sql"),
]

def _season_header(year=2026):
    return '<h4 class="d3w-buttons-head-title">Regular Season {}</h4>'.format(year)


def _schedule_row(
    matchid, date_text, opponent_name, opponent_id, venue, slug,
    is_home=True, time_text=None, status="UPCOMING",
):
    """One match-item of the real schedule's match-list widget (also no
    JSON-LD -- see sync_sources.fetch_nwsl_schedule), trimmed to the bits
    the parser reads: the date header, the match id/url, the two team
    blocks (matched by data-team-id, one of them always Denver Summit's own
    real id), the optional kickoff time, and the venue."""
    if is_home:
        home_id, home_name = DENVER_SUMMIT_TEAM_ID, "Denver Summit"
        away_id, away_name = opponent_id, opponent_name
    else:
        home_id, home_name = opponent_id, opponent_name
        away_id, away_name = DENVER_SUMMIT_TEAM_ID, "Denver Summit"
    time_html = (
        '<span class="d3w-status-wrapper status-date">{}</span>'.format(time_text)
        if time_text else ""
    )
    return """
    <div class="StyledMatchList--1nggtrl fhXkdX d3w-match-list-date-group">
      <div class="StyledDateHeader--2vvlk1 kaLxsd d3w-match-list-date-header">
        <span class="StyledDate--pbzu0p eWlUqB d3w-match-list-date">{date_text}</span>
      </div>
      <div data-matchid="nwsl::Football_Match::{matchid}" data-match-status="{status}"
           class="StyledListItem--126skdp igWQeF d3w-match-list-item">
        <div class="StyledListItemInfoWrap--1h0jwfl ebewJl d3w-match-list-item-info-wrap">
          <a class="d3w-entity-link" href="https://www.nwslsoccer.com/match/{matchid}/{slug}">
            {time_html}
            <div class="StyledListItemVenue--10ubxwj kJWyCr d3w-match-list-item-venue">
              <div class="StyledVenueItem--405a8q gVekZh d3w-item-venue"><span>{venue}</span> <span>Somewhere</span></div>
            </div>
          </a>
        </div>
        <div class="StyledListItemFixtureWrap--1b7aniv iMVjYj d3w-match-list-item-fixture-wrap">
          <div class="StyledListItemFixture--xofr1m eoaKhm d3w-match-list-item-fixture">
            <div data-team-id="nwsl::Football_Team::{home_id}" class="StyledTeam--100iqrf blEifR d3w-match-team team-h score-upcoming ">
              <div class="StyledTeamName--188jpx5 hRkspW d3w-team-name-wrap  d3w-draw "><span>{home_name}</span></div>
            </div>
            <div class="StyledTime--17pmvh8 gRQzyh d3w-match-score d3w-match-time">vs</div>
            <div data-team-id="nwsl::Football_Team::{away_id}" class="StyledTeam--100iqrf blEifR d3w-match-team team-a score-upcoming ">
              <div class="StyledTeamName--188jpx5 hRkspW d3w-team-name-wrap  d3w-draw "><span>{away_name}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
    """.format(
        matchid=matchid, date_text=date_text, status=status, slug=slug,
        time_html=time_html, venue=venue,
        home_id=home_id, home_name=home_name, away_id=away_id, away_name=away_name,
    )


SCHEDULE_HTML = "<html><body>" + _season_header() + _schedule_row(
    "1111aaaa1111aaaa1111aaaa1111aaaa", "Sunday, Oct 4", "Seattle Reign FC",
    "bbbb2222bbbb2222bbbb2222bbbb2222", "Sunrise Stadium", "denver-summit-vs-seattle-reign",
    is_home=True, time_text="7:00 PM",
) + "</body></html>"

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
        self.assertEqual(rows[0]["kickoff_at"], "2026-10-04T19:00:00")

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
        html = (
            "<html><body><table><tbody>"
            + _roster_row("aaaa1111aaaa1111aaaa1111aaaa1111", "Ada", "Okafor", "ada-okafor", 9, "Forward")
            + '<tr><td><div data-player-id="nwsl::Football_Player::dddd4444dddd4444dddd4444dddd4444">'
            + "</div></td></tr>"
            + "</tbody></table></body></html>"
        )
        js.fetch.install({NWSL_ROSTER_URL: FakeFetchResponse(html)})

        with self.assertRaises(SyncSourceError):
            await fetch_nwsl_roster(self.env)

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
        self.assertEqual(rows[0]["kickoff_at"], "2026-10-04T19:00:00")

    async def test_fixture_sync_preserves_venue_when_remote_omits_it(self):
        await sync_exec(
            self.env,
            """
            INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, weighted_value_cents)
            VALUES ('fix_1', NULL, 'Seattle Reign FC', '2026-10-04T18:00:00-06:00', 'Admin-entered Venue', 5000)
            """,
        )
        html = "<html><body>" + _season_header() + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", "Sunday, Oct 4", "Seattle Reign FC",
            "bbbb2222bbbb2222bbbb2222bbbb2222", "", "denver-summit-vs-seattle-reign",
            is_home=True, time_text="7:00 PM",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        await sync._sync_fixtures(self.env)

        rows = await sync_query(self.env, "SELECT venue FROM fixtures WHERE id = 'fix_1'")
        self.assertEqual(rows[0]["venue"], "Admin-entered Venue")

    async def _seed_group(self, group_id="grp_1", total_seats=2, season_year=2026):
        await sync_exec(
            self.env,
            "INSERT INTO groups (id, name, season_year, total_seats, package_cost_cents) VALUES (?, 'Test Syndicate', ?, ?, 100000)",
            group_id,
            season_year,
            total_seats,
        )

    async def test_fixture_sync_creates_a_fixture_for_an_upcoming_home_match(self):
        future = datetime.date.today() + datetime.timedelta(days=30)
        await self._seed_group(total_seats=2, season_year=future.year)
        html = "<html><body>" + _season_header(future.year) + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", future.strftime("%A, %b ") + str(future.day),
            "Angel City", "bbbb2222bbbb2222bbbb2222bbbb2222", "Centennial Stadium",
            "denver-summit-vs-angel-city", is_home=True, time_text="7:00 PM",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["created"], 1)
        fixtures = await sync_query(self.env, "SELECT id, opponent, venue FROM fixtures")
        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["opponent"], "Angel City")
        self.assertEqual(fixtures[0]["venue"], "Centennial Stadium")

        seats = await sync_query(
            self.env,
            "SELECT seat_number, status, assigned_user_id FROM seat_allocations WHERE fixture_id = ? ORDER BY seat_number",
            fixtures[0]["id"],
        )
        self.assertEqual(len(seats), 2)
        for seat in seats:
            self.assertEqual(seat["status"], "on_bench")
            self.assertIsNone(seat["assigned_user_id"])

    async def test_fixture_sync_does_not_create_for_an_away_match(self):
        future = datetime.date.today() + datetime.timedelta(days=30)
        await self._seed_group(season_year=future.year)
        html = "<html><body>" + _season_header(future.year) + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", future.strftime("%A, %b ") + str(future.day),
            "Chicago Stars", "bbbb2222bbbb2222bbbb2222bbbb2222", "Some Away Venue",
            "chicago-stars-vs-denver-summit", is_home=False, time_text="7:00 PM",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["created"], 0)
        fixtures = await sync_query(self.env, "SELECT COUNT(*) AS n FROM fixtures")
        self.assertEqual(fixtures[0]["n"], 0)

    async def test_fixture_sync_does_not_create_for_a_match_already_played(self):
        past = datetime.date.today() - datetime.timedelta(days=30)
        await self._seed_group(season_year=past.year)
        html = "<html><body>" + _season_header(past.year) + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", past.strftime("%A, %b ") + str(past.day),
            "Angel City", "bbbb2222bbbb2222bbbb2222bbbb2222", "Centennial Stadium",
            "denver-summit-vs-angel-city", is_home=True, status="FINISHED",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["created"], 0)
        fixtures = await sync_query(self.env, "SELECT COUNT(*) AS n FROM fixtures")
        self.assertEqual(fixtures[0]["n"], 0)

    async def test_fixture_sync_still_creates_within_the_kickoff_timezone_slop(self):
        # kickoff_at is a naive local time compared against the Worker's
        # naive UTC clock -- a match earlier today can look "already
        # kicked off" several hours before it truly has (see
        # sync._KICKOFF_TIMEZONE_SLOP). The deliberate trade-off is to
        # still create rather than risk wrongly skipping a genuinely
        # upcoming match: 12:01 AM today is within the slop, so this must
        # still create.
        today = datetime.date.today()
        await self._seed_group(season_year=today.year)
        html = "<html><body>" + _season_header(today.year) + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", today.strftime("%A, %b ") + str(today.day),
            "Angel City", "bbbb2222bbbb2222bbbb2222bbbb2222", "Centennial Stadium",
            "denver-summit-vs-angel-city", is_home=True, time_text="12:01 AM",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["created"], 1)

    async def test_fixture_sync_does_not_create_for_a_group_in_a_different_season(self):
        future = datetime.date.today() + datetime.timedelta(days=30)
        # Group's season is one year off the remote match's -- a 2026
        # schedule must never populate a 2025 or 2027 syndicate's fixtures.
        await self._seed_group(season_year=future.year + 1)
        html = "<html><body>" + _season_header(future.year) + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", future.strftime("%A, %b ") + str(future.day),
            "Angel City", "bbbb2222bbbb2222bbbb2222bbbb2222", "Centennial Stadium",
            "denver-summit-vs-angel-city", is_home=True, time_text="7:00 PM",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        result = await sync._sync_fixtures(self.env)

        self.assertEqual(result["created"], 0)
        fixtures = await sync_query(self.env, "SELECT COUNT(*) AS n FROM fixtures")
        self.assertEqual(fixtures[0]["n"], 0)

    async def test_fixture_sync_is_idempotent_against_a_racing_duplicate_create(self):
        # Simulates two overlapping sync runs both finding the same group
        # missing the same match: calling the creation step twice for the
        # same (group, remote) must not produce two fixtures or two sets of
        # seats -- migrations/0007_fixture_source_ref_unique.sql is what
        # makes the second call a no-op instead of a duplicate insert.
        future = datetime.date.today() + datetime.timedelta(days=30)
        await self._seed_group(total_seats=2, season_year=future.year)
        group = (await sync_query(self.env, "SELECT id, total_seats FROM groups"))[0]
        remote = {
            "source_ref": "https://www.nwslsoccer.com/match/aaaa/denver-summit-vs-angel-city",
            "opponent": "Angel City",
            "kickoff_at": "{}-01-01T19:00:00".format(future.year),
            "venue": "Centennial Stadium",
        }

        first = await sync._create_fixture_from_sync(self.env, group, remote)
        second = await sync._create_fixture_from_sync(self.env, group, remote)

        self.assertTrue(first)
        self.assertFalse(second)
        fixtures = await sync_query(self.env, "SELECT COUNT(*) AS n FROM fixtures")
        self.assertEqual(fixtures[0]["n"], 1)
        seats = await sync_query(self.env, "SELECT COUNT(*) AS n FROM seat_allocations")
        self.assertEqual(seats[0]["n"], 2)

    async def test_fixture_sync_preserves_a_known_kickoff_time_when_remote_time_is_unknown(self):
        # A match that has since finished carries no kickoff time widget
        # (see fetch_nwsl_schedule); its synthesized midnight must not
        # overwrite the real kickoff time a previous sync already recorded.
        await sync_exec(
            self.env,
            "INSERT INTO fixtures (id, group_id, opponent, kickoff_at, venue, weighted_value_cents, source_ref) VALUES "
            "('fix_1', NULL, 'Seattle Reign FC', '2026-10-04T19:00:00', 'Sunrise Stadium', 5000, "
            "'https://www.nwslsoccer.com/match/1/denver-summit-vs-seattle-reign')",
        )
        html = "<html><body>" + _season_header() + _schedule_row(
            "1", "Sunday, Oct 4", "Seattle Reign FC",
            "bbbb2222bbbb2222bbbb2222bbbb2222", "Sunrise Stadium", "denver-summit-vs-seattle-reign",
            is_home=True, status="FINISHED",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        await sync._sync_fixtures(self.env)

        rows = await sync_query(self.env, "SELECT kickoff_at FROM fixtures WHERE id = 'fix_1'")
        self.assertEqual(rows[0]["kickoff_at"], "2026-10-04T19:00:00")

    async def test_fetch_nwsl_schedule_rejects_a_row_missing_denver_team_id(self):
        # Both sides present, but neither is Denver Summit's own team id --
        # without an explicit check, by_team_id.get(DENVER_ID) == "team-h"
        # would silently resolve to False and fabricate an away fixture
        # against whichever team happened to be found, instead of failing.
        html = "<html><body>" + _season_header() + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", "Sunday, Oct 4", "Seattle Reign FC",
            "bbbb2222bbbb2222bbbb2222bbbb2222", "Sunrise Stadium", "chicago-stars-vs-seattle-reign",
            is_home=True, time_text="7:00 PM",
        ).replace(DENVER_SUMMIT_TEAM_ID, "cccc3333cccc3333cccc3333cccc3333") + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        with self.assertRaises(SyncSourceError):
            await fetch_nwsl_schedule(self.env)

    async def test_fetch_nwsl_schedule_rejects_an_unparseable_kickoff(self):
        # A date/time format change (or plain garbage) must not escape as a
        # bare ValueError, which _safe() does not catch -- that would crash
        # run_sync entirely instead of skipping just this one job.
        html = "<html><body>" + _season_header() + _schedule_row(
            "1111aaaa1111aaaa1111aaaa1111aaaa", "Sunday, Not-A-Month 99", "Seattle Reign FC",
            "bbbb2222bbbb2222bbbb2222bbbb2222", "Sunrise Stadium", "denver-summit-vs-seattle-reign",
            is_home=True, time_text="7:00 PM",
        ) + "</body></html>"
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        with self.assertRaises(SyncSourceError):
            await fetch_nwsl_schedule(self.env)

    async def test_fetch_nwsl_schedule_rejects_a_partial_parse(self):
        # A row whose data-matchid marker is found but whose team blocks
        # aren't (a markup change breaking just the team names, not the
        # marker) must fail the whole fetch, not silently return a shorter
        # schedule -- sync.py's creation logic would otherwise miss real
        # upcoming home matches without any sign anything had gone wrong.
        html = (
            "<html><body>"
            + _season_header()
            + _schedule_row(
                "1111aaaa1111aaaa1111aaaa1111aaaa", "Sunday, Oct 4", "Seattle Reign FC",
                "bbbb2222bbbb2222bbbb2222bbbb2222", "Sunrise Stadium", "denver-summit-vs-seattle-reign",
            )
            + '<div class="StyledMatchList--1nggtrl fhXkdX d3w-match-list-date-group">'
            + '<div class="d3w-match-list-date-header"><span class="d3w-match-list-date">Saturday, Oct 17</span></div>'
            + '<div data-matchid="nwsl::Football_Match::dddd4444dddd4444dddd4444dddd4444" data-match-status="UPCOMING"></div>'
            + "</div></body></html>"
        )
        js.fetch.install({NWSL_SCHEDULE_URL: FakeFetchResponse(html)})

        with self.assertRaises(SyncSourceError):
            await fetch_nwsl_schedule(self.env)

    async def test_run_sync_survives_one_source_failing(self):
        # No fetch responses installed at all -- roster/fixtures/opponents
        # each call fetch and get FetchNotStubbed, wrapped as
        # SyncSourceError; headshots has no roster rows to look up in this
        # empty env, so it succeeds trivially rather than failing, and so
        # does opponent_rosters -- there are no opponents to try fetching.
        summary = await sync.run_sync(self.env)
        for job_name in ("roster", "fixtures", "opponents"):
            self.assertIn("error", summary[job_name])
        self.assertNotIn("error", summary["headshots"])
        self.assertNotIn("error", summary["opponent_rosters"])

    async def _seed_opponent(self, opponent_id="op_1", club="Angel City", source_ref=None, source_slug=None):
        await sync_exec(
            self.env,
            "INSERT INTO opponents (id, club, chip_label, source_ref, source_slug) VALUES (?, ?, ?, ?, ?)",
            opponent_id,
            club,
            club,
            source_ref,
            source_slug,
        )

    async def test_opponent_roster_sync_skips_a_club_with_no_source_on_file(self):
        await self._seed_opponent(source_ref=None, source_slug=None)

        result = await sync._sync_opponent_rosters(self.env)

        self.assertEqual(result["tracked"], 0)
        players = await sync_query(self.env, "SELECT COUNT(*) AS n FROM opponent_players")
        self.assertEqual(players[0]["n"], 0)

    async def test_opponent_roster_sync_inserts_real_players_for_a_tracked_club(self):
        await self._seed_opponent(source_ref="9587b8ce40624165903b6bc9fd252634", source_slug="angel-city-fc")
        roster_html = (
            "<html><body><table><tbody>"
            + _roster_row("cccc3333cccc3333cccc3333cccc3333", "Sam", "Striker", "sam-striker", 7, "Forward")
            + "</tbody></table></body></html>"
        )
        js.fetch.install(
            {
                "https://www.nwslsoccer.com/teams/9587b8ce40624165903b6bc9fd252634/angel-city-fc/roster": FakeFetchResponse(
                    roster_html
                )
            }
        )

        result = await sync._sync_opponent_rosters(self.env)

        self.assertEqual(result["tracked"], 1)
        self.assertEqual(result["clubs"]["Angel City"]["inserted"], 1)
        players = await sync_query(
            self.env, "SELECT name, jersey_number, position, opponent_id FROM opponent_players"
        )
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0]["name"], "Sam Striker")
        self.assertEqual(players[0]["jersey_number"], 7)
        self.assertEqual(players[0]["position"], "FWD")
        self.assertEqual(players[0]["opponent_id"], "op_1")

    async def test_opponent_roster_sync_records_a_per_club_error_without_raising(self):
        # A wrong or dead source_slug fails just that club's fetch (via
        # FetchNotStubbed here, standing in for a real 404) -- the job
        # itself still returns normally, per-club failures included.
        await self._seed_opponent(source_ref="9587b8ce40624165903b6bc9fd252634", source_slug="angel-city-fc")

        result = await sync._sync_opponent_rosters(self.env)

        self.assertIn("error", result["clubs"]["Angel City"])


async def sync_exec(env, sql, *params):
    from db import execute

    return await execute(env, sql, *params)


async def sync_query(env, sql, *params):
    from db import query

    return await query(env, sql, *params)


if __name__ == "__main__":
    unittest.main()
