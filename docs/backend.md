# Backend

The API is a single Cloudflare Python Worker (`summit-basecamp-api`) over D1 for
data, and KV for both sessions and member-uploaded profile pictures. The PWA is
deployed separately on Cloudflare Pages and talks to this Worker cross-origin.

Player headshots and club crests still have no object storage behind them --
they're committed to `frontend/public/assets/images/` and served by Pages;
`player_bios.image_path` holds the root-relative path to each one, falling
back to `/assets/images/players/placeholder-avatar.webp`. Member avatars are
the exception (see "Profile pictures" below): they're uploaded at runtime, so
they can't be committed to the repo the way the roster/bio images are, hence
the second KV namespace (`AVATARS`). Not R2: R2 needs its own one-time
account-level enablement in the Cloudflare dashboard before any API token can
touch it, which cost a broken deploy the first time this was wired up (see
git history) -- KV was already active on this account via SESSIONS, and a
profile picture is nowhere near KV's 25 MiB per-value limit.

## Layout

| Path | What it holds |
| --- | --- |
| `wrangler.jsonc` | Worker config: D1, KV, cron triggers |
| `migrations/0001_initial.sql` | The D1 schema |
| `migrations/0002_roster.sql` | Home-team squad and opponent dossiers |
| `migrations/0003_national_team.sql` | National-team caps history for squad players |
| `migrations/0006_opponent_sync.sql` | Sync tracking columns (`source_ref`, `source_slug`, `match_url`) for opponents/opponent_players, and nullable `opponent_players.jersey_number` |
| `migrations/0007_fixture_source_ref_unique.sql` | Partial unique index on `fixtures(group_id, source_ref)`, guarding `_create_fixture_from_sync` against two overlapping sync runs both creating the same fixture |
| `migrations/0008_group_invite_codes.sql` | `groups.invite_code`, unique, backing `POST /api/groups/join` |
| `migrations/0009_user_contact_info.sql` | `users.phone`, `users.contact_email`, backing `PATCH /api/me` |
| `migrations/0010_guest_password_auth.sql` | Seeds the six shared-password guest slots (`usr_guest1`..`usr_guest6`) sign-in uses |
| `migrations/0011_syndicate_seat_labels.sql` | `groups.section`/`seat_row`/`seat_labels`, `group_members.seat_label` -- the real physical seats behind a syndicate, distinct from the internal 1..`total_seats` seat numbering |
| `seed/dev_seed.sql` | Four members, two fixtures, a part-paid ledger, the squad and all 15 opponent dossiers -- dev only, not safe to run against production (see below); DELETE-then-INSERT throughout, so rerunning it against the same database is a full reset |
| `seed/roster_seed.sql` | Just the real home roster, safe to run against production (`wrangler d1 execute ... --remote --file=seed/roster_seed.sql`) as a one-off; the sync job is the ongoing way this table gets updated |
| `seed/opponents_seed.sql` | All 15 real opponent dossiers, safe to run against production -- **not** just an optional bootstrap like the other two seeds; the sync job never creates an opponent row from nothing, only updates ones this file (or an equivalent) already put there. Idempotent (`INSERT ... ON CONFLICT DO UPDATE`, never a DELETE), so rerunning it -- to add a club or fix a typo -- never wipes sync-owned `opponent_players` rows or an admin's hand-edited `form`/`shape_note` |
| `src/entry.py` | `on_fetch` route table, `on_scheduled` cron jobs |
| `src/router.py` | Path matching (`/api/groups/{group_id}/fixtures`) |
| `src/handlers.py` | One function per endpoint, including admin-only `trigger_sync` |
| `src/db.py` | D1 helpers that hand back plain dicts |
| `src/storage.py` | KV helpers for the `AVATARS` namespace (member profile pictures) |
| `src/auth.py` | Bearer token to user, membership and admin checks |
| `src/splits.py` | Expense-split and settle-up arithmetic |
| `src/responses.py` | JSON responses, `ApiError`, and `binary_response` for a non-JSON body (an avatar) |
| `src/sync.py` | Roster/fixture/opponent/headshot sync: diffs external data against D1 and writes what drifted |
| `src/sync_sources.py` | Fetching and parsing for the NWSL and Wikipedia sources `sync.py` reconciles against |
| `.github/workflows/sync-roster.yml` | Triggers the sync via `POST /api/admin/sync`, on deploy and on a weekly schedule |

