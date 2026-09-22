"""Endpoint handlers.

Every handler takes ``(request, env, params)`` and returns a Response.
``params`` holds the path parameters the router pulled out of the URL.
"""

import hmac
import json

from auth import current_user, require_admin, require_membership
from db import batch, execute, new_id, query, query_one
from responses import ApiError, json_response, read_json, require, require_int
from splits import net_balances, settle_plan, split_equally
from sync import run_sync

SEAT_STATUSES = ("confirmed", "on_bench", "gifted", "resale_listed")
FIXTURE_TIERS = ("rivalry", "standard", "cup")
BIO_SCOPES = ("home_first", "summit_only", "league_wide")


# --- health and identity ---------------------------------------------------


async def health(request, env, params):
    # Touches D1 so the check fails loudly when migrations have not been run.
    await query_one(env, "SELECT 1 AS ok")
    return json_response({"status": "ok", "environment": env.ENVIRONMENT})


async def begin_session(request, env, params):
    """Exchange a Google/Apple ID token for a session token.

    Not implemented in this scaffold. Verifying the provider's JWT against its
    JWKS and writing `session:<token>` into the SESSIONS KV namespace is the
    only piece missing; auth.py already reads the other end of it.
    """
    return json_response(
        {"error": "Sign-in is not wired up yet in this scaffold"},
        status=501,
    )


async def get_me(request, env, params):
    user = await current_user(request, env)
    prefs = await query_one(
        env, "SELECT * FROM user_notification_prefs WHERE user_id = ?", user["id"]
    )
    return json_response({"user": user, "preferences": prefs})


# --- syndicates ------------------------------------------------------------


async def list_groups(request, env, params):
    user = await current_user(request, env)
    groups = await query(
        env,
        """
        SELECT g.*, m.role, m.default_seat_number
        FROM groups g
        JOIN group_members m ON m.group_id = g.id
        WHERE m.user_id = ?
        ORDER BY g.season_year DESC, g.name
        """,
        user["id"],
    )
    return json_response({"groups": groups})


