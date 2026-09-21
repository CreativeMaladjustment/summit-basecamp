# Backend

The API is a single Cloudflare Python Worker (`summit-hearth-api`) over D1 for
data and KV for sessions. The PWA is deployed separately on Cloudflare Pages
and talks to this Worker cross-origin.

There is no object storage. Player headshots and club crests are committed to
`frontend/public/assets/images/` and served by Pages; `player_bios.image_path`
holds the root-relative path to each one, falling back to
`/assets/images/players/placeholder-avatar.webp`.

## Layout

| Path | What it holds |
| --- | --- |
| `wrangler.jsonc` | Worker config: D1, KV, cron triggers |
| `migrations/0001_initial.sql` | The D1 schema |
| `migrations/0002_roster.sql` | Home-team squad and opponent dossiers |
| `seed/dev_seed.sql` | Four members, two fixtures, a part-paid ledger, the squad and opponent dossiers |
| `src/entry.py` | `on_fetch` route table, `on_scheduled` cron jobs |
| `src/router.py` | Path matching (`/api/groups/{group_id}/fixtures`) |
| `src/handlers.py` | One function per endpoint |
| `src/db.py` | D1 helpers that hand back plain dicts |
| `src/auth.py` | Bearer token to user, membership and admin checks |
| `src/splits.py` | Expense-split and settle-up arithmetic |
| `src/responses.py` | JSON responses and `ApiError` |

## Running it

```sh
npm install
npm run migrate:local      # apply migrations to the local D1 database
npm run seed:local         # load the development data
npm run dev                # wrangler dev on http://localhost:8787
npm test                   # the Python unit and API tests
```

With `ENVIRONMENT=development` the OIDC round trip is skipped: name the caller
in an `X-Dev-User` header instead of a bearer token.

```sh
curl -H 'X-Dev-User: usr_ada' http://localhost:8787/api/groups
```

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/health` | Liveness, including a D1 round trip |
| POST | `/api/auth/session` | Exchange an OIDC token for a session (not implemented) |
| GET | `/api/me` | The signed-in member and their notification preferences |
| GET | `/api/groups` | Syndicates the caller belongs to |
| POST | `/api/groups` | Start a syndicate; the creator becomes its admin |
| GET | `/api/groups/{id}` | One syndicate and its members |
| GET | `/api/groups/{id}/members` | Members only |
| GET | `/api/groups/{id}/fixtures` | Fixtures in kickoff order |
| POST | `/api/groups/{id}/fixtures` | Add a fixture (admin); seats are created with it |
| GET | `/api/fixtures/{id}/seats` | The seat map for one fixture |
| PATCH | `/api/seats/{id}` | Claim, bench, gift, or list a seat for resale |
| GET | `/api/groups/{id}/listings` | Upcoming seats going spare |
| GET | `/api/groups/{id}/ledger` | Unsettled transactions, net balances, settle plan |
| POST | `/api/groups/{id}/expenses` | Record an expense and split it |
| POST | `/api/groups/{id}/settle` | Mark the debts with one member settled |
| GET | `/api/bios/today` | The player bio scheduled for today |
| GET | `/api/roster` | The home squad, club-wide (not per-syndicate) |
| GET | `/api/opponents` | Visiting-club dossiers, each with its own scouting roster |
| GET/PUT | `/api/preferences` | Notification preferences |

## Data model

The design export's vocabulary carries through to the tables: a syndicate is a
`group`, a seat for one fixture is a `seat_allocation`, and money movements are
rows in `transactions`.

A resale listing is not a table of its own. It is a seat allocation whose
`status` is `resale_listed` with a `resale_price_cents`; a seat offered back to
the syndicate for free sits at `on_bench`. `/api/groups/{id}/listings` reads
both.

`roster_players` and `opponents`/`opponent_players` (migration `0002`) are
club-wide reference data, not scoped to a `group` — every syndicate reads the
same squad and opponent dossiers. Per-player stats and per-opponent quick
stats are free-form `[label, value]` pairs stored as JSON text (`stats_json`,
`quick_stats_json`), since which stats matter varies by position; handlers
decode them before returning.

An expense split writes one `transactions` row per member who owes a share,
all sharing a `split_id` so the split can be shown or reversed as one unit. The
payer's own share is not written, since nobody owes themselves.

## Cron jobs

| Schedule | Job |
| --- | --- |
| `0 8 * * *` | Schedule the next unscheduled player bio for today |
| `0 10 * * *` | Find seats still on the bench three days before kickoff |

## What is deliberately left out

- **Sign-in.** `POST /api/auth/session` returns 501. Verifying the Google or
  Apple ID token against the provider's JWKS and writing `session:<token>` into
  the SESSIONS KV namespace is the only missing piece; `src/auth.py` already
  reads the other end of it.
- **Push delivery.** The 10:00 cron finds who needs a nudge and logs it; it
  does not send anything yet.
- **Weighted payouts.** `split_equally` splits an expense evenly. Weighting by
  fixture tier and crediting members who bench a seat are still being decided;
  when they land, that one function changes.

## Testing

`npm test` runs the Python suite. `tests/test_router.py` and
`tests/test_splits.py` cover the pure logic. `tests/test_api.py` drives
`on_fetch` end to end against an in-memory SQLite database standing in for D1,
so the routing, SQL and handler behaviour are exercised without the Workers
runtime.