## Running it

```sh
npm install
npm run migrate:local      # apply migrations to the local D1 database
npm run seed:local         # load the development data
npm run dev                # wrangler dev on http://localhost:8787
npm test                   # the Python unit and API tests
```

With `ENVIRONMENT=development` real sign-in is skipped: name the caller
in an `X-Dev-User` header instead of a bearer token.

```sh
curl -H 'X-Dev-User: usr_ada' http://localhost:8787/api/groups
```

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/health` | Liveness, including a D1 round trip |
| GET | `/api/auth/guests` | The six shared-password guest slots, id and current name (unauthenticated) |
| POST | `/api/auth/session` | Sign in to a guest slot with the shared site password |
| GET | `/api/me` | The signed-in member and their notification preferences |
| PATCH | `/api/me` | Edit your own display name, phone or fallback contact email |
| GET | `/api/groups` | Syndicates the caller belongs to |
| POST | `/api/groups` | Start a syndicate; the creator becomes its admin, and gets a fresh invite code |
| POST | `/api/groups/join` | Join an existing syndicate by its invite code |
| GET | `/api/groups/{id}` | One syndicate and its members |
| PATCH | `/api/groups/{id}` | Rename a syndicate, set its total package price, or grow/shrink its total seat count (admin) |
| POST | `/api/groups/{id}/invite-code/rotate` | Replace a syndicate's invite code (admin) |
| GET | `/api/groups/{id}/members` | Members only |
| PATCH | `/api/groups/{id}/members/{user_id}` | Change a member's default seat number (self, or admin for anyone); change a role (admin only) |
| GET | `/api/groups/{id}/fixtures` | Fixtures in kickoff order |
| POST | `/api/groups/{id}/fixtures` | Add a fixture (admin); seats are created with it |
| GET | `/api/fixtures/{id}/seats` | The seat map for one fixture |
| PATCH | `/api/seats/{id}` | Claim, bench, gift, or list a seat for resale (holder); reassign or edit any seat regardless of holder (admin) |
| GET | `/api/groups/{id}/listings` | Upcoming seats going spare |
| GET | `/api/groups/{id}/ledger` | Unsettled transactions, net balances, settle plan |
| POST | `/api/groups/{id}/expenses` | Record an expense and split it |
| POST | `/api/groups/{id}/settle` | Mark the debts with one member settled |
| GET | `/api/bios/today` | The player bio scheduled for today |
| GET | `/api/roster` | The home squad, club-wide (not per-syndicate) |
| GET | `/api/opponents` | Visiting-club dossiers, each with its own scouting roster |
| GET/PUT | `/api/preferences` | Notification preferences |
| PUT | `/api/me/avatar` | Upload the caller's own profile picture |
| GET | `/api/avatars/{user_id}` | Fetch a member's uploaded profile picture |

## Data model

The design export's vocabulary carries through to the tables: a syndicate is a
`group`, a seat for one fixture is a `seat_allocation`, and money movements are
rows in `transactions`.

A resale listing is not a table of its own. It is a seat allocation whose
`status` is `resale_listed` with a `resale_price_cents`; a seat offered back to
the syndicate for free sits at `on_bench`. `/api/groups/{id}/listings` reads
both.

`group_members.default_seat_number` (edited via `PATCH .../members/{user_id}`)
is a member's season-long seat assignment -- what their Profile card shows --
separate from `seat_allocations`, which is who is actually sitting where for
one specific fixture (edited via `PATCH /api/seats/{id}`). A regular member
can only change either for themselves: their own default seat, or a seat they
already hold (bench it, gift it, list it -- never assign it to someone else,
since they have no transfer authority over another member's seat). A
syndicate admin can change both for anyone: reassign or bench any seat in
their syndicate regardless of who holds it, edit any member's default seat
number, and promote or demote a member's role -- the override that lets an
admin fix a seat nobody else involved can (e.g. one whose holder has left the
syndicate).

`default_seat_number` and `seat_allocations.seat_number` are an internal
1..`total_seats` index used to assign and track seats -- they are not what's
printed on anyone's actual ticket. `groups.section`/`seat_row`/`seat_labels`
(migration `0011`, all optional freeform text, settable at `POST /api/groups`
time) describe the syndicate's real physical seats -- e.g. Section 114, Row
8, seat_labels `"3, 4"` -- as one shared block for the whole package, the
same shape the design export's own mock data uses. `group_members.seat_label`
(also freeform text, edited the same way and under the same permission rules
as `default_seat_number` via `PATCH .../members/{user_id}`, or set for the
creator at creation via `my_seat_label`) is which one of those real seats is
a given member's own. Neither is validated against the other -- there is no
constraint tying a `seat_label` to appear in the group's own `seat_labels`
string -- since both are free text describing the real world, not identifiers
anything else in the schema joins against.

An admin can also grow or shrink the syndicate itself, via `total_seats` on
`PATCH /api/groups/{id}`. Growing it retrofits every existing fixture with
one new `on_bench` `seat_allocation` per new seat number, the same shape
`create_fixture` seeds a brand-new fixture with. Shrinking is refused with
409 if it would silently destroy anything: a member's `default_seat_number`
still pointing above the new total, or a `seat_allocation` above it that
isn't just `on_bench` (confirmed, gifted, or resale-listed) -- both have to
be freed by hand first, the same way the collision guards elsewhere in this
file work.

## Invite codes

Every syndicate has an `invite_code` (`groups.invite_code`, backfilled for
pre-existing rows by migration `0008`, generated fresh for a new one in
`create_group`) -- 16 hex characters from `secrets` (`db.new_invite_code`),
64 bits so it can't be brute-forced over the network (nothing else gates
`POST /api/groups/join` -- no throttling, no expiry), distinct from the
shorter, non-secret `new_id()` ids used elsewhere. `POST /api/groups/join`
looks a code up (case-insensitively) and adds the caller as a plain `member`
with no `default_seat_number`, the same starting point as anyone else added
to a syndicate. Already a member: 409. Unknown code: 404.
`POST /api/groups/{id}/invite-code/rotate` (admin-only) replaces a
syndicate's code outright, so a leaked or no-longer-wanted one stops working
without touching anyone already in.

Deploys apply migrations before deploying the Worker (see "Renaming the
Worker or Pages project" below, same ordering), so there is a narrow window
where a previous Worker version -- built before `create_group` knew
`invite_code` existed -- could still insert a group with none, if a deploy
ever lands old code after this migration. `invite_code` has no `NOT NULL`
for exactly that reason: a `NOT NULL` insert from that stale code would 500
outright rather than merely leave the row without a code. Recovery is the
same rotate call above, run once by that syndicate's admin -- not
self-healing, but not stuck either. A `CREATE TRIGGER` in the migration
itself would close the window automatically, but D1's remote migration
runner has a real, currently-open bug misparsing multi-statement
`BEGIN ... END` trigger bodies (`SQLITE_ERROR` / code 7500 --
[cloudflare/workers-sdk#10998](https://github.com/cloudflare/workers-sdk/issues/10998),
[#15690](https://github.com/cloudflare/workers-sdk/issues/15690)) even
though the same SQL runs fine locally -- worth revisiting once that's fixed
upstream, not worth risking a broken production migration for now.

## Sign-in

There is no per-person auth. Sign-in is a shared-password gate over six fixed
guest slots (`usr_guest1`..`usr_guest6`, seeded by migration `0010`): everyone
types the same `SITE_PWD` Worker secret and picks which slot they are.
`POST /api/auth/session` (`src/handlers.begin_session`) checks the password
with `hmac.compare_digest` (same constant-time pattern as `trigger_sync`'s
`SYNC_ADMIN_TOKEN` check) via `src/auth.verify_site_password`, then mints a
session token (`src/auth.start_session`, 64 bytes from `secrets`) and writes
`session:<token>` into the `SESSIONS` KV namespace with a 30-day TTL -- the
write side of `_user_id_from_request`'s read. `GET /api/auth/guests` lists
all six slots' current names, unauthenticated, so the landing screen can show
real names to a visitor who has not signed in yet.

Each slot starts named "Guest N". `PATCH /api/me` (`src/handlers.update_me`)
lets whoever is signed into a slot replace that with their own name, which
then sticks for that slot going forward -- the frontend does this as part of
signing in (a "Your name" field on the same landing-screen form as the
password), but nothing about the endpoint ties it to that specific moment.

Set `SITE_PWD` once as a secret in the `sb` GitHub environment; like
`CF_SYNC_ADMIN_TOKEN`, deploy.yml's "Set SITE_PWD secret" step pushes it to
the Worker on every deploy, no local `wrangler secret put` needed. Never set,
`POST /api/auth/session` refuses every call with 503 rather than falling
open. Removing the GitHub secret later doesn't just stop future pushes --
a Worker secret persists on Cloudflare independently of GitHub, so deploy.yml's
"Delete SITE_PWD secret if removed from GitHub" step actively deletes it from
the Worker in that case, so revoking access really revokes it rather than
leaving the last-deployed password silently active.

There is deliberately no rate-limiting or lockout on wrong-password attempts
beyond the constant-time comparison -- the same call this codebase already
made for invite codes (see "Invite codes" above): the password is a single
shared secret whose entropy is the deploying admin's to choose, not a
per-account credential guarding something that needs its own throttling.

## Profile

`PATCH /api/me` edits the caller's own `name`, `phone`, or `contact_email`
(migration `0009`) -- the Settings screen's "Group & profile" card, and also
how a guest slot replaces its "Guest N" placeholder (see "Sign-in" above).
`name` can be changed but never cleared to empty, since it's what every
other member sees in a member list; `phone`/`contact_email` can be cleared
by sending `null` or an empty string. All three fields are optional in one
call (only what's present in the body changes), and a body with none of
them is rejected.

`phone` and `contact_email` are their own columns, not the same as `email`
(migration `0001`, unique -- the guest slot's own login identity, not a
contact address) -- a member's fallback contact for a critical ticket
transfer isn't necessarily the same number or address they sign in with.

## Profile pictures

`PUT /api/me/avatar` stores the caller's own profile picture in the `AVATARS`
KV namespace and points `users.avatar_url` at `GET /api/avatars/{user_id}`,
which streams it back out. The request body is JSON
(`{"content_type", "image_base64"}`), not a raw/multipart upload -- Workers
Python's body handling is simplest through the same `read_json()` every other
handler already uses, and a profile picture is small enough (capped at 2 MiB)
that base64's overhead doesn't matter. `content_type` must be
`image/png`, `image/jpeg`, or `image/webp`.

Each user has exactly one value in KV, keyed by their id with no extension;
the content type is stored as that value's own KV metadata rather than baked
into the key. Re-uploading in a different format replaces the picture
outright instead of leaving an orphaned copy under its old key.

`GET /api/avatars/{user_id}` is deliberately unauthenticated: an avatar isn't
sensitive, and every other member who can already see this user's name in a
member list needs to be able to show their picture too, which an auth-gated
image would make awkward (threading a bearer token through an `<img src>`).

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

The roster/fixture/headshot sync used to be a third Worker cron here
(`0 5 * * 1`). It now runs as a GitHub Actions workflow instead --
`.github/workflows/sync-roster.yml`, on the same weekly schedule plus every
successful deploy to main -- calling `POST /api/admin/sync`
(`src/handlers.trigger_sync`) rather than being invoked by
`on_scheduled`. That trades the "stays behind the existing D1 binding, no
second deployment path" argument for a run's logs and history living in
GitHub Actions with everything else in this repo, and for a sync firing
right after the code or data that feeds it changes rather than waiting up
to a week for the next cron tick. The admin endpoint is authenticated by a
shared-secret bearer token (`SYNC_ADMIN_TOKEN` on the Worker), not a
signed-in user. Set it once as the `CF_SYNC_ADMIN_TOKEN` secret in the
`sb` GitHub environment -- deploy.yml's "Set SYNC_ADMIN_TOKEN secret" step
pushes that value to the Worker on every deploy, so there is no
`wrangler secret put` to run by hand.

### Roster/fixture/opponent/headshot sync

`src/sync.py` runs five independent jobs: roster and fixture facts from
nwslsoccer.com's Denver Summit team page, opponent facts and rosters from
the same site's pages for the other 15 NWSL clubs, and player headshots
from Wikipedia's API, filtered to CC0/CC-BY/public-domain licenses only.
Neither the schedule page nor a roster page (Denver Summit's or any other
club's -- they share the same page template) renders JSON-LD (both were
assumed to; verified against real snapshots of both on 2026-09-21/22 that
neither does) -- both are plain server-rendered markup (a match-list widget
and a roster table), so every job that touches either scrapes that markup
directly. See `src/sync_sources.py` for both parsers, and what happens if either page's
markup changes -- each raises rather than returning a partial result if
even one row fails to parse, since a shorter-but-nonempty result would
otherwise look like a clean, smaller roster/schedule instead of a broken
scraper. Existing rows are matched by `source_ref` (falling back to a name
match the first time) and only the fields that drifted are written, so
hand-curated content -- scouting notes, stats, dossier prose -- is never
overwritten; a field the source came back without (a blank position, an
empty venue) never blanks out an existing value. A fixture is scoped to one
syndicate (`group_id`), so more than one syndicate's fixture row can match
the same real-world match -- the sync updates every matching row, not just
one. A fixture not yet matched by `source_ref` is matched by opponent
within a 21-day window of its kickoff date, wide enough to catch a real
reschedule without confusing a team's home and away fixtures against the
same opponent later in the season.

A home fixture still ahead of kickoff that has no matching row yet in a
given syndicate gets one created for it there (every seat starting
unassigned, on the bench), one per syndicate missing it -- unlike
`handlers.create_fixture`, this never pre-assigns a member's default seat,
since nobody has claimed anything on a fixture nobody asked for; `tier` and
`weighted_value_cents` get placeholders (`'standard'`, `0`) for an admin to
correct, since a source page has no idea what a group's package costs.
Away fixtures and ones that have already kicked off never create anything:
this app only ever sells seats at the home venue, and a match already
played has nothing left to claim. Opponent dossiers are still only ever
updated, never created here -- the scouting content that makes a dossier
useful (a real result, a real roster) still needs `seed/opponents_seed.sql`
run once first, the same way a fixture still needs a syndicate to hold it
before sync can touch it.

Roster players not seen in a run are marked `active = FALSE` rather than
deleted, so their stats and national-team history survive a departure;
`GET /api/roster` only returns active players. Opponents are matched by
`source_ref` too now -- nwslsoccer.com's own team id for that club, read
off the schedule page's `data-team-id` for free while parsing fixtures
(`fetch_nwsl_schedule`'s `opponent_team_id`) -- falling back to a name
match and setting `source_ref` the first time that succeeds, same
two-step pattern as the roster. The previous claim that opponents have no
stable identifier only held before the schedule page's real markup was
scraped.

A fifth job, `_sync_opponent_rosters`, reconciles each tracked opponent's
real players into `opponent_players`, the same insert/update/deactivate
logic as the home roster but scoped to one `opponent_id` at a time. An
opponent is "tracked" once it has both `source_ref` and `source_slug` (that
club's own roster-page slug) on file; `seed/opponents_seed.sql` seeds both,
verified directly against nwslsoccer.com for all 15 clubs rather than
guessed from a naming pattern -- Denver Summit's own roster-page slug
(`denver-summit-fc`) does not match its match-page slug (`denver-summit`),
so the same pattern can't be trusted for any other club either. A club
missing either column is silently left alone (nothing to fetch yet); a
wrong or dead `source_slug` shows up as a per-club error in that job's
result instead of failing the whole sync -- see
`sync._sync_one_opponent_roster` and its caller for how a bad one gets
caught rather than corrupting data.

There is no object storage (see above), so a sync-sourced headshot is stored
as the full Wikimedia Commons URL rather than a path under
`frontend/public/assets/images/`; `roster_players.image_path` can hold
either a root-relative asset path (hand-curated) or an `https://` URL
(synced), and `roster_players.image_attribution` carries the credit line for
the latter.

