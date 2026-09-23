"""End-to-end tests of the API, driven through on_fetch.

These run the real router, handlers and SQL against an in-memory SQLite
database standing in for D1. See fake_workers.py.
"""

import asyncio
import base64
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
    os.path.join(ROOT, "migrations", "0004_sync_metadata.sql"),
    os.path.join(ROOT, "migrations", "0005_roster_jersey_nullable.sql"),
    os.path.join(ROOT, "migrations", "0006_opponent_sync.sql"),
    os.path.join(ROOT, "migrations", "0007_fixture_source_ref_unique.sql"),
    os.path.join(ROOT, "migrations", "0008_group_invite_codes.sql"),
    os.path.join(ROOT, "migrations", "0009_user_contact_info.sql"),
    os.path.join(ROOT, "migrations", "0010_guest_password_auth.sql"),
    os.path.join(ROOT, "migrations", "0011_syndicate_seat_labels.sql"),
]
SEED = os.path.join(ROOT, "seed", "dev_seed.sql")


def call(env, method, path, user="usr_ada", body=None, authorization=None):
    headers = {}
    if user:
        headers["X-Dev-User"] = user
    if body is not None:
        headers["Content-Type"] = "application/json"
    if authorization is not None:
        headers["Authorization"] = authorization
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

    def test_guest_slots_are_listed_unauthenticated(self):
        status, payload = call(self.env, "GET", "/api/auth/guests", user=None)
        self.assertEqual(status, 200)
        self.assertEqual(
            [g["id"] for g in payload["guests"]],
            ["usr_guest1", "usr_guest2", "usr_guest3", "usr_guest4", "usr_guest5", "usr_guest6"],
        )
        self.assertEqual(payload["guests"][0]["name"], "Guest 1")

    def test_sign_in_is_unavailable_with_no_site_password_configured(self):
        # self.env (SEED-backed, no site_pwd) is the default -- a deployment
        # that never set SITE_PWD refuses every sign-in rather than falling
        # open to an empty/None comparison.
        status, payload = call(
            self.env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "password": "anything"},
        )
        self.assertEqual(status, 503)

    def test_sign_in_rejects_the_wrong_password(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        status, _ = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "password": "nope"},
        )
        self.assertEqual(status, 401)

    def test_sign_in_rejects_a_non_string_password(self):
        # A JSON number reaches verify_site_password as an int; without an
        # isinstance check it would hit hmac.compare_digest and raise
        # TypeError, surfacing as an uncaught 500 instead of a plain 401.
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        status, _ = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "password": 12345},
        )
        self.assertEqual(status, 401)

    def test_sign_in_rejects_an_unknown_guest_id(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        status, _ = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_ada", "password": "letmein"},
        )
        self.assertEqual(status, 400)

    def test_sign_in_issues_a_session_token_that_authenticates(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        status, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest2", "password": "letmein"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["id"], "usr_guest2")
        token = payload["token"]
        self.assertTrue(token)

        # The minted token, not X-Dev-User, is what proves who this is.
        status, payload = call(
            env, "GET", "/api/me", user=None, authorization="Bearer " + token
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["id"], "usr_guest2")

    def test_sign_in_with_password_returns_a_device_token(self):
        # The device is meant to remember this instead of the raw password
        # (see docs/backend.md "Sign-in") -- a CodeQL clear-text-storage
        # finding on the frontend is exactly what this replaces.
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        status, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "password": "letmein"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["device_token"])

    def test_sign_in_with_a_valid_device_token_needs_no_password(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        _, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "password": "letmein"},
        )
        device_token = payload["device_token"]

        status, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest3", "device_token": device_token},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["id"], "usr_guest3")
        self.assertEqual(payload["device_token"], device_token)

    def test_sign_in_rejects_an_unknown_device_token(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        status, _ = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "device_token": "made-up-token"},
        )
        self.assertEqual(status, 401)

    def test_rotating_site_pwd_invalidates_outstanding_device_tokens(self):
        # A device token is fingerprinted to the password that minted it
        # (src/auth._password_fingerprint), so rotating SITE_PWD rejects it
        # immediately -- not just once its own 30-day TTL happens to run
        # out, which would otherwise let an old device sign in for up to a
        # month after the password it trusted was retired.
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        _, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "password": "letmein"},
        )
        device_token = payload["device_token"]

        env.SITE_PWD = "newpassword"
        status, _ = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1", "device_token": device_token},
        )
        self.assertEqual(status, 401)

    def test_sign_in_with_neither_password_nor_device_token_is_400(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        status, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest1"},
        )
        self.assertEqual(status, 400)
        self.assertIn("password", payload["error"])

    def test_a_guest_can_rename_their_own_slot(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        _, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest3", "password": "letmein"},
        )
        token = payload["token"]

        status, payload = call(
            env, "PATCH", "/api/me", user=None, authorization="Bearer " + token,
            body={"name": "Priya"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["name"], "Priya")

        status, payload = call(env, "GET", "/api/auth/guests", user=None)
        self.assertIn("Priya", [g["name"] for g in payload["guests"]])

    def test_renaming_to_an_empty_name_is_rejected(self):
        env = make_env(SCHEMA, SEED, site_pwd="letmein")
        _, payload = call(
            env, "POST", "/api/auth/session", user=None,
            body={"user_id": "usr_guest4", "password": "letmein"},
        )
        token = payload["token"]
        status, _ = call(
            env, "PATCH", "/api/me", user=None, authorization="Bearer " + token,
            body={"name": "   "},
        )
        self.assertEqual(status, 400)

    # --- profile ------------------------------------------------------------

    def test_a_member_can_update_their_own_profile(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/me",
            body={"name": "Ada Okafor", "phone": "(303) 555-0142", "contact_email": "ada@family.example"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["name"], "Ada Okafor")
        self.assertEqual(payload["user"]["phone"], "(303) 555-0142")
        self.assertEqual(payload["user"]["contact_email"], "ada@family.example")

        status, payload = call(self.env, "GET", "/api/me")
        self.assertEqual(payload["user"]["name"], "Ada Okafor")

    def test_updating_the_profile_accepts_a_partial_body(self):
        status, payload = call(self.env, "PATCH", "/api/me", body={"phone": "(303) 555-0199"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["phone"], "(303) 555-0199")
        self.assertEqual(payload["user"]["name"], "Ada")  # unchanged (see seed/dev_seed.sql)

    def test_phone_and_contact_email_can_be_cleared_with_an_empty_string(self):
        call(self.env, "PATCH", "/api/me", body={"phone": "(303) 555-0142"})
        status, payload = call(self.env, "PATCH", "/api/me", body={"phone": ""})
        self.assertEqual(status, 200)
        self.assertIsNone(payload["user"]["phone"])

    def test_phone_and_contact_email_can_be_cleared_with_an_explicit_null(self):
        call(
            self.env,
            "PATCH",
            "/api/me",
            body={"phone": "(303) 555-0142", "contact_email": "ada@family.example"},
        )
        status, payload = call(
            self.env, "PATCH", "/api/me", body={"phone": None, "contact_email": None}
        )
        self.assertEqual(status, 200)
        self.assertIsNone(payload["user"]["phone"])
        self.assertIsNone(payload["user"]["contact_email"])

    def test_updating_the_profile_rejects_an_empty_name(self):
        status, payload = call(self.env, "PATCH", "/api/me", body={"name": "   "})
        self.assertEqual(status, 400)
        self.assertIn("name", payload["error"])

    def test_updating_the_profile_with_nothing_to_update_is_400(self):
        status, payload = call(self.env, "PATCH", "/api/me", body={})
        self.assertEqual(status, 400)
        self.assertIn("Nothing to update", payload["error"])

    def test_updating_the_profile_rejects_a_non_string_phone(self):
        status, payload = call(self.env, "PATCH", "/api/me", body={"phone": 5551234})
        self.assertEqual(status, 400)
        self.assertIn("phone", payload["error"])

    # --- syndicates, fixtures and seats -----------------------------------

    def test_a_member_sees_their_syndicates(self):
        status, payload = call(self.env, "GET", "/api/groups")
        self.assertEqual(status, 200)
        self.assertEqual([g["id"] for g in payload["groups"]], ["grp_summit"])
        self.assertEqual(payload["groups"][0]["role"], "admin")
        # Present so a client can skip straight into a syndicate someone is
        # already a member of instead of always landing on create/join --
        # same seat_label create_group and update_member accept elsewhere.
        self.assertIn("seat_label", payload["groups"][0])

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

    def test_creating_a_syndicate_accepts_section_row_and_seat_labels(self):
        status, payload = call(
            self.env,
            "POST",
            "/api/groups",
            body={
                "name": "Away Day Crew",
                "season_year": 2027,
                "total_seats": 2,
                "package_cost_cents": 100000,
                "section": "114",
                "seat_row": "8",
                "seat_labels": "3, 4",
                "my_seat_label": "3",
            },
        )
        self.assertEqual(status, 201)
        group = payload["group"]
        self.assertEqual(group["section"], "114")
        self.assertEqual(group["seat_row"], "8")
        self.assertEqual(group["seat_labels"], "3, 4")

        status, payload = call(self.env, "GET", "/api/groups/" + group["id"])
        self.assertEqual(status, 200)
        self.assertEqual(payload["members"][0]["seat_label"], "3")

    def test_creating_a_syndicate_without_seat_details_leaves_them_null(self):
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
        group = payload["group"]
        self.assertIsNone(group["section"])
        self.assertIsNone(group["seat_row"])
        self.assertIsNone(group["seat_labels"])

    def test_a_member_can_set_their_own_seat_label(self):
        status, payload = call(
            self.env, "PATCH", "/api/groups/grp_summit/members/usr_ada",
            body={"seat_label": "3"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["member"]["seat_label"], "3")

        status, _ = call(
            self.env, "PATCH", "/api/groups/grp_summit/members/usr_ada",
            body={"seat_label": None},
        )
        self.assertEqual(status, 200)

    def test_a_member_cannot_set_another_members_seat_label(self):
        # usr_bo is a plain member, not the admin -- only usr_ada (admin) or
        # usr_cyd themselves may edit usr_cyd's seat_label.
        status, _ = call(
            self.env, "PATCH", "/api/groups/grp_summit/members/usr_cyd",
            user="usr_bo", body={"seat_label": "5"},
        )
        self.assertEqual(status, 403)

    def test_an_admin_can_set_the_total_package_price(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit",
            body={"package_cost_cents": 500000},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["group"]["package_cost_cents"], 500000)

        status, payload = call(self.env, "GET", "/api/groups/grp_summit")
        self.assertEqual(payload["group"]["package_cost_cents"], 500000)

    def test_a_non_admin_cannot_set_the_package_price(self):
        status, _ = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit",
            user="usr_bo",
            body={"package_cost_cents": 500000},
        )
        self.assertEqual(status, 403)

    def test_updating_a_group_rejects_an_empty_name(self):
        status, payload = call(
            self.env, "PATCH", "/api/groups/grp_summit", body={"name": ""}
        )
        self.assertEqual(status, 400)
        self.assertIn("name", payload["error"])

    def test_a_member_can_edit_their_own_default_seat_number(self):
        # All 4 of grp_summit's seats already have a default holder (see
        # seed/dev_seed.sql), so clearing usr_bo's own to null -- rather
        # than moving it to a number already taken by someone else -- is
        # the real self-service change available to test here.
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_bo",
            user="usr_bo",
            body={"default_seat_number": None},
        )
        self.assertEqual(status, 200)
        self.assertIsNone(payload["member"]["default_seat_number"])

    def test_a_member_cannot_edit_someone_elses_seat_number(self):
        status, _ = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_cyd",
            user="usr_bo",
            body={"default_seat_number": None},
        )
        self.assertEqual(status, 403)

    def test_an_admin_can_edit_any_members_default_seat_number(self):
        # usr_ada (the admin) frees seat 1 first, so reassigning it to
        # usr_cyd below doesn't collide with usr_ada's own.
        call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_ada",
            body={"default_seat_number": None},
        )
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_cyd",
            body={"default_seat_number": 1},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["member"]["default_seat_number"], 1)

    def test_a_default_seat_number_cannot_collide_with_another_member(self):
        # usr_ada already holds default seat 1.
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_bo",
            body={"default_seat_number": 1},
        )
        self.assertEqual(status, 409)

    def test_a_default_seat_number_cannot_exceed_total_seats(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_bo",
            body={"default_seat_number": 99},
        )
        self.assertEqual(status, 400)

    def test_a_member_cannot_change_their_own_role(self):
        status, _ = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_bo",
            user="usr_bo",
            body={"role": "admin"},
        )
        self.assertEqual(status, 403)

    def test_an_admin_can_promote_a_member(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_bo",
            body={"role": "admin"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["member"]["role"], "admin")

    def test_the_only_admin_cannot_be_demoted(self):
        # usr_ada is grp_summit's sole admin (see seed/dev_seed.sql).
        # Demoting them would leave nobody who can pass require_admin.
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_ada",
            body={"role": "member"},
        )
        self.assertEqual(status, 409)

        status, payload = call(self.env, "GET", "/api/groups/grp_summit/members")
        ada = next(m for m in payload["members"] if m["id"] == "usr_ada")
        self.assertEqual(ada["role"], "admin")

    def test_an_admin_can_be_demoted_once_another_admin_exists(self):
        call(self.env, "PATCH", "/api/groups/grp_summit/members/usr_bo", body={"role": "admin"})
        status, payload = call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_ada",
            body={"role": "member"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["member"]["role"], "member")

    # --- invite codes -------------------------------------------------------

    def test_a_new_syndicate_gets_an_invite_code(self):
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
        self.assertTrue(payload["group"]["invite_code"])

    def test_joining_by_invite_code_adds_a_member(self):
        asyncio.run(
            self.env.DB.prepare(
                "INSERT INTO users (id, email, name, auth_provider, auth_provider_id)"
                " VALUES ('usr_out', 'out@example.com', 'Out', 'google', 'dev-out')"
            ).run()
        )
        status, payload = call(
            self.env,
            "POST",
            "/api/groups/join",
            user="usr_out",
            body={"invite_code": "summit01"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["group"]["id"], "grp_summit")
        joined = next(m for m in payload["members"] if m["id"] == "usr_out")
        self.assertEqual(joined["role"], "member")
        self.assertIsNone(joined["default_seat_number"])

        status, payload = call(self.env, "GET", "/api/groups", user="usr_out")
        self.assertEqual([g["id"] for g in payload["groups"]], ["grp_summit"])

    def test_an_invalid_invite_code_is_404(self):
        status, payload = call(
            self.env, "POST", "/api/groups/join", body={"invite_code": "NOPE0000"}
        )
        self.assertEqual(status, 404)

    def test_joining_a_syndicate_already_belonged_to_is_409(self):
        status, _ = call(
            self.env, "POST", "/api/groups/join", body={"invite_code": "SUMMIT01"}
        )
        self.assertEqual(status, 409)

    def test_an_admin_can_rotate_the_invite_code(self):
        status, payload = call(
            self.env, "GET", "/api/groups/grp_summit"
        )
        original = payload["group"]["invite_code"]

        status, payload = call(
            self.env, "POST", "/api/groups/grp_summit/invite-code/rotate"
        )
        self.assertEqual(status, 200)
        self.assertNotEqual(payload["group"]["invite_code"], original)

        status, _ = call(
            self.env, "POST", "/api/groups/join", user="usr_bo", body={"invite_code": original}
        )
        self.assertEqual(status, 404)

    def test_a_non_admin_cannot_rotate_the_invite_code(self):
        status, _ = call(
            self.env, "POST", "/api/groups/grp_summit/invite-code/rotate", user="usr_bo"
        )
        self.assertEqual(status, 403)

    # --- resizing a syndicate -------------------------------------------

    def test_an_admin_can_grow_total_seats(self):
        status, payload = call(
            self.env, "PATCH", "/api/groups/grp_summit", body={"total_seats": 5}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["group"]["total_seats"], 5)

        status, payload = call(self.env, "GET", "/api/fixtures/fix_001/seats")
        self.assertEqual(len(payload["seats"]), 5)
        new_seat = next(s for s in payload["seats"] if s["seat_number"] == 5)
        self.assertEqual(new_seat["status"], "on_bench")
        self.assertIsNone(new_seat["assigned_user_id"])

        status, payload = call(self.env, "GET", "/api/fixtures/fix_002/seats")
        self.assertEqual(len(payload["seats"]), 5)

    def test_shrinking_total_seats_is_blocked_by_an_occupied_seat(self):
        # fix_001's seat 4 is resale_listed and fix_002's seat 4 is confirmed
        # (see seed/dev_seed.sql) -- shrinking to 3 would destroy both. Clear
        # usr_dev's default seat first so only this guard is under test.
        call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_dev",
            body={"default_seat_number": None},
        )

        status, _ = call(
            self.env, "PATCH", "/api/groups/grp_summit", body={"total_seats": 3}
        )
        self.assertEqual(status, 409)

        status, payload = call(self.env, "GET", "/api/groups/grp_summit")
        self.assertEqual(payload["group"]["total_seats"], 4)

    def test_shrinking_total_seats_is_blocked_by_a_members_default_seat(self):
        # usr_dev's default_seat_number is 4 (see seed/dev_seed.sql). Free
        # both seat-4 allocations first so only this guard is under test.
        call(self.env, "PATCH", "/api/seats/seat_004", body={"status": "on_bench", "assigned_user_id": None})
        call(self.env, "PATCH", "/api/seats/seat_008", body={"status": "on_bench", "assigned_user_id": None})

        status, _ = call(self.env, "PATCH", "/api/groups/grp_summit", body={"total_seats": 3})
        self.assertEqual(status, 409)

    def test_shrinking_total_seats_removes_the_freed_bench_seats(self):
        call(
            self.env,
            "PATCH",
            "/api/groups/grp_summit/members/usr_dev",
            body={"default_seat_number": None},
        )
        call(self.env, "PATCH", "/api/seats/seat_004", body={"status": "on_bench", "assigned_user_id": None})
        call(self.env, "PATCH", "/api/seats/seat_008", body={"status": "on_bench", "assigned_user_id": None})

        status, payload = call(
            self.env, "PATCH", "/api/groups/grp_summit", body={"total_seats": 3}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["group"]["total_seats"], 3)

        status, payload = call(self.env, "GET", "/api/fixtures/fix_001/seats")
        self.assertEqual(len(payload["seats"]), 3)
        status, payload = call(self.env, "GET", "/api/fixtures/fix_002/seats")
        self.assertEqual(len(payload["seats"]), 3)

    def test_a_non_admin_cannot_change_total_seats(self):
        status, _ = call(
            self.env, "PATCH", "/api/groups/grp_summit", user="usr_bo", body={"total_seats": 5}
        )
        self.assertEqual(status, 403)

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
        # usr_bo (not an admin) holds seat_002 -- unlike usr_ada, who holds
        # seat_001 but is also the syndicate admin and so gets the admin
        # override tested below, a plain holder still cannot do this.
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_002",
            user="usr_bo",
            body={"status": "gifted", "assigned_user_id": "usr_cyd"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["seat"]["assigned_user_id"], "usr_bo")

    def test_an_admin_can_reassign_a_seat_held_by_someone_else(self):
        # seat_002 belongs to usr_bo, not usr_ada -- this is the override a
        # regular holder (tested above) does not get.
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_002",
            body={"status": "confirmed", "assigned_user_id": "usr_cyd"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["seat"]["assigned_user_id"], "usr_cyd")
        self.assertEqual(payload["seat"]["status"], "confirmed")

    def test_an_admin_can_assign_an_unclaimed_seat_to_any_member(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_003",
            body={"status": "confirmed", "assigned_user_id": "usr_dev"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["seat"]["assigned_user_id"], "usr_dev")

    def test_an_admin_can_bench_a_seat_held_by_someone_else(self):
        status, payload = call(
            self.env, "PATCH", "/api/seats/seat_002", body={"status": "on_bench"}
        )
        self.assertEqual(status, 200)
        self.assertIsNone(payload["seat"]["assigned_user_id"])

    def test_an_admin_cannot_assign_a_seat_to_a_non_member(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_003",
            body={"status": "confirmed", "assigned_user_id": "usr_ghost"},
        )
        self.assertEqual(status, 400)
        self.assertIn("not a member", payload["error"])

    def test_an_admin_cannot_bench_a_seat_while_also_assigning_it(self):
        # A benched seat with a holder would be unclaimable through the
        # normal claim path, which treats any holder as authoritative.
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_002",
            body={"status": "on_bench", "assigned_user_id": "usr_bo"},
        )
        self.assertEqual(status, 400)
        self.assertIn("on_bench", payload["error"])

    def test_a_non_admin_still_cannot_reassign_someone_elses_seat(self):
        status, payload = call(
            self.env,
            "PATCH",
            "/api/seats/seat_002",
            user="usr_cyd",
            body={"status": "confirmed", "assigned_user_id": "usr_cyd"},
        )
        self.assertEqual(status, 403)

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

    # --- profile picture ----------------------------------------------------

    def test_a_member_can_upload_and_fetch_their_own_avatar(self):
        image_bytes = b"\x89PNG\r\n\x1a\n not a real png but non-empty"
        status, payload = call(
            self.env,
            "PUT",
            "/api/me/avatar",
            body={
                "content_type": "image/png",
                "image_base64": base64.b64encode(image_bytes).decode(),
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["user"]["avatar_url"], "/api/avatars/usr_ada")

        request = FakeRequest(method="GET", url="http://localhost:8787/api/avatars/usr_ada")
        response = asyncio.run(entry.on_fetch(request, self.env))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, image_bytes)
        self.assertEqual(response.headers.get("Content-Type"), "image/png")

    def test_fetching_an_avatar_that_was_never_uploaded_is_404(self):
        request = FakeRequest(method="GET", url="http://localhost:8787/api/avatars/usr_bo")
        response = asyncio.run(entry.on_fetch(request, self.env))
        self.assertEqual(response.status, 404)

    def test_an_avatar_upload_rejects_an_unsupported_content_type(self):
        status, payload = call(
            self.env,
            "PUT",
            "/api/me/avatar",
            body={"content_type": "image/gif", "image_base64": base64.b64encode(b"x").decode()},
        )
        self.assertEqual(status, 400)
        self.assertIn("content_type", payload["error"])

    def test_an_avatar_upload_rejects_invalid_base64(self):
        status, payload = call(
            self.env,
            "PUT",
            "/api/me/avatar",
            body={"content_type": "image/png", "image_base64": "not-valid-base64!!"},
        )
        self.assertEqual(status, 400)

    def test_an_avatar_upload_rejects_a_non_string_image_base64(self):
        # A bare int/list/bool would otherwise reach base64.b64decode() and
        # raise an uncaught TypeError (a 500), not a clean 400.
        for bad_value in (12345, ["not", "a", "string"], True):
            status, payload = call(
                self.env,
                "PUT",
                "/api/me/avatar",
                body={"content_type": "image/png", "image_base64": bad_value},
            )
            self.assertEqual(status, 400, "value {!r} should be rejected".format(bad_value))
            self.assertIn("image_base64", payload["error"])

    def test_an_avatar_upload_rejects_an_oversized_image(self):
        oversized = base64.b64encode(b"x" * (2 * 1024 * 1024 + 1)).decode()
        status, payload = call(
            self.env,
            "PUT",
            "/api/me/avatar",
            body={"content_type": "image/png", "image_base64": oversized},
        )
        self.assertEqual(status, 400)
        self.assertIn("2 MiB", payload["error"])

    def test_re_uploading_an_avatar_replaces_the_old_one(self):
        # A different content_type on the second upload too -- proves this
        # replaces the single stored object rather than leaving an orphaned
        # copy under the old content type.
        first = base64.b64encode(b"first-image-bytes").decode()
        second = base64.b64encode(b"second-image-bytes-here").decode()
        call(self.env, "PUT", "/api/me/avatar", body={"content_type": "image/png", "image_base64": first})
        call(self.env, "PUT", "/api/me/avatar", body={"content_type": "image/webp", "image_base64": second})

        request = FakeRequest(method="GET", url="http://localhost:8787/api/avatars/usr_ada")
        response = asyncio.run(entry.on_fetch(request, self.env))
        self.assertEqual(response.body, b"second-image-bytes-here")
        self.assertEqual(response.headers.get("Content-Type"), "image/webp")

    # --- roster and opponents -----------------------------------------------

    def test_roster_is_ordered_with_parsed_stats(self):
        status, payload = call(self.env, "GET", "/api/roster")
        self.assertEqual(status, 200)
        players = payload["players"]
        self.assertEqual(len(players), 28)
        self.assertEqual(players[0]["name"], "Abby Smith")
        self.assertEqual(players[0]["stats"], [["Position", "Goalkeeper"], ["Nationality", "USA"]])
        self.assertNotIn("stats_json", players[0])

    def test_roster_requires_sign_in(self):
        status, payload = call(self.env, "GET", "/api/roster", user=None)
        self.assertEqual(status, 401)

    def test_roster_carries_national_team_history(self):
        # No sourced cap history is seeded yet (seed/dev_seed.sql), so every
        # player comes back with an empty history rather than invented caps.
        status, payload = call(self.env, "GET", "/api/roster")
        self.assertEqual(status, 200)
        players = {p["id"]: p for p in payload["players"]}

        abby = players["p1"]
        self.assertIsNone(abby["current_national_team"])
        self.assertEqual(abby["national_team_history"], [])

    def test_opponents_nest_their_players(self):
        status, payload = call(self.env, "GET", "/api/opponents")
        self.assertEqual(status, 200)
        opponents = payload["opponents"]
        # All 15 other NWSL clubs are seeded (see seed/opponents_seed.sql),
        # not just Denver Summit's remaining 2026 opponents.
        self.assertEqual(len(opponents), 15)
        angel_city = opponents[0]
        self.assertEqual(angel_city["club"], "Angel City")
        self.assertEqual(angel_city["source_ref"], "9587b8ce40624165903b6bc9fd252634")
        # No real per-club rosters are seeded -- opponent_players is
        # populated by src/sync.py's _sync_opponent_rosters, not by hand.
        self.assertEqual(angel_city["quick_stats"], [])
        self.assertEqual(angel_city["players"], [])


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

    # --- admin sync -----------------------------------------------------

    def test_trigger_sync_is_unavailable_with_no_token_configured(self):
        # self.env (SEED-backed, no sync_admin_token) is the default -- a
        # deployment that never set the secret refuses every call, rather
        # than falling open.
        status, payload = call(
            self.env, "POST", "/api/admin/sync", user=None, authorization="Bearer anything"
        )
        self.assertEqual(status, 503)
        self.assertIn("SYNC_ADMIN_TOKEN", payload["error"])

    def test_trigger_sync_rejects_a_missing_token(self):
        env = make_env(SCHEMA, SEED, sync_admin_token="s3cret")
        status, payload = call(env, "POST", "/api/admin/sync", user=None)
        self.assertEqual(status, 401)

    def test_trigger_sync_rejects_the_wrong_token(self):
        env = make_env(SCHEMA, SEED, sync_admin_token="s3cret")
        status, payload = call(
            env, "POST", "/api/admin/sync", user=None, authorization="Bearer nope"
        )
        self.assertEqual(status, 401)

    def test_trigger_sync_does_not_require_a_signed_in_user(self):
        # The caller is a GitHub Actions job with the shared secret, not a
        # syndicate member -- no X-Dev-User/session is sent at all here.
        env = make_env(SCHEMA, SEED, sync_admin_token="s3cret")
        status, payload = call(
            env, "POST", "/api/admin/sync", user=None, authorization="Bearer s3cret"
        )
        self.assertEqual(status, 200)
        self.assertIn("summary", payload)
        # No fetch responses are stubbed in this test module, so every
        # source job fails fast with SyncSourceError/FetchNotStubbed rather
        # than hanging or making a real network call -- run_sync itself is
        # exercised end-to-end against real page markup in test_sync.py.
        for job_name in ("roster", "fixtures", "opponents"):
            self.assertIn("error", payload["summary"][job_name])


if __name__ == "__main__":
    unittest.main()
