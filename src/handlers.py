"""Endpoint handlers.

Every handler takes ``(request, env, params)`` and returns a Response.
``params`` holds the path parameters the router pulled out of the URL.
"""

from auth import current_user, require_admin, require_membership
from db import batch, execute, new_id, query, query_one
from responses import ApiError, json_response, read_json, require
from splits import net_balances, settle_plan, split_equally

SEAT_STATUSES = ("confirmed", "on_bench", "gifted", "resale_listed")
FIXTURE_TIERS = ("rivalry", "standard", "cup")


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
    name, season_year, total_seats, package_cost_cents = require(
        body, "name", "season_year", "total_seats", "package_cost_cents"
    )

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
                    int(season_year),
                    int(total_seats),
                    int(package_cost_cents),
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
    opponent, kickoff_at, venue, weighted_value_cents = require(
        body, "opponent", "kickoff_at", "venue", "weighted_value_cents"
    )
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
                int(weighted_value_cents),
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
    """Claim a seat, put it on the bench, gift it, or list it for resale."""
    user = await current_user(request, env)
    body = await read_json(request)

    seat = await query_one(
        env, "SELECT * FROM seat_allocations WHERE id = ?", params["allocation_id"]
    )
    if seat is None:
        raise ApiError(404, "No such seat")
    await _fixture_for_member(env, seat["fixture_id"], user["id"])

    status = body.get("status", seat["status"])
    if status not in SEAT_STATUSES:
        raise ApiError(400, "status must be one of: " + ", ".join(SEAT_STATUSES))

    # Only the seat's holder may give it up; anyone in the syndicate may take a
    # seat that is sitting on the bench.
    holder = seat["assigned_user_id"]
    if holder and holder != user["id"] and seat["status"] != "on_bench":
        raise ApiError(403, "That seat belongs to another member")

    if status == "on_bench":
        assigned_user_id = None
    elif status == "confirmed":
        assigned_user_id = body.get("assigned_user_id") or user["id"]
    else:
        assigned_user_id = holder or user["id"]

    resale_price_cents = body.get("resale_price_cents")
    if status == "resale_listed" and not resale_price_cents:
        raise ApiError(400, "A resale listing needs a resale_price_cents")
    if status != "resale_listed":
        resale_price_cents = None

    await execute(
        env,
        """
        UPDATE seat_allocations
        SET status = ?,
            assigned_user_id = ?,
            guest_name = ?,
            resale_price_cents = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        status,
        assigned_user_id,
        body.get("guest_name"),
        int(resale_price_cents) if resale_price_cents else None,
        seat["id"],
    )
    updated = await query_one(
        env, "SELECT * FROM seat_allocations WHERE id = ?", seat["id"]
    )
    return json_response({"seat": updated})


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
          AND f.kickoff_at >= CURRENT_TIMESTAMP
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
    amount_cents, description = require(body, "amount_cents", "description")
    amount_cents = int(amount_cents)
    if amount_cents <= 0:
        raise ApiError(400, "amount_cents must be greater than zero")

    paid_by = body.get("paid_by") or user["id"]
    members = await _members(env, group_id)
    member_ids = [member["id"] for member in members]

    split_between = body.get("split_between") or member_ids
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
        bool(body.get("notify_3day_checkin", True)),
        bool(body.get("notify_bench_alerts", True)),
        body.get("daily_bio_scope", "home_first"),
    )
    prefs = await query_one(
        env, "SELECT * FROM user_notification_prefs WHERE user_id = ?", user["id"]
    )
    return json_response({"preferences": prefs})
