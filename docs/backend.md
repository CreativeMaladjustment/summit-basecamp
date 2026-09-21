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
| `migrations/0003_national_team.sql` | National-team caps history for squad players |
| `seed/dev_seed.sql` | Four members, two fixtures, a part-paid ledger, the squad and opponent dossiers |
| `src/entry.py` | `on_fetch` route table, `on_scheduled` cron jobs |
| `src/router.py` | Path matching (`/api/groups/{group_id}/fixtures`) |
| `src/handlers.py` | One function per endpoint |
| `src/db.py` | D1 helpers that hand back plain dicts |
| `src/auth.py` | Bearer token to user, membership and admin checks |
| `src/splits.py` | Expense-split and settle-up arithmetic |
| `src/responses.py` | JSON responses and `ApiError` |
| `src/sync.py` | Weekly roster/fixture/headshot sync: diffs external data against D1 and writes what drifted |
| `src/sync_sources.py` | Fetching and parsing for the NWSL and Wikipedia sources `sync.py` reconciles against |

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

`national_team_appearances` (migration `0003`) is one row per national-team
stint for a `roster_players` row -- a player can have represented more than
one country, or the same one more than once, over a career. `year_end IS
NULL` marks a stint still active. `GET /api/roster` nests each player's full
history under `national_team_history` and also surfaces a convenience
`current_national_team` (the country of their open stint, or `null`).

An expense split writes one `transactions` row per member who owes a share,
all sharing a `split_id` so the split can be shown or reversed as one unit. The
payer's own share is not written, since nobody owes themselves.

## Cron jobs

| Schedule | Job |
| --- | --- |
| `0 8 * * *` | Schedule the next unscheduled player bio for today |
| `0 10 * * *` | Find seats still on the bench three days before kickoff |
| `0 5 * * 1` | Sync `roster_players`, `fixtures` and `opponents` against nwslsoccer.com, and headshots against Wikipedia (`src/sync.py`) |

### Roster/fixture/headshot sync

A Worker cron rather than a separate GitHub Actions workflow, since the data
it reconciles already lives behind this Worker's D1 binding and the two
existing daily crons already run the same way -- a second deployment path
(a workflow with its own D1 credentials) would buy nothing here.

`src/sync.py` runs four independent jobs weekly: roster and fixture facts
from nwslsoccer.com's Denver Summit team pages (JSON-LD embedded in the
page; see `src/sync_sources.py` for why and what happens if that markup
changes), and player headshots from Wikipedia's API, filtered to
CC0/CC-BY/public-domain licenses only. Existing rows are matched by
`source_ref` (falling back to a name match the first time) and only the
fields that drifted are written, so hand-curated content -- scouting notes,
stats, dossier prose -- is never overwritten; a field the source came back
without (a blank position, an empty venue) never blanks out an existing
value. Fixtures and opponent dossiers are only ever updated, never created,
by this job: creating a fixture also creates its seat allocations, which
stays an admin decision. A fixture is scoped to one syndicate (`group_id`),
so more than one syndicate's fixture row can match the same real-world
match -- the sync updates every matching row, not just one. A fixture not
yet matched by `source_ref` is matched by opponent within a 21-day window of
its kickoff date, wide enough to catch a real reschedule without confusing a
team's home and away fixtures against the same opponent later in the
season.

Roster players not seen in a run are marked `active = FALSE` rather than
deleted, so their stats and national-team history survive a departure;
`GET /api/roster` only returns active players. Opponents have no
`source_ref` -- nwslsoccer.com's schedule data carries no stable per-club
identifier, only the name, so matching stays name-based and a club rename
upstream needs a manual re-match.

There is no object storage (see above), so a sync-sourced headshot is stored
as the full Wikimedia Commons URL rather than a path under
`frontend/public/assets/images/`; `roster_players.image_path` can hold
either a root-relative asset path (hand-curated) or an `https://` URL
(synced), and `roster_players.image_attribution` carries the credit line for
the latter.

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
