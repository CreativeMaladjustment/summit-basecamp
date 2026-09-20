"""Cloudflare Worker entry point for Summit Hearth & Bench.

`on_fetch` serves the JSON API; `on_scheduled` runs the two daily crons
declared in wrangler.jsonc.
"""

from js import URL

import handlers
from db import execute, query
from responses import ApiError, error_response, json_response
from router import Router

router = Router()

router.add("GET", "/api/health", handlers.health)
router.add("POST", "/api/auth/session", handlers.begin_session)
router.add("GET", "/api/me", handlers.get_me)

router.add("GET", "/api/groups", handlers.list_groups)
router.add("POST", "/api/groups", handlers.create_group)
router.add("GET", "/api/groups/{group_id}", handlers.get_group)
router.add("GET", "/api/groups/{group_id}/members", handlers.list_members)

router.add("GET", "/api/groups/{group_id}/fixtures", handlers.list_fixtures)
router.add("POST", "/api/groups/{group_id}/fixtures", handlers.create_fixture)
router.add("GET", "/api/fixtures/{fixture_id}/seats", handlers.list_seats)
router.add("PATCH", "/api/seats/{allocation_id}", handlers.update_seat)
router.add("GET", "/api/groups/{group_id}/listings", handlers.list_listings)

router.add("GET", "/api/groups/{group_id}/ledger", handlers.get_ledger)
router.add("POST", "/api/groups/{group_id}/expenses", handlers.create_expense)
router.add("POST", "/api/groups/{group_id}/settle", handlers.settle_up)

router.add("GET", "/api/bios/today", handlers.bio_of_the_day)
router.add("GET", "/api/preferences", handlers.get_preferences)
router.add("PUT", "/api/preferences", handlers.update_preferences)


# The PWA is served from Pages on its own origin, so the API answers
# cross-origin requests from the browser.
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Dev-User",
    "Access-Control-Max-Age": "86400",
}


async def on_fetch(request, env):
    if request.method == "OPTIONS":
        return json_response({}, status=204, headers=CORS_HEADERS)

    path = URL.new(request.url).pathname
    handler, params = router.match(request.method, path)

    if handler is None:
        if params:
            return _with_cors(
                error_response(405, "Method not allowed on " + path)
            )
        return _with_cors(error_response(404, "No route for " + path))

    try:
        response = await handler(request, env, params)
    except ApiError as error:
        response = error_response(error.status, error.message)
    except Exception as error:  # noqa: BLE001 - never leak a stack trace
        print("Unhandled error on {} {}: {!r}".format(request.method, path, error))
        response = error_response(500, "Something went wrong")

    return _with_cors(response)


def _with_cors(response):
    for name, value in CORS_HEADERS.items():
        response.headers.set(name, value)
    return response


async def on_scheduled(event, env, ctx):
    """Cron entry point. The two schedules do different jobs."""
    cron = event.cron
    if cron == "0 8 * * *":
        await _rotate_daily_bio(env)
    elif cron == "0 10 * * *":
        await _send_checkin_reminders(env)
    else:
        print("No job registered for cron " + str(cron))


async def _rotate_daily_bio(env):
    """Schedule the next unscheduled player bio for today."""
    changed = await execute(
        env,
        """
        UPDATE player_bios
        SET scheduled_date = DATE('now')
        WHERE id = (
            SELECT id FROM player_bios
            WHERE scheduled_date IS NULL
            ORDER BY player_name
            LIMIT 1
        )
        """,
    )
    print("Daily bio rotation scheduled {} bio(s)".format(changed))


async def _send_checkin_reminders(env):
    """Find members who have not answered for a fixture three days out.

    Delivering the push notification itself is not wired up yet; this logs the
    seats still sitting on the bench so the job is observable in the meantime.
    """
    pending = await query(
        env,
        """
        SELECT f.id AS fixture_id, f.opponent, f.kickoff_at, COUNT(s.id) AS benched
        FROM fixtures f
        JOIN seat_allocations s ON s.fixture_id = f.id
        WHERE s.status = 'on_bench'
          AND DATE(f.kickoff_at) = DATE('now', '+3 days')
        GROUP BY f.id, f.opponent, f.kickoff_at
        """,
    )
    for row in pending:
        print(
            "Check-in reminder due: {} seat(s) on the bench for {}".format(
                row["benched"], row["opponent"]
            )
        )