### The naive-datetime/timezone gap

`fixtures.kickoff_at` (and the remote kickoff time `fetch_nwsl_schedule`
parses it from) is a naive local-ish timestamp -- whatever the schedule
page displays, with no timezone offset attached. The Worker's own clock,
and SQLite's `DATETIME('now')`, are both naive UTC. Comparing the two
directly is comparing two different instants that happen to share a
format: a 6:45 PM Mountain Time kickoff is roughly 00:45 UTC the next day,
so a naive `remote_kickoff <= now` can call a match "already kicked off"
up to several hours before it truly has.

This is a pre-existing gap, not something introduced by the sync job --
the bench-alert cron in `src/handlers.py` (the 10:00 job in the table
above, finding seats still on the bench three days before kickoff) compares
`fixtures.kickoff_at` against `DATETIME('now')` the same naive way. Neither
place has been fully fixed here; a real fix needs each match's actual
timezone (the source page doesn't provide one) rather than a margin.

`src/sync.py`'s fixture-creation check (`_sync_fixtures`, see its comments)
mitigates its own instance with `_KICKOFF_TIMEZONE_SLOP`, a 24-hour margin
comfortably larger than any real offset a US-based NWSL venue could
produce: it only skips creating a fixture once `remote_kickoff` is more
than 24 hours in the past by the Worker's clock, deliberately erring toward
creating a fixture a little early rather than silently missing a real
upcoming one -- an admin can remove an accidentally-early fixture, but a
wrongly-skipped one just never appears at all.

## What is deliberately left out

- **Push delivery.** The 10:00 cron finds who needs a nudge and logs it; it
  does not send anything yet.
- **Weighted payouts.** `split_equally` splits an expense evenly. Weighting by
  fixture tier and crediting members who bench a seat are still being decided;
  when they land, that one function changes.
- **The frontend calls this API in exactly one place.** `web/index.html` is
  still a static build (`web/build_src/build.py`) from mock data in
  `web/build_src/data.py`, and `web/src/app.js` still mostly just toggles
  pre-rendered DOM. Sign-in (see "Sign-in" above) is the one real exception --
  `POST /api/auth/session`, `GET /api/auth/guests` and `PATCH /api/me` are
  now reachable from the deployed site, using `API_BASE` (`app.js`, hardcoded
  to the Worker's own hostname -- update it by hand the same way
  `CF_API_BASE_URL` already needs updating on a Worker rename, see
  `docs/deploy.md`). Every other endpoint above -- the syndicate/fixture/seat
  data, the ledger, avatar upload -- is real and tested (`tests/test_api.py`)
  but still not reachable from the deployed site; a signed-in session now
  exists to authenticate those calls with, but wiring each screen up to real
  data is still its own piece of work, not something this change set
  attempts to close.

## Testing

`npm test` runs the Python suite. `tests/test_router.py` and
`tests/test_splits.py` cover the pure logic. `tests/test_api.py` drives
`on_fetch` end to end against an in-memory SQLite database standing in for D1,
so the routing, SQL and handler behaviour are exercised without the Workers
runtime.
