"""Endpoint handlers.

Every handler takes ``(request, env, params)`` and returns a Response.
``params`` holds the path parameters the router pulled out of the URL.
"""

import base64
import binascii
import hmac
import json

from auth import (
    current_user,
    require_admin,
    require_membership,
    start_device_trust,
    start_session,
    verify_device_token,
    verify_site_password,
)
from db import batch, execute, new_id, new_invite_code, query, query_one
from responses import ApiError, binary_response, json_response, read_json, require, require_int
from splits import net_balances, settle_plan, split_equally
from storage import get_object, put_object
from sync import run_sync

SEAT_STATUSES = ("confirmed", "on_bench", "gifted", "resale_listed")
FIXTURE_TIERS = ("rivalry", "standard", "cup")
BIO_SCOPES = ("home_first", "summit_only", "league_wide")
MEMBER_ROLES = ("admin", "member")
AVATAR_CONTENT_TYPES = ("image/png", "image/jpeg", "image/webp")
# A profile picture, not a photo album -- large enough for any real headshot,
# small enough that base64's ~33% overhead over the wire is a non-issue.
MAX_AVATAR_BYTES = 2 * 1024 * 1024
# The longest a base64 string encoding MAX_AVATAR_BYTES can legally be
# (base64 always expands in groups of 4 output chars per 3 input bytes) --
# checked against the *encoded* string before decoding it, so an oversized
# upload is rejected without decoding it first just to measure it.
MAX_AVATAR_BASE64_CHARS = ((MAX_AVATAR_BYTES + 2) // 3) * 4


# --- health and identity ---------------------------------------------------


async def health(request, env, params):
    # Touches D1 so the check fails loudly when migrations have not been run.
    await query_one(env, "SELECT 1 AS ok")
    return json_response({"status": "ok", "environment": env.ENVIRONMENT})


async def list_guest_slots(request, env, params):
    """The six shared-password login slots on the landing screen, in id
    order. Public and unauthenticated -- nobody is signed in yet at this
    point in the flow. Each slot's name starts as "Guest N" (migration 0010)
    and is whatever PATCH /api/me most recently set it to once someone
    claims that slot as their own."""
    guests = await query(
        env, "SELECT id, name FROM users WHERE auth_provider = 'password' ORDER BY id"
    )
    return json_response({"guests": guests})


async def begin_session(request, env, params):
    """Sign in to one of the six shared guest slots with the site password,
    or with a device_token a previous call already returned in its place.

    This is an access gate, not per-person auth: every slot accepts the same
    SITE_PWD Worker secret, and the caller just picks which slot they are.
    Only one of password/device_token is required. Proving the caller's
    device already passed the site password once (device_token) returns
    that same still-valid token back; proving it fresh (password) mints a
    new one -- either way the device stores whatever token comes back
    instead of the raw password itself, so a successful sign-in never
    leaves the literal shared secret sitting in the browser's own storage
    (see src/auth.start_device_trust).
    """
    body = await read_json(request)
    (user_id,) = require(body, "user_id")
    device_token = body.get("device_token")
    if device_token:
        await verify_device_token(env, device_token)
        new_device_token = device_token
    else:
        (password,) = require(body, "password")
        verify_site_password(env, password)
        new_device_token = await start_device_trust(env)

    user = await query_one(
        env, "SELECT * FROM users WHERE id = ? AND auth_provider = 'password'", user_id
    )
    if user is None:
        raise ApiError(400, "Not a valid login")

    token = await start_session(env, user["id"])
    return json_response({"token": token, "user": user, "device_token": new_device_token})


async def get_me(request, env, params):
    user = await current_user(request, env)
    prefs = await query_one(
        env, "SELECT * FROM user_notification_prefs WHERE user_id = ?", user["id"]
    )
    return json_response({"user": user, "preferences": prefs})


async def update_me(request, env, params):
    """Edit the caller's own display name, phone or fallback contact email
    -- the Settings screen's "Group & profile" card. Also how a guest slot
    replaces its "Guest N" placeholder (see migration 0010) with the name
    someone actually goes by, the first time they set one.

    `phone`/`contact_email` are deliberately separate columns from the
    sign-in `email` (see migration 0009): a member may want a different
    number or address reachable for critical ticket transfers than the one
    their account uses. `name` doubles as what every other member sees in
    a member list, so unlike phone/contact_email it can be edited but never
    cleared to empty.
    """
    user = await current_user(request, env)
    body = await read_json(request)

    editable_fields = ("name", "phone", "contact_email")
    if not any(field in body for field in editable_fields):
        raise ApiError(400, "Nothing to update")

    updates = {}
    if "name" in body:
        name = body["name"]
        if not isinstance(name, str) or not name.strip():
            raise ApiError(400, "name must be a non-empty string")
        updates["name"] = name.strip()
    for field in ("phone", "contact_email"):
        if field in body:
            value = body[field]
            if value is not None and not isinstance(value, str):
                raise ApiError(400, f"{field} must be a string or null")
            # A blank or whitespace-only string clears the field, same as
            # sending null explicitly, rather than storing empty text.
            updates[field] = value.strip() if value and value.strip() else None

    set_clause = ", ".join(f"{field} = ?" for field in updates)
    await execute(
        env,
        f"UPDATE users SET {set_clause} WHERE id = ?",
        *updates.values(),
        user["id"],
    )
    updated = await query_one(env, "SELECT * FROM users WHERE id = ?", user["id"])
    return json_response({"user": updated})


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


def _optional_text(body, field):
    """Pull an optional freeform string out of a parsed body: absent or ''
    becomes None (nothing set / cleared), otherwise the trimmed string.
    Same shape as update_me's phone/contact_email handling."""
    value = body.get(field)
    if value is not None and not isinstance(value, str):
        raise ApiError(400, f"{field} must be a string or null")
    return value.strip() if value and value.strip() else None


async def create_group(request, env, params):
    """Start a syndicate. ``section``/``seat_row``/``seat_labels`` describe
    the physical seats the whole package holds (e.g. Section 114, Row 8,
    seats "3, 4") -- freeform text, all optional, distinct from
    ``total_seats`` and the internal 1..total_seats seat numbering
    ``create_fixture``/``update_member`` use to track who's assigned where.
    ``my_seat_label`` is which one of those real seats is the creator's own
    (they're always seat #1 internally, as the syndicate's first member)."""
    user = await current_user(request, env)
    body = await read_json(request)
    (name,) = require(body, "name")
    season_year = require_int(body, "season_year", minimum=1900)
    total_seats = require_int(body, "total_seats", minimum=1)
    package_cost_cents = require_int(body, "package_cost_cents", minimum=0)
    section = _optional_text(body, "section")
    seat_row = _optional_text(body, "seat_row")
    seat_labels = _optional_text(body, "seat_labels")
    my_seat_label = _optional_text(body, "my_seat_label")

    group_id = new_id("grp")
    invite_code = new_invite_code()
    await batch(
        env,
        [
            (
                """
                INSERT INTO groups
                    (id, name, season_year, total_seats, package_cost_cents,
                     created_by, invite_code, section, seat_row, seat_labels)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    group_id,
                    name,
                    season_year,
                    total_seats,
                    package_cost_cents,
                    user["id"],
                    invite_code,
                    section,
                    seat_row,
                    seat_labels,
                ),
            ),
            (
                """
                INSERT INTO group_members (group_id, user_id, default_seat_number, role, seat_label)
                VALUES (?, ?, ?, 'admin', ?)
                """,
                (group_id, user["id"], 1, my_seat_label),
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


async def update_group(request, env, params):
    """Admin-only: rename the syndicate, change its total package price, or
    grow/shrink its total seat count.

    Growing total_seats retrofits every existing fixture with one new
    on_bench seat_allocation per new seat number -- the same shape
    create_fixture seeds a brand-new fixture with. Shrinking is only allowed
    once nothing would be lost by it: refused with 409 if any member's
    default_seat_number, or any seat_allocation's seat_number, still points
    above the new total and isn't just sitting on_bench -- reconciling that
    silently (dropping a confirmed/gifted/resale_listed seat, or a member's
    default assignment) would destroy state the admin never asked to lose.

    A resize is never just a read-then-write against a snapshot taken
    moments earlier: the guards above, and an optimistic
    "total_seats hasn't moved since I read it" check that applies either
    way, are embedded directly in the write statements below and run in one
    D1 batch (one atomic transaction) -- the same INSERT/DELETE ... WHERE
    EXISTS pattern sync._create_fixture_from_sync uses to chain a later
    statement's effect off an earlier one in the same batch. Without that,
    a concurrent create_fixture could read the old total and seed a new
    fixture with too few seats after this handler already took its
    snapshot of which fixtures exist, or a seat could become occupied after
    the shrink guards ran and still get deleted. _require_seats_shrinkable
    below still runs first, as a pre-check -- purely so the common,
    non-racing case gets a specific, helpful 409 rather than the generic
    conflict one below; the embedded guards are what actually enforces it.
    """
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_admin(env, group_id, user["id"])

    group = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
    if group is None:
        raise ApiError(404, "No such syndicate")

    body = await read_json(request)
    name = body.get("name", group["name"])
    if not name:
        raise ApiError(400, "name must not be empty")
    package_cost_cents = (
        require_int(body, "package_cost_cents", minimum=0)
        if "package_cost_cents" in body
        else group["package_cost_cents"]
    )
    old_total_seats = int(group["total_seats"])
    total_seats = (
        require_int(body, "total_seats", minimum=1)
        if "total_seats" in body
        else old_total_seats
    )

    if total_seats == old_total_seats:
        await execute(
            env,
            "UPDATE groups SET name = ?, package_cost_cents = ? WHERE id = ?",
            name,
            package_cost_cents,
            group_id,
        )
        updated = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
        return json_response({"group": updated})

    if total_seats < old_total_seats:
        await _require_seats_shrinkable(env, group_id, total_seats)

    group_guard_sql = "id = ? AND total_seats = ?"
    group_guard_params = [group_id, old_total_seats]
    if total_seats < old_total_seats:
        group_guard_sql += """
              AND NOT EXISTS (
                SELECT 1 FROM group_members gm
                WHERE gm.group_id = groups.id AND gm.default_seat_number > ?
              )
              AND NOT EXISTS (
                SELECT 1 FROM seat_allocations s
                JOIN fixtures f ON f.id = s.fixture_id
                WHERE f.group_id = groups.id AND s.seat_number > ? AND s.status != 'on_bench'
              )
        """
        group_guard_params += [total_seats, total_seats]

    writes = [
        (
            "UPDATE groups SET name = ?, package_cost_cents = ?, total_seats = ? WHERE "
            + group_guard_sql,
            tuple([name, package_cost_cents, total_seats, *group_guard_params]),
        )
    ]
    if total_seats > old_total_seats:
        for seat_number in range(old_total_seats + 1, total_seats + 1):
            writes.append(
                (
                    """
                    INSERT INTO seat_allocations (id, fixture_id, seat_number, status)
                    SELECT 'seat_' || lower(hex(randomblob(8))), f.id, ?, 'on_bench'
                    FROM fixtures f
                    WHERE f.group_id = ?
                      AND EXISTS (SELECT 1 FROM groups g WHERE g.id = ? AND g.total_seats = ?)
                      AND NOT EXISTS (
                        SELECT 1 FROM seat_allocations s2
                        WHERE s2.fixture_id = f.id AND s2.seat_number = ?
                      )
                    """,
                    (seat_number, group_id, group_id, total_seats, seat_number),
                )
            )
    else:
        writes.append(
            (
                """
                DELETE FROM seat_allocations
                WHERE seat_number > ?
                  AND fixture_id IN (SELECT id FROM fixtures WHERE group_id = ?)
                  AND EXISTS (SELECT 1 FROM groups g WHERE g.id = ? AND g.total_seats = ?)
                """,
                (total_seats, group_id, group_id, total_seats),
            )
        )

    results = await batch(env, writes)
    if _rows_changed(results[0] if results else None) == 0:
        raise ApiError(
            409, "This syndicate changed since you last looked at it -- refresh and retry"
        )
    updated = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
    return json_response({"group": updated})


def _rows_changed(batch_result):
    """How many rows one statement in a batch() result actually changed --
    same shape sync._create_fixture_from_sync reads to tell whether its own
    guarded statement in the same batch took effect."""
    meta = getattr(batch_result, "meta", None) if batch_result is not None else None
    return (getattr(meta, "changes", 0) or 0) if meta is not None else 0


async def _require_seats_shrinkable(env, group_id, new_total_seats):
    """A fast, specific pre-check for the common (non-racing) case -- see
    update_group's docstring for why the embedded guards in its own batch,
    not this function, are what actually enforces it."""
    orphaned_default = await query_one(
        env,
        "SELECT 1 FROM group_members WHERE group_id = ? AND default_seat_number > ?",
        group_id,
        new_total_seats,
    )
    if orphaned_default:
        raise ApiError(
            409,
            "A member's default seat is above the new total_seats -- reassign it first",
        )
    still_occupied = await query_one(
        env,
        """
        SELECT 1 FROM seat_allocations s
        JOIN fixtures f ON f.id = s.fixture_id
        WHERE f.group_id = ? AND s.seat_number > ? AND s.status != 'on_bench'
        """,
        group_id,
        new_total_seats,
    )
    if still_occupied:
        raise ApiError(
            409,
            "A seat above the new total_seats is still confirmed, gifted or listed -- free it first",
        )


async def join_group(request, env, params):
    """Join an existing syndicate by its invite code.

    Membership starts as a plain 'member' with no default_seat_number, same
    as anyone else added to a syndicate -- they pick a seat afterward via
    PATCH /api/groups/{id}/members/{user_id}, the same self-service path an
    existing member already uses.
    """
    user = await current_user(request, env)
    body = await read_json(request)
    (raw_code,) = require(body, "invite_code")
    if not isinstance(raw_code, str):
        raise ApiError(400, "invite_code must be a string")

    group = await query_one(
        env, "SELECT * FROM groups WHERE invite_code = ?", raw_code.strip().upper()
    )
    if group is None:
        raise ApiError(404, "Invalid invite code")

    # INSERT ... SELECT ... WHERE NOT EXISTS, not a membership check
    # followed by a separate INSERT: two simultaneous redemptions by the
    # same user could otherwise both pass the check, and the loser would
    # hit group_members' primary key and surface as an uncaught 500 instead
    # of the documented 409 -- same atomic-guard pattern as the seat/role
    # collision guards in update_member.
    changed = await execute(
        env,
        """
        INSERT INTO group_members (group_id, user_id, role)
        SELECT ?, ?, 'member'
        WHERE NOT EXISTS (
            SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?
        )
        """,
        group["id"],
        user["id"],
        group["id"],
        user["id"],
    )
    if changed == 0:
        raise ApiError(409, "You are already a member of this syndicate")

    return json_response(
        {"group": group, "members": await _members(env, group["id"])}, status=201
    )


async def rotate_invite_code(request, env, params):
    """Admin-only: replace a syndicate's invite code with a fresh one, so a
    leaked or no-longer-wanted code stops working without disturbing anyone
    already in the syndicate."""
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_admin(env, group_id, user["id"])

    group = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
    if group is None:
        raise ApiError(404, "No such syndicate")

    await execute(
        env, "UPDATE groups SET invite_code = ? WHERE id = ?", new_invite_code(), group_id
    )
    updated = await query_one(env, "SELECT * FROM groups WHERE id = ?", group_id)
    return json_response({"group": updated})


async def list_members(request, env, params):
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_membership(env, group_id, user["id"])
    return json_response({"members": await _members(env, group_id)})


async def update_member(request, env, params):
    """Change a member's default seat assignment -- their profile's "Seat
    assignment" card -- their own real seat_label (which of the syndicate's
    physical seats is theirs), or, admin only, their role.

    A member may only edit their own default_seat_number/seat_label. Only
    an admin can edit another member's, or change anyone's role; this is
    what lets an admin move seats around the syndicate rather than each
    member being stuck with whatever they picked first.
    """
    user = await current_user(request, env)
    group_id = params["group_id"]
    target_id = params["user_id"]
    membership = await require_membership(env, group_id, user["id"])
    is_admin = membership.get("role") == "admin"

    if target_id != user["id"] and not is_admin:
        raise ApiError(403, "Only a syndicate admin can edit another member")
    target_membership = await require_membership(env, group_id, target_id)

    body = await read_json(request)
    if "default_seat_number" not in body and "role" not in body and "seat_label" not in body:
        raise ApiError(400, "Nothing to update")

    if "seat_label" in body:
        await execute(
            env,
            "UPDATE group_members SET seat_label = ? WHERE group_id = ? AND user_id = ?",
            _optional_text(body, "seat_label"),
            group_id,
            target_id,
        )

    if "default_seat_number" in body:
        raw_seat_number = body["default_seat_number"]
        if raw_seat_number is None:
            await execute(
                env,
                "UPDATE group_members SET default_seat_number = NULL WHERE group_id = ? AND user_id = ?",
                group_id,
                target_id,
            )
        else:
            seat_number = require_int(body, "default_seat_number", minimum=1)
            group = await query_one(env, "SELECT total_seats FROM groups WHERE id = ?", group_id)
            if seat_number > int(group["total_seats"]):
                raise ApiError(400, "default_seat_number exceeds this syndicate's total_seats")
            # The collision guard has to live in the same statement as the
            # write, not a SELECT beforehand -- two concurrent edits could
            # otherwise both read "nobody has this seat" and both write,
            # since nothing stops a second write between the first's check
            # and its own write. NOT EXISTS re-evaluates as part of this
            # one atomic UPDATE, so whichever request's write actually lands
            # first is the only one that can win the seat.
            changed = await execute(
                env,
                """
                UPDATE group_members
                SET default_seat_number = ?
                WHERE group_id = ? AND user_id = ?
                  AND NOT EXISTS (
                    SELECT 1 FROM group_members AS other
                    WHERE other.group_id = ?
                      AND other.default_seat_number = ?
                      AND other.user_id != ?
                  )
                """,
                seat_number,
                group_id,
                target_id,
                group_id,
                seat_number,
                target_id,
            )
            if changed == 0:
                raise ApiError(409, "That seat is already someone else's default")

    if "role" in body:
        if not is_admin:
            raise ApiError(403, "Only a syndicate admin can change a member's role")
        role = body["role"]
        if role not in MEMBER_ROLES:
            raise ApiError(400, "role must be one of: " + ", ".join(MEMBER_ROLES))
        if role == "admin" or target_membership.get("role") != "admin":
            await execute(
                env,
                "UPDATE group_members SET role = ? WHERE group_id = ? AND user_id = ?",
                role,
                group_id,
                target_id,
            )
        else:
            # Demoting the syndicate's only admin would leave nobody who
            # can pass require_admin -- every admin-only endpoint,
            # including this one's own role field, becomes permanently
            # unreachable. Guarded the same atomic way as the seat
            # collision above: the EXISTS check runs as part of the same
            # UPDATE that would perform the demotion, not a separate SELECT
            # a concurrent demotion of the *other* admin could race past.
            changed = await execute(
                env,
                """
                UPDATE group_members
                SET role = ?
                WHERE group_id = ? AND user_id = ?
                  AND EXISTS (
                    SELECT 1 FROM group_members AS other
                    WHERE other.group_id = ? AND other.role = 'admin' AND other.user_id != ?
                  )
                """,
                role,
                group_id,
                target_id,
                group_id,
                target_id,
            )
            if changed == 0:
                raise ApiError(409, "Cannot demote the only remaining admin")

    updated = await query_one(
        env,
        """
        SELECT u.id, u.name, u.email, u.avatar_url, m.role, m.default_seat_number, m.seat_label
        FROM group_members m
        JOIN users u ON u.id = m.user_id
        WHERE m.group_id = ? AND m.user_id = ?
        """,
        group_id,
        target_id,
    )
    return json_response({"member": updated})


async def _members(env, group_id):
    return await query(
        env,
        """
        SELECT u.id, u.name, u.email, u.avatar_url, m.role, m.default_seat_number, m.seat_label
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
    """Admin-only: add a fixture, seeding one seat_allocation per seat.

    The seat count and default-seat assignments used to seed them are read
    live, inside the same batch/transaction as the fixture insert itself
    (the WITH RECURSIVE below, bounded by a correlated subquery against
    groups.total_seats, plus the LEFT JOIN against group_members), not from
    a Python-side read taken moments earlier: an admin resizing total_seats
    (PATCH /api/groups/{id}) concurrently with this could otherwise commit
    the resize's own "add a seat to every existing fixture" pass before
    this fixture exists to be reconciled by it, and this handler's own
    then-stale seat count would permanently under-seed it.
    """
    user = await current_user(request, env)
    group_id = params["group_id"]
    await require_admin(env, group_id, user["id"])

    body = await read_json(request)
    opponent, kickoff_at, venue = require(body, "opponent", "kickoff_at", "venue")
    weighted_value_cents = require_int(body, "weighted_value_cents", minimum=0)
    tier = body.get("tier", "standard")
    if tier not in FIXTURE_TIERS:
        raise ApiError(400, "tier must be one of: " + ", ".join(FIXTURE_TIERS))

    group = await query_one(env, "SELECT id FROM groups WHERE id = ?", group_id)
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
        ),
        (
            """
            WITH RECURSIVE seat_numbers(n) AS (
                SELECT 1
                UNION ALL
                SELECT n + 1 FROM seat_numbers
                WHERE n < (SELECT total_seats FROM groups WHERE id = ?)
            )
            INSERT INTO seat_allocations (id, fixture_id, seat_number, assigned_user_id, status)
            SELECT 'seat_' || lower(hex(randomblob(8))), ?, seat_numbers.n, gm.user_id,
                   CASE WHEN gm.user_id IS NOT NULL THEN 'confirmed' ELSE 'on_bench' END
            FROM seat_numbers
            LEFT JOIN group_members gm
              ON gm.group_id = ? AND gm.default_seat_number = seat_numbers.n
            """,
            (group_id, fixture_id, group_id),
        ),
    ]

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
    endpoint has no transfer flow for a regular member. A seat with a holder
    can only be changed by that holder.

    A syndicate admin is the exception to both: they can set any seat's
    status and reassign it to any member of the syndicate (or bench it),
    regardless of who currently holds it -- this is the admin override that
    lets them fix a seat nobody involved can, e.g. reassigning a seat whose
    holder left the syndicate.
    """
    user = await current_user(request, env)
    body = await read_json(request)

    seat = await query_one(
        env, "SELECT * FROM seat_allocations WHERE id = ?", params["allocation_id"]
    )
    if seat is None:
        raise ApiError(404, "No such seat")
    fixture = await _fixture_for_member(env, seat["fixture_id"], user["id"])

    holder = seat["assigned_user_id"]
    status = body.get("status", seat["status"])
    if status not in SEAT_STATUSES:
        raise ApiError(400, "status must be one of: " + ", ".join(SEAT_STATUSES))

    membership = await require_membership(env, fixture["group_id"], user["id"])
    if membership.get("role") == "admin":
        if "assigned_user_id" in body:
            assigned_user_id = body["assigned_user_id"]
            if assigned_user_id is not None and status == "on_bench":
                # A benched seat with a holder is a state the rest of this
                # endpoint doesn't expect: the normal claim path (the
                # `elif holder:`/`else:` branches below) treats a holder as
                # authoritative and refuses anyone else, so a seat stuck
                # here could never be claimed even though list_listings
                # shows it as available. Reject the conflicting payload
                # rather than silently picking one field over the other.
                raise ApiError(400, "assigned_user_id must be null when status is on_bench")
            if assigned_user_id is not None:
                target = await query_one(
                    env,
                    "SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?",
                    fixture["group_id"],
                    assigned_user_id,
                )
                if target is None:
                    raise ApiError(400, "assigned_user_id is not a member of this syndicate")
        elif status == "on_bench":
            assigned_user_id = None
        else:
            assigned_user_id = holder if holder is not None else user["id"]
    elif holder:
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


# --- profile picture --------------------------------------------------------


async def upload_avatar(request, env, params):
    """Store the caller's own profile picture, for their Profile card.

    The body is JSON ({"content_type", "image_base64"}), not a raw/multipart
    upload -- Workers Python's request-body handling is simplest through the
    same read_json() every other handler already uses, and a profile
    picture is small enough that base64's overhead does not matter.

    Written to KV under a single fixed key per user (no extension) with the
    content type stored as the value's own KV metadata, rather than one
    key per content type -- so re-uploading in a different format replaces
    the old picture outright instead of leaving an orphaned copy behind
    under its old key. KV rather than R2 or D1: R2 needs its own one-time
    account-level enablement in the Cloudflare dashboard before any API
    token can touch it, where KV is already active on this account
    (SESSIONS already uses it) -- see wrangler.jsonc's comment on the
    AVATARS binding. There is still no general object storage in this app
    (see docs/backend.md); this is its own binding rather than folding it
    into whatever eventually fills the player-headshot gap.
    """
    user = await current_user(request, env)
    body = await read_json(request)
    (content_type,) = require(body, "content_type")
    (image_base64,) = require(body, "image_base64")

    if content_type not in AVATAR_CONTENT_TYPES:
        raise ApiError(
            400, "content_type must be one of: " + ", ".join(AVATAR_CONTENT_TYPES)
        )

    # Checked before decoding, not after: b64decode() can raise TypeError
    # for a non-string JSON value (a number, a list) rather than the
    # binascii/ValueError a malformed string raises, which would otherwise
    # escape as an uncaught 500. And bounding the *encoded* length up front
    # rejects an oversized upload without first paying the CPU/memory cost
    # of decoding all of it just to reject it on the decoded-byte check
    # below.
    if not isinstance(image_base64, str):
        raise ApiError(400, "image_base64 must be a string")
    if len(image_base64) > MAX_AVATAR_BASE64_CHARS:
        raise ApiError(400, "Profile pictures are limited to 2 MiB")

    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise ApiError(400, "image_base64 is not valid base64")
    if not image_bytes:
        raise ApiError(400, "image_base64 must not be empty")
    if len(image_bytes) > MAX_AVATAR_BYTES:
        raise ApiError(400, "Profile pictures are limited to 2 MiB")

    await put_object(env, _avatar_key(user["id"]), image_bytes, content_type)

    avatar_url = "/api/avatars/{}".format(user["id"])
    await execute(env, "UPDATE users SET avatar_url = ? WHERE id = ?", avatar_url, user["id"])
    updated = await query_one(env, "SELECT * FROM users WHERE id = ?", user["id"])
    return json_response({"user": updated})


async def get_avatar(request, env, params):
    """Stream a member's uploaded profile picture back out of KV.

    Unauthenticated: an avatar is not sensitive, and every other member who
    can already see this user's name in a member list needs to be able to
    show their picture too, which an auth-gated image would make awkward
    (threading a bearer token through an <img src>). No avatar uploaded yet
    (or a bad user id) is a 404, same as any other missing resource.
    """
    found = await get_object(env, _avatar_key(params["user_id"]))
    if found is None:
        raise ApiError(404, "No avatar uploaded for this user")
    return binary_response(found["bytes"], found["content_type"] or "application/octet-stream")


def _avatar_key(user_id):
    return "avatars/" + user_id


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
