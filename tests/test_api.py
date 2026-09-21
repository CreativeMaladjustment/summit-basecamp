"""End-to-end tests of the API, driven through on_fetch.

These run the real router, handlers and SQL against an in-memory SQLite
database standing in for D1. See fake_workers.py.
"""

import asyncio
import json
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from fake_workers import FakeRequest, install_runtime_stubs, make_env  # noqa: E402

install_runtime_stubs()

import entry  # noqa: E402

SCHEMA = [
    os.path.join(ROOT, "migrations", "0001_initial.sql"),
    os.path.join(ROOT, "migrations", "0002_roster.sql"),
    os.path.join(ROOT, "migrations", "0003_national_team.sql"),
]
SEED = os.path.join(ROOT, "seed", "dev_seed.sql")


def call(env, method, path, user="usr_ada", body=None):
    headers = {}
    if user:
        headers["X-Dev-User"] = user
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = FakeRequest(
        method=method,
        url="http://localhost:8787" + path,
        headers=headers,
        body=body,
    )
    response = asyncio.run(entry.on_fetch(request, env))
    payload = json.loads(response.body) if response.body else None
    return response.status, payload


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.env = make_env(SCHEMA, SEED)

    # --- routing ----------------------------------------------------------

    def test_health_reports_ok(self):
        status, payload = call(self.env, "GET", "/api/health", user=None)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_unknown_path_is_404(self):
        status, payload = call(self.env, "GET", "/api/nope")
        self.assertEqual(status, 404)
        self.assertIn("No route", payload["error"])

    def test_wrong_method_is_405(self):
        status, _ = call(self.env, "DELETE", "/api/groups")
        self.assertEqual(status, 405)

    def test_preflight_carries_cors_headers(self):
        request = FakeRequest(method="OPTIONS", url="http://localhost:8787/api/groups")
        response = asyncio.run(entry.on_fetch(request, self.env))
        self.assertEqual(response.status, 204)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    def test_preflight_response_has_no_body(self):
        # A 204 carrying a JSON body is rejected by real fetch implementations
        # even though the test double would accept it.
        request = FakeRequest(method="OPTIONS", url="http://localhost:8787/api/groups")
        response = asyncio.run(entry.on_fetch(request, self.env))
        self.assertFalse(response.body)

    def test_every_response_carries_cors_headers(self):
        request = FakeRequest(method="GET", url="http://localhost:8787/api/health")
        response = asyncio.run(entry.on_fetch(request, self.env))
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    # --- auth -------------------------------------------------------------

    def test_an_unidentified_caller_is_401(self):
        status, _ = call(self.env, "GET", "/api/groups", user=None)
        self.assertEqual(status, 401)

    def test_a_non_member_cannot_read_a_syndicate(self):
        asyncio.run(
            self.env.DB.prepare(
                "INSERT INTO users (id, email, name, auth_provider, auth_provider_id)"
                " VALUES ('usr_out', 'out@example.com', 'Out', 'google', 'dev-out')"
            ).run()
        )
        status, _ = call(self.env, "GET", "/api/groups/grp_summit", user="usr_out")
        self.assertEqual(status, 403)

    def test_sign_in_is_not_implemented_yet(self):
        status, _ = call(self.env, "POST", "/api/auth/session", user=None, body={})
        self.assertEqual(status, 501)

    # --- syndicates, fixtures and seats -----------------------------------

    def test_a_member_sees_their_syndicates(self):
        status, payload = call(self.env, "GET", "/api/groups")
        self.assertEqual(status, 200)
        self.assertEqual([g["id"] for g in payload["groups"]], ["grp_summit"])
        self.assertEqual(payload["groups"][0]["role"], "admin")

    def test_creating_a_syndicate_makes_the_creator_its_admin(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups",
            body={
                "name": "Away Day Crew",
                "season_year": 2027,
                "total_seats": 2,
                "package_cost_cents": 100000,
            },
        )
        self.assertEqual(status, 201)
        group_id = payload["group"]["id"]

        status, payload = call(self.env, "GET", "/api/groups/" + group_id)
        self.assertEqual(status, 200)
        self.assertEqual(payload["members"][0]["role"], "admin")

    def test_a_new_fixture_gets_a_seat_per_member(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/fixtures",
            body={
                "opponent": "Harbour City",
                "kickoff_at": "2026-11-01T19:30:00Z",
                "venue": "Summit Park",
                "weighted_value_cents": 7000,
                "tier": "cup",
            },
        )
        self.assertEqual(status, 201)
        fixture_id = payload["fixture"]["id"]

        status, payload = call(self.env, "GET", "/api/fixtures/{}/seats".format(fixture_id))
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["seats"]), 4)
        self.assertEqual(
            [seat["assigned_user_id"] for seat in payload["seats"]],
            ["usr_ada", "usr_bo", "usr_cyd", "usr_dev"],
        )

    def test_only_an_admin_can_add_a_fixture(self):
        status, _ = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/fixtures",
            user="usr_bo",
            body={
                "opponent": "Harbour City",
                "kickoff_at": "2026-11-01T19:30:00Z",
                "venue": "Summit Park",
                "weighted_value_cents": 7000,
            },
        )
        self.assertEqual(status, 403)

    def test_a_missing_field_is_rejected(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/fixtures",
            body={"opponent": "Harbour City"},
        )
        self.assertEqual(status, 400)
        self.assertIn("Missing required field", payload["error"])

    def test_a_non_integer_weighted_value_is_rejected_not_500ed(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/fixtures",
            body={
                "opponent": "Harbour City",
                "kickoff_at": "2026-11-01T19:30:00Z",
                "venue": "Summit Park",
                "weighted_value_cents": "not-a-number",
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("weighted_value_cents", payload["error"])

    def test_a_non_integer_group_field_is_rejected_not_500ed(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups",
            body={
                "name": "Away Day Crew",
                "season_year": "soon",
                "total_seats": 2,
                "package_cost_cents": 100000,
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("season_year", payload["error"])

    def test_a_zero_seat_group_is_rejected(self):
        status, _ = call(
            self.env,
            "POST",
            "/api/groups",
            body={
                "name": "Away Day Crew",
                "season_year": 2027,
                "total_seats": 0,
                "package_cost_cents": 100000,
            },
        )
        self.assertEqual(status, 400)

    def test_benching_a_seat_releases_it(self):
        status, payload = call(
            self.env, "PATCH", "/api/seats/seat_001", body={"status": "on_bench"}
        )
        self.assertEqual(status, 200)
        self.assertIsNone(payload["seat"]["assigned_user_id"])
        self.assertEqual(payload["seat"]["status"], "on_bench")

    def test_a_benched_seat_can_be_claimed_by_another_member(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_003",
            user="usr_bo",
            body={"status": "confirmed"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["seat"]["assigned_user_id"], "usr_bo")

    def test_a_seat_someone_else_holds_cannot_be_taken(self):
        status, _ = call(
            self.env,
            "PATCH",
            "/api/seats/seat_001",
            user="usr_bo",
            body={"status": "confirmed"},
        )
        self.assertEqual(status, 403)

    def test_a_resale_listing_needs_a_price(self):
        status, payload = call(
            self.env, "PATCH", "/api/seats/seat_001", body={"status": "resale_listed"}
        )
        self.assertEqual(status, 400)
        self.assertIn("resale_price_cents", payload["error"])

    def test_a_resale_price_must_be_a_positive_number(self):
        for bad_price in ("0", -500, "not-a-number", True):
            status, _ = call(
                self.env,
                "PATCH",
                "/api/seats/seat_001",
                body={"status": "resale_listed", "resale_price_cents": bad_price},
            )
            self.assertEqual(status, 400, "price {!r} should be rejected".format(bad_price))

    def test_an_unknown_status_is_rejected(self):
        status, _ = call(
            self.env, "PATCH", "/api/seats/seat_001", body={"status": "teleported"}
        )
        self.assertEqual(status, 400)

    def test_a_benched_seat_cannot_be_resold_without_being_claimed_first(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_003",
            user="usr_bo",
            body={"status": "resale_listed", "resale_price_cents": 5000},
        )
        self.assertEqual(status, 400)
        self.assertIn("can only be claimed", payload["error"])

    def test_a_claim_cannot_assign_the_seat_to_someone_else(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_003",
            user="usr_bo",
            body={"status": "confirmed", "assigned_user_id": "usr_cyd"},
        )
        self.assertEqual(status, 200)
        # The caller claiming it, not the assigned_user_id they sent, wins.
        self.assertEqual(payload["seat"]["assigned_user_id"], "usr_bo")

    def test_a_holder_cannot_reassign_their_seat_to_someone_else(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_001",
            body={"status": "gifted", "assigned_user_id": "usr_bo"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["seat"]["assigned_user_id"], "usr_ada")

    def test_a_stale_seat_write_is_rejected_as_a_conflict_not_overwritten(self):
        import handlers

        seat = asyncio.run(
            self.env.DB.prepare(
                "SELECT * FROM seat_allocations WHERE id = 'seat_003'"
            ).first()
        )
        # Two callers who both read the seat while it was still on the bench;
        # only the first write should land.
        first = asyncio.run(
            handlers._write_seat_if_unchanged(self.env, seat, "confirmed", "usr_bo", None, None)
        )
        second = asyncio.run(
            handlers._write_seat_if_unchanged(self.env, seat, "confirmed", "usr_cyd", None, None)
        )
        self.assertEqual(first, 1)
        self.assertEqual(second, 0)

    def test_a_past_fixture_does_not_appear_in_listings(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/fixtures",
            body={
                "opponent": "Yesterday United",
                "kickoff_at": "2020-01-01T12:00:00Z",
                "venue": "Summit Park",
                "weighted_value_cents": 1000,
            },
        )
        self.assertEqual(status, 201)
        fixture_id = payload["fixture"]["id"]
        status, payload = call(self.env, "GET", "/api/fixtures/{}/seats".format(fixture_id))
        seat_id = payload["seats"][0]["id"]
        call(self.env, "PATCH", "/api/seats/{}".format(seat_id), body={"status": "on_bench"})

        status, payload = call(self.env, "GET", "/api/groups/grp_summit/listings")
        self.assertNotIn(
            "Yesterday United", [listing["opponent"] for listing in payload["listings"]]
        )

    def test_listings_show_benched_and_resale_seats(self):
        status, payload = call(self.env, "GET", "/api/groups/grp_summit/listings")
        self.assertEqual(status, 200)
        statuses = sorted(listing["status"] for listing in payload["listings"])
        self.assertEqual(statuses, ["on_bench", "on_bench", "resale_listed"])
        self.assertIn("opponent", payload["listings"][0])

    # --- ledger -----------------------------------------------------------

    def test_the_ledger_nets_balances_and_proposes_a_settle_plan(self):
        status, payload = call(self.env, "GET", "/api/groups/grp_summit/ledger")
        self.assertEqual(status, 200)
        self.assertEqual(payload["balances"]["usr_ada"], 360000)
        self.assertEqual(payload["balances"]["usr_bo"], -120000)
        self.assertEqual(len(payload["settle_plan"]), 3)
        self.assertTrue(all(t["to"] == "usr_ada" for t in payload["settle_plan"]))

    def test_an_expense_splits_across_the_syndicate_but_not_the_payer(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/expenses",
            body={"amount_cents": 4000, "description": "Parking"},
        )
        self.assertEqual(status, 201)
        shares = payload["transactions"]
        self.assertEqual(len(shares), 3)
        self.assertTrue(all(share["recipient_id"] == "usr_ada" for share in shares))
        self.assertEqual(sum(share["amount_cents"] for share in shares), 3000)

    def test_an_expense_can_be_split_between_named_members(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/expenses",
            body={
                "amount_cents": 3000,
                "description": "Coach to the ground",
                "split_between": ["usr_ada", "usr_bo"],
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(len(payload["transactions"]), 1)
        self.assertEqual(payload["transactions"][0]["payer_id"], "usr_bo")
        self.assertEqual(payload["transactions"][0]["amount_cents"], 1500)

    def test_an_expense_cannot_name_an_outsider(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/expenses",
            body={
                "amount_cents": 3000,
                "description": "Coach",
                "split_between": ["usr_ada", "usr_nobody"],
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("usr_nobody", payload["error"])

    def test_a_zero_amount_expense_is_rejected(self):
        status, _ = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/expenses",
            body={"amount_cents": 0, "description": "Nothing"},
        )
        self.assertEqual(status, 400)

    def test_a_non_integer_amount_is_rejected_not_500ed(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/expenses",
            body={"amount_cents": "abc", "description": "Parking"},
        )
        self.assertEqual(status, 400)
        self.assertIn("amount_cents", payload["error"])

    def test_an_empty_split_between_is_rejected_not_silently_everyone(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/expenses",
            body={"amount_cents": 3000, "description": "Coach", "split_between": []},
        )
        self.assertEqual(status, 400)
        self.assertIn("split_between", payload["error"])

    def test_a_repeated_member_in_split_between_is_rejected(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/expenses",
            body={
                "amount_cents": 3000,
                "description": "Coach",
                "split_between": ["usr_ada", "usr_bo", "usr_bo"],
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("split_between", payload["error"])

    def test_settling_up_clears_only_that_pair(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/grp_summit/settle",
            body={"with_member_id": "usr_bo"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["settled_transactions"], 1)

        status, payload = call(self.env, "GET", "/api/groups/grp_summit/ledger")
        self.assertNotIn("usr_bo", payload["balances"])
        self.assertEqual(payload["balances"]["usr_ada"], 240000)

    # --- bios and preferences ---------------------------------------------

    def test_the_daily_bio_carries_a_static_asset_path(self):
        status, payload = call(self.env, "GET", "/api/bios/today")
        self.assertEqual(status, 200)
        self.assertEqual(payload["bio"]["player_name"], "Sophia Smith")
        self.assertTrue(payload["bio"]["image_path"].startswith("/assets/images/"))

    def test_preferences_round_trip(self):
        status, payload = call(
            self.env,
            "PUT",
            "/api/preferences",
            body={"notify_bench_alerts": False, "daily_bio_scope": "league_wide"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["preferences"]["daily_bio_scope"], "league_wide")
        self.assertEqual(payload["preferences"]["notify_bench_alerts"], 0)

        status, payload = call(self.env, "GET", "/api/preferences")
        self.assertEqual(payload["preferences"]["daily_bio_scope"], "league_wide")

    def test_a_non_boolean_preference_is_rejected(self):
        status, payload = call(
            self.env, "PUT", "/api/preferences", body={"notify_bench_alerts": "false"}
        )
        self.assertEqual(status, 400)
        self.assertIn("notify_bench_alerts", payload["error"])

    def test_an_unknown_bio_scope_is_rejected(self):
        status, payload = call(
            self.env, "PUT", "/api/preferences", body={"daily_bio_scope": "everywhere"}
        )
        self.assertEqual(status, 400)
        self.assertIn("daily_bio_scope", payload["error"])

    # --- roster and opponents -----------------------------------------------

    def test_roster_is_ordered_with_parsed_stats(self):
        status, payload = call(self.env, "GET", "/api/roster")
        self.assertEqual(status, 200)
        players = payload["players"]
        self.assertEqual(len(players), 10)
        self.assertEqual(players[0]["name"], "Rowan Vasquez")
        self.assertEqual(players[0]["stats"], [["Clean sheets", "7"], ["Saves", "54"], ["Starts", "19"]])
        self.assertNotIn("stats_json", players[0])

    def test_roster_requires_sign_in(self):
        status, payload = call(self.env, "GET", "/api/roster", user=None)
        self.assertEqual(status, 401)

    def test_roster_carries_national_team_history(self):
        status, payload = call(self.env, "GET", "/api/roster")
        self.assertEqual(status, 200)
        players = {p["id"]: p for p in payload["players"]}

        # Tess Aldridge: still capped for the USWNT.
        tess = players["p7"]
        self.assertEqual(tess["current_national_team"], "USWNT")
        self.assertEqual(len(tess["national_team_history"]), 1)
        self.assertIsNone(tess["national_team_history"][0]["year_end"])

        # Sloane Beckett: past Canada caps, not currently on a national team.
        sloane = players["p6"]
        self.assertIsNone(sloane["current_national_team"])
        self.assertEqual(sloane["national_team_history"][0]["year_end"], 2022)

        # Rowan Vasquez: never capped.
        rowan = players["p1"]
        self.assertIsNone(rowan["current_national_team"])
        self.assertEqual(rowan["national_team_history"], [])

    def test_opponents_nest_their_players(self):
        status, payload = call(self.env, "GET", "/api/opponents")
        self.assertEqual(status, 200)
        opponents = payload["opponents"]
        self.assertEqual(len(opponents), 3)
        portland = opponents[0]
        self.assertEqual(portland["club"], "Portland Thorns")
        self.assertEqual(portland["quick_stats"], [["Goals for", "31"], ["Goals against", "19"], ["Away wins", "5"]])
        self.assertEqual([p["name"] for p in portland["players"]], ["Marisol Vega", "Elin Sandberg", "Dara Whitfield"])
        self.assertTrue(portland["players"][0]["is_danger"])


class ScheduledTests(unittest.TestCase):
    def setUp(self):
        self.env = make_env(SCHEMA, SEED)

    def _unscheduled_count(self):
        row = asyncio.run(
            self.env.DB.prepare(
                "SELECT COUNT(*) AS n FROM player_bios WHERE scheduled_date IS NULL"
            ).first()
        )
        return row["n"]

    def test_the_morning_cron_is_a_no_op_when_todays_bio_is_already_set(self):
        import types as _types

        # The seed data already has bio_001 scheduled for today.
        before = self._unscheduled_count()
        asyncio.run(entry.on_scheduled(_types.SimpleNamespace(cron="0 8 * * *"), self.env, None))
        self.assertEqual(self._unscheduled_count(), before)

    def test_the_morning_cron_schedules_a_bio_when_none_is_set_for_today(self):
        import types as _types

        asyncio.run(
            self.env.DB.prepare(
                "UPDATE player_bios SET scheduled_date = NULL WHERE scheduled_date = DATE('now')"
            ).run()
        )
        before = self._unscheduled_count()
        asyncio.run(entry.on_scheduled(_types.SimpleNamespace(cron="0 8 * * *"), self.env, None))
        self.assertEqual(self._unscheduled_count(), before - 1)

        row = asyncio.run(
            self.env.DB.prepare(
                "SELECT COUNT(*) AS n FROM player_bios"
                " WHERE scheduled_date = DATE('now')"
            ).first()
        )
        self.assertEqual(row["n"], 1)

    def test_the_morning_cron_is_idempotent_across_retries(self):
        import types as _types

        asyncio.run(
            self.env.DB.prepare(
                "UPDATE player_bios SET scheduled_date = NULL WHERE scheduled_date = DATE('now')"
            ).run()
        )
        for _ in range(3):
            asyncio.run(
                entry.on_scheduled(_types.SimpleNamespace(cron="0 8 * * *"), self.env, None)
            )
        row = asyncio.run(
            self.env.DB.prepare(
                "SELECT COUNT(*) AS n FROM player_bios"
                " WHERE scheduled_date = DATE('now')"
            ).first()
        )
        self.assertEqual(row["n"], 1)

    def test_the_check_in_cron_runs_against_fixtures_three_days_out(self):
        import types as _types

        # Exercises the query; fixture fix_001 is seeded three days out.
        asyncio.run(entry.on_scheduled(_types.SimpleNamespace(cron="0 10 * * *"), self.env, None))

    def test_an_unknown_cron_is_ignored(self):
        import types as _types

        asyncio.run(entry.on_scheduled(_types.SimpleNamespace(cron="* * * * *"), self.env, None))


if __name__ == "__main__":
    unittest.main()