async def create_group(request, env, params):
    user = await current_user(request, env)
    body = await read_json(request)
    (name,) = require(body, "name")
    season_year = require_int(body, "season_year", minimum=1900)
    total_seats = require_int(body, "total_seats", minimum=1)
    package_cost_cents = require_int(body, "package_cost_cents", minimum=0)

    group_id = new_id("grp")
    await batch(
        env,
        [
            (
                """
                INSERT INTO groups
                    (id, name, season_year, total_seats, package_cost_cents, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    group_id,
                    name,
                    season_year,
                    total_seats,
                    package_cost_cents,
                    user["id"],
                ),
            ),
            (
                """
                INSERT INTO group_members (group_id, user_id, default_seat_number, role)
                VALUES (?, ?, ?, 'admin')
                """,
                (group_id, user["id"], 1),
            ),
        ],
    )
    group = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
    return json_response({"group": group}, status=201)


async def get_group(request, env, params):
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])

    group = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
    if group is None:
        raise ApiError(404, "No such syndicate")
    members = await _members(env, group_id)
    return json_response({"group": group, "members": members})


async def list_members(request, env, params):
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])
    return json_response({"members": await _members(env, group_id)})


async def _members(env, group_id):
    return await query(
        env,
        """
        SELECT u.id, u.name, u.email, u.avatar_url, m.role, m.default_seat_number
        FROM group_members m
        JOIN users u ON u.id = m.user_id
        WHERE m.group_id = ?
        ORDER BY m.default_seat_number, u.name
        """,
        group_id,
    )


# --- fixtures and seats ----------------------------------------------------


async def list_fixtures(request, env, params):
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])

    fixtures = await query(
        env,
        "SELECT * FROM fixtures WHERE group_id = ? ORDER BY kickoff_at",
        group_id,
    )
    return json_response({"fixtures": fixtures})


async def create_fixture(request, env, params):
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_admin(env, group_id, user["id"])

    body = await read_json(request)
    opponent, kickoff_at, venue = require(body, "opponent", "kickoff_at", "venue")
    weighted_value_cents = require_int(body, "weighted_value_cents", minimum=0)
    tier = body.get("tier", "standard")
    if tier not in FIXTURE_TIERS:
        raise ApiError(400, "tier must be one of: " + ", ".join(FIXTURE_TIERS))

    group = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
    if group is None:
        raise ApiError(404, "No such syndicate")

    fixture_id = new_id("fix")
    writes = [
        (
            """
            INSERT INTO fixtures
                (id, group_id, opponent, kickoff_at, venue, tier, weighted_value_cents)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fixture_id,
                group_id,
                opponent,
                kickoff_at,
                venue,
                tier,
                weighted_value_cents,
            ),
        )
    ]

    # Seed one allocation per seat, pre-assigned to whoever holds that seat
    # number by default. Members move them to the bench from there.
    members = await _members(env, group_id)
    by_seat = {
        member["default_seat_number"]: member["id"]
        for member in members
        if member.get("default_seat_number")
    }
    for seat_number in range(1, int(group["total_seats"]) + 1):
        writes.append(
            (
                """
                INSERT INTO seat_allocations
                    (id, fixture_id, seat_number, assigned_user_id, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    new_id("seat"),
                    fixture_id,
                    seat_number,
                    by_seat.get(seat_number),
                    "confirmed" if by_seat.get(seat_number) else "on_bench",
                ),
            )
        )

    await batch(env, writes)
    fixture = await query_one(env, "SELECT * FROM fixtures WHERE id = ?", fixture_id)
    return json_response({"fixture": fixture}, status=201)


async def list_seats(request, env, params):
    user = await current_user(request, env)
    fixture = await _fixture_for_member(env, params["fixture_id"], user["id"])
    seats = await query(
        env,
        """
        SELECT s.*, u.name AS assigned_user_name
        FROM seat_allocations s
        LEFT JOIN users u ON u.id = s.assigned_user_id
        WHERE s.fixture_id = ?
        ORDER BY s.seat_number
        """,
        fixture["id"],
    )
    return json_response({"fixture": fixture, "seats": seats})


async def update_seat(request, env, params):
    """Claim a benched seat, or -- as its holder -- bench it, gift it, or list it.

    A seat with no holder can only be claimed (set to 'confirmed', for the
    caller themselves): a member cannot gift or resell a seat they have not
    first taken, and cannot assign a seat to anyone but themselves -- this
    endpoint has no transfer flow. A seat with a holder can only be changed by
    that holder.
    """
    user = await current_user(request, env)
    body = await read_json(request)

    seat = await query_one(
        env, "SELECT * FROM seat_allocations WHERE id = ?", params["allocation_id"]
    )
    if seat is None:
        raise ApiError(404, "No such seat")
    await _fixture_for_member(env, seat["fixture_id"], user["id"])

    holder = seat["assigned_user_id"]
    status = body.get("status", seat["status"])
    if status not in SEAT_STATUSES:
        raise ApiError(400, "status must be one of: " + ", ".join(SEAT_STATUSES))

    if holder:
        if holder != user["id"]:
            raise ApiError(403, "That seat belongs to another member")
        assigned_user_id = None if status == "on_bench" else holder
    else:
        if status != "confirmed":
            raise ApiError(400, "A benched seat can only be claimed (status=confirmed)")
        assigned_user_id = user["id"]

    if status == "resale_listed":
        resale_price_cents = require_int(body, "resale_price_cents", minimum=1)
    else:
        resale_price_cents = None

    changed = await _write_seat_if_unchanged(
        env, seat, status, assigned_user_id, body.get("guest_name"), resale_price_cents
    )
    if changed == 0:
        raise ApiError(
            409, "This seat changed since you last looked at it -- refresh and retry"
        )
    updated = await query_one(
        env, "SELECT * FROM seat_allocations WHERE id = ?", seat["id"]
    )
    return json_response({"seat": updated})


async def _write_seat_if_unchanged(
    env, seat, status, assigned_user_id, guest_name, resale_price_cents
):
    """Write a seat's new state, but only if it still looks like ``seat``.

    Returns the number of rows changed. 0 means someone else changed this seat
    between the caller's read and this write -- two callers racing to claim
    the same seat can't both succeed, since the loser's WHERE clause matches
    nothing rather than silently overwriting the winner's write.
    """
    return await execute(
        env,
        """
        UPDATE seat_allocations
        SET status = ?,
            assigned_user_id = ?,
            guest_name = ?,
            resale_price_cents = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = ? AND assigned_user_id IS ?
        """,
        status,
        assigned_user_id,
        guest_name,
        resale_price_cents,
        seat["id"],
        seat["status"],
        seat["assigned_user_id"],
    )


async def list_listings(request, env, params):
    """Seats going spare across the syndicate: benched or listed for resale."""
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])

    listings = await query(
        env,
        """
        SELECT s.*, f.opponent, f.kickoff_at, f.venue, f.tier
        FROM seat_allocations s
        JOIN fixtures f ON f.id = s.fixture_id
        WHERE f.group_id = ?
          AND s.status IN ('on_bench', 'resale_listed')
          AND datetime(f.kickoff_at) >= datetime('now')
        ORDER BY f.kickoff_at, s.seat_number
        """,
        group_id,
    )
    return json_response({"listings": listings})


async def _fixture_for_member(env, fixture_id, user_id):
    fixture = await query_one(env, "SELECT * FROM fixtures WHERE id = ?", fixture_id)
    if fixture is None:
        raise ApiError(404, "No such fixture")
    await require_membership(env, fixture["group_id"], user_id)
    return fixture


# --- ledger ----------------------------------------------------------------


async def get_ledger(request, env, params):
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])

    transactions = await query(
        env,
        """
        SELECT * FROM transactions
        WHERE group_id = ? AND settled = FALSE
        ORDER BY created_at DESC
        """,
        group_id,
    )
    balances = net_balances(transactions)
    return json_response(
        {
            "transactions": transactions,
            "balances": balances,
            "settle_plan": [
                {"from": payer, "to": recipient, "amount_cents": amount}
                for payer, recipient, amount in settle_plan(balances)
            ],
        }
    )


async def create_expense(request, env, params):
    """Record an expense one member paid and split it across the syndicate."""
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])

    body = await read_json(request)
    (description,) = require(body, "description")
    amount_cents = require_int(body, "amount_cents", minimum=1)

    paid_by = body.get("paid_by") or user["id"]
    members = await _members(env, group_id)
    member_ids = [member["id"] for member in members]

    split_between = body.get("split_between")
    if split_between is None:
        split_between = member_ids
    elif not isinstance(split_between, list) or not split_between:
        raise ApiError(400, "split_between must be a non-empty list of member ids")
    elif len(set(split_between)) != len(split_between):
        raise ApiError(400, "split_between must not repeat a member id")

    unknown = [member for member in split_between if member not in member_ids]
    if unknown:
        raise ApiError(400, "Not members of this syndicate: " + ", ".join(unknown))
    if paid_by not in member_ids:
        raise ApiError(400, "paid_by is not a member of this syndicate")

    split_id = new_id("split")
    writes = []
    for member_id, share in split_equally(amount_cents, sorted(split_between)):
        # The payer's own share is not a debt to themselves.
        if member_id == paid_by or share == 0:
            continue
        writes.append(
            (
                """
                INSERT INTO transactions
                    (id, group_id, payer_id, recipient_id, amount_cents,
                     description, kind, split_id)
                VALUES (?, ?, ?, ?, ?, ?, 'expense_share', ?)
                """,
                (
                    new_id("txn"),
                    group_id,
                    member_id,
                    paid_by,
                    share,
                    description,
                    split_id,
                ),
            )
        )

    await batch(env, writes)
    created = await query(
        env, "SELECT * FROM transactions WHERE split_id = ?", split_id
    )
    return json_response({"split_id": split_id, "transactions": created}, status=201)


async def settle_up(request, env, params):
    """Mark the debts between the caller and one other member as settled."""
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])

    body = await read_json(request)
    (other_member,) = require(body, "with_member_id")
    await require_membership(env, group_id, other_member)

    changed = await execute(
        env,
        """
        UPDATE transactions
        SET settled = TRUE
        WHERE group_id = ?
          AND settled = FALSE
          AND ((payer_id = ? AND recipient_id = ?) OR (payer_id = ? AND recipient_id = ?))
        """,
        group_id,
        user["id"],
        other_member,
        other_member,
        user["id"],
    )
    return json_response({"settled_transactions": changed})


# --- daily player bios -----------------------------------------------------


async def bio_of_the_day(request, env, params):
    # image_path is a root-relative path to an asset committed under
    # frontend/public/assets/images/ and served by Pages, not a signed URL.
    await current_user(request, env)
    bio = await query_one(
        env,
        """
        SELECT * FROM player_bios
        WHERE scheduled_date <= DATE('now')
        ORDER BY scheduled_date DESC
        LIMIT 1
        """,
    )
    if bio is None:
        raise ApiError(404, "No player bio is scheduled yet")
    return json_response({"bio": bio})


# --- roster and opponents ---------------------------------------------------


async def list_roster(request, env, params):
    """The home squad, for the Home Team screen. Club-wide, not per-syndicate."""
    await current_user(request, env)
    players = await query(
        env,
        "SELECT * FROM roster_players WHERE active ORDER BY sort_order, jersey_number",
    )
    caps = await query(
        env,
        """
        SELECT * FROM national_team_appearances
        ORDER BY player_id, year_start
        """,
    )
    caps_by_player = {}
    for cap in caps:
        caps_by_player.setdefault(cap["player_id"], []).append(cap)

    for player in players:
        player["stats"] = json.loads(player.pop("stats_json"))
        history = caps_by_player.get(player["id"], [])
        player["national_team_history"] = history
        current = next((cap for cap in history if cap["year_end"] is None), None)
        player["current_national_team"] = current["country"] if current else None
    return json_response({"players": players})


async def list_opponents(request, env, params):
    """Visiting-club dossiers, for the Visitors screen."""
    await current_user(request, env)
    opponents = await query(
        env, "SELECT * FROM opponents ORDER BY sort_order"
    )
    players = await query(
        env,
        "SELECT * FROM opponent_players WHERE active ORDER BY sort_order, jersey_number",
    )
    by_opponent = {}
    for player in players:
        by_opponent.setdefault(player["opponent_id"], []).append(player)

    for opponent in opponents:
        opponent["quick_stats"] = json.loads(opponent.pop("quick_stats_json"))
        players_for_opponent = by_opponent.get(opponent["id"], [])
        for player in players_for_opponent:
            # SQLite/D1 hands BOOLEAN columns back as 0/1, not JSON booleans.
            player["is_danger"] = bool(player["is_danger"])
        opponent["players"] = players_for_opponent
    return json_response({"opponents": opponents})


# --- preferences -----------------------------------------------------------


async def get_preferences(request, env, params):
    user = await current_user(request, env)
    prefs = await query_one(
        env, "SELECT * FROM user_notification_prefs WHERE user_id = ?", user["id"]
    )
    return json_response({"preferences": prefs})


async def update_preferences(request, env, params):
    user = await current_user(request, env)
    body = await read_json(request)

    notify_3day_checkin = body.get("notify_3day_checkin", True)
    notify_bench_alerts = body.get("notify_bench_alerts", True)
    daily_bio_scope = body.get("daily_bio_scope", "home_first")

    if not isinstance(notify_3day_checkin, bool):
        raise ApiError(400, "notify_3day_checkin must be a boolean")
    if not isinstance(notify_bench_alerts, bool):
        raise ApiError(400, "notify_bench_alerts must be a boolean")
    if daily_bio_scope not in BIO_SCOPES:
        raise ApiError(400, "daily_bio_scope must be one of: " + ", ".join(BIO_SCOPES))

    await execute(
        env,
        """
        INSERT INTO user_notification_prefs
            (user_id, notify_3day_checkin, notify_bench_alerts, daily_bio_scope)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            notify_3day_checkin = excluded.notify_3day_checkin,
            notify_bench_alerts = excluded.notify_bench_alerts,
            daily_bio_scope = excluded.daily_bio_scope
        """,
        user["id"],
        notify_3day_checkin,
        notify_bench_alerts,
        daily_bio_scope,
    )
    prefs = await query_one(
        env, "SELECT * FROM user_notification_prefs WHERE user_id = ?", user["id"]
    )
    return json_response({"preferences": prefs})


# --- admin -------------------------------------------------------------


async def trigger_sync(request, env, params):
    """Run the roster/fixture/opponent/headshot sync against nwslsoccer.com
    and Wikipedia right now, rather than waiting on a schedule.

    There is deliberately no Cloudflare-side cron calling this: it is
    invoked by .github/workflows/sync-roster.yml, both on every push to
    main (after the deploy) and on its own weekly schedule, so a run's logs
    and history live in GitHub Actions with everything else in this repo
    rather than in the Worker's own (harder to reach) cron log.

    Authenticated by a shared-secret bearer token (the SYNC_ADMIN_TOKEN
    Worker secret; see `wrangler secret put SYNC_ADMIN_TOKEN`) rather than
    current_user()/require_membership() -- the caller is a CI job, not a
    signed-in syndicate member.
    """
    expected = getattr(env, "SYNC_ADMIN_TOKEN", None)
    if not expected:
        raise ApiError(503, "SYNC_ADMIN_TOKEN is not configured")

    header = request.headers.get("Authorization") or ""
    token = header[len("Bearer ") :].strip() if header.startswith("Bearer ") else ""
    # Constant-time compare: a naive == would let a timing attack narrow the
    # token down a character at a time.
    if not token or not hmac.compare_digest(token, expected):
        raise ApiError(401, "Invalid or missing sync admin token")

    summary = await run_sync(env)
    return json_response({"summary": summary})
