# SquadSeats Requirements Document

_As of 2026-09-21_

## Purpose

SquadSeats (internally "Summit Basecamp") is a mobile-first progressive web app (PWA) for a season-ticket syndicate: a small group of fans (a "circle") who co-own a season package for one club (modeled on Denver Summit FC) and need to coordinate who sits in which seat at which fixture, hand off seats they can't use, and split the shared costs fairly.

The product solves three problems syndicates otherwise track by spreadsheet and group chat:

1. **Seat allocation** — who holds which seat for which match, and what happens when a seat-holder can't go (release to the bench, gift it to a guest, or list it externally).
2. **Liquidity** — surfacing seats that are free ("on the bench") so another member can claim them before a match, rather than a seat going empty.
3. **Expense splitting** — the shared package cost and match-day extras, split by a weighted formula (rivalry/cup fixtures cost more than standard ones), with a running ledger and a one-tap settle-up.

## Current state

The repository (`creativemaladjustment/summit-basecamp`) has both halves scaffolded and merged to `main`: a Cloudflare Python Worker API over D1 (`src/`, `migrations/0001_initial.sql`, `docs/backend.md`) and a pre-rendered Python-generated PWA (`web/`, `web/README.md`). The two are not yet wired together — the frontend currently renders from mock data baked in at build time (`web/build_src/data.py`); replacing that with live calls to the Worker API is the largest piece of work still ahead. This document describes requirements grounded in what is actually built, not the original design brief's full aspirational scope.

## User roles

| Role | Defined by | Can do |
| --- | --- | --- |
| Admin | `group_members.role = 'admin'`, the syndicate's creator by default | Everything a member can, plus add fixtures (`POST /api/groups/{id}/fixtures`); promote or demote a member's role, and reassign or bench any seat or any member's default seat regardless of who holds it (`PATCH /api/groups/{id}/members/{user_id}`, `PATCH /api/seats/{id}`); grow or shrink the syndicate's `total_seats` (`PATCH /api/groups/{id}`); rotate the syndicate's invite code (`POST /api/groups/{id}/invite-code/rotate`). *No route to remove a member outright yet* — only role changes, seat reassignment, and resizing are built. |
| Member | `group_members.role = 'member'` | Belongs to one or more syndicates (`groups`); claims, releases, gifts or lists their own seats; records and settles expenses; sets their own notification preferences |
| Guest | `seat_allocations.guest_name`, no `users` row | Receives a gifted seat; not a syndicate member, has no login or ledger entry |

Not to be confused with the sign-in "guest slots" (`usr_guest1`..`usr_guest6`,
`users.auth_provider = 'password'`) above — those are real, logged-in
`users` rows behind the shared site password, distinct from this table's
seat-gift `Guest`, which has no account at all.

A single person can be a member of several syndicates (`group_members` is keyed by `group_id, user_id`), each with its own roster, fixtures and ledger — there is no cross-syndicate view beyond "Find your syndicate" and per-syndicate switching implied by `GET /api/groups`.

Sign-in is a shared-password gate, not per-person auth (see `docs/backend.md`
"Sign-in"): six fixed guest slots (`users.auth_provider = 'password'`), one
site-wide password, no email/password-per-person path and no anonymous
browsing beyond the Landing and "Find your syndicate" screens.

## Core features by screen

| Screen | Purpose | Backed by |
| --- | --- | --- |
| Landing | Summit Basecamp lockup, tonight's Summit Touchline notes as teasers, six guest logins behind one shared password (remembered on the device after the first time) | `GET /api/auth/guests`, `POST /api/auth/session`, `PATCH /api/me` (all built and wired) |
| Find your syndicate | Join by invite code, or start a new one | `POST /api/groups`, `POST /api/groups/join` (both wired to the real API — a syndicate created or joined here is real, and every screen below reflects it) |
| Matchday | Next Match hero, Summit Touchline carousel, bench note threads, balance line | `GET /api/groups/{id}/fixtures`, `GET /api/fixtures/{id}/seats`, `GET /api/groups/{id}/bench-notes`, `GET /api/groups/{id}/ledger` (balance line), `GET /api/bios/today`. The Summit Touchline carousel is the one part still fixed daily-content flavor, unrelated to fixture data. |
| The 14er Pass | Every home fixture in the season, filtered by All / My Matches / On the Bench | `GET /api/groups/{id}/fixtures`, `GET /api/fixtures/{id}/seats` |
| The Bench | Seats waiting for a sub, plus anything listed on an external resale exchange | `GET /api/groups/{id}/fixtures` + `.../seats` (filtered client-side to `on_bench`/`resale_listed`), `GET /api/groups/{id}/bench-notes`, `POST /api/bench-notes/{id}/replies` |
| The 14ers | Package cost, simplified debts, Settle Up, season history | `GET /api/groups/{id}/ledger`, `POST /api/groups/{id}/expenses`, `POST /api/groups/{id}/settle` (wired: real package price, real seat/member counts, and real per-member balances via `net_balances`/`settle_plan` — evenly split, no fixture-tier weighting; the old weighted-by-tier breakdown is gone since no real fixture has a tier yet) |
| Home Team | Full squad roster with position filters, stats and scouting notes (a "Peak Tifo" visual grid) | `GET /api/roster` (frontend still renders from `web/build_src/data.py`, not wired yet) |
| Visitors | The visiting club's dressing room: real club/date/venue facts, the most recent meeting's result, real rosters where synced | `GET /api/opponents` (frontend still renders from `web/build_src/data.py`, not wired yet) |
| Campfire Settings | Push permissions, matchday alerts, Summit Touchline notes mix, profile | `GET/PUT /api/preferences`, `GET/PATCH /api/me` |

### Seat handoff ("Call a Sub")

A seat holder who can't attend a fixture has three ways to give up their seat, all going through `PATCH /api/seats/{id}`:

1. **Release to the Bench** — posts a note to the circle with an explicit cost choice: *get paid back* at face value, or *on the house* at no cost. Status becomes `on_bench`.
2. **Send to Guest** — a direct gift to a named guest (`guest_name`); nobody's ledger balance moves. Status becomes `gifted`.
3. **List Outside the 14ers** — flags the seat as listed on an external exchange (SeatGeek/Ticketmaster) with a `resale_price_cents`. Status becomes `resale_listed`. This is a tracking flag only: SquadSeats has no API integration with any ticketing platform (SeatGeek, Ticketmaster, the club's own app, etc.) — the admin or seat holder must actually transfer or sell the ticket on that platform themselves, outside the app.

### Expense splitting

An expense (`POST /api/groups/{id}/expenses`) writes one `transactions` row per member owing a share (all sharing a `split_id` so the split can be shown or reversed as a unit); the payer owes nothing so gets no row. Splits are currently equal only — `split_equally` in `src/splits.py`. Weighting by fixture tier, and crediting members who release a seat to the bench, are named in `docs/backend.md` as decided-but-not-built.

## Functional requirements

1. **Authentication.** Sign in to one of six shared guest slots with a single site-wide password (`POST /api/auth/session`); a session is a bearer token resolved server-side to a `users` row (`src/auth.py`). In development, `X-Dev-User` substitutes for a real session. Whoever is signed into a slot can set their own display name (`PATCH /api/me`), replacing that slot's "Guest N" placeholder for good.
2. **Syndicate management.** A member creates a syndicate (name, season, total seats, package cost) and becomes its admin (`POST /api/groups`), which also mints the syndicate's invite code. Each syndicate has its own roster, fixtures and ledger. Another member joins an existing syndicate with that code (`POST /api/groups/join`); an admin can rotate it (`POST /api/groups/{id}/invite-code/rotate`) or resize the syndicate's `total_seats` (`PATCH /api/groups/{id}`), which retrofits existing fixtures with the new seats and refuses to shrink past anything still occupied. *Gap: no route to remove a member outright.*
3. **Fixture & seat management.** An admin adds fixtures (opponent, kickoff time, venue, tier). Seats are created with the fixture and default to `confirmed`, assigned to each member's `default_seat_number`.
4. **Seat handoff.** A seat holder can release, gift, or externally list a seat they can't use (see Seat handoff above); every seat has exactly one current status (`confirmed`, `on_bench`, `gifted`, `resale_listed`).
5. **Bench liquidity.** Seats `on_bench` or `resale_listed` are surfaced via `GET /api/groups/{id}/listings` so another member can claim them before kickoff. A daily cron (10:00) finds seats still on the bench 3 days out for a nudge — *the nudge is logged, not delivered; push send is unbuilt.*
6. **Expense tracking & settlement.** Any member records an expense, split (currently equally) across the syndicate; the ledger (`GET /api/groups/{id}/ledger`) shows unsettled transactions, net balances per member, and a simplified settle-up plan. `POST /api/groups/{id}/settle` marks a member's debt settled.
7. **Player bios.** One scheduled bio per day (`player_bios.scheduled_date`), surfaced via `GET /api/bios/today`; a cron job (08:00) schedules the next unscheduled bio for today if none is set. `player_bios` rows are hand-entered today; see **Roster and fixture data sync** under Open questions for the planned automated source.
8. **Notification preferences.** Each member controls 3-day check-in alerts, bench alerts, and the scope of daily bios (home team only / Summit only / league-wide) via `GET/PUT /api/preferences`.
9. **Rosters (Home Team / Visitors).** `GET /api/roster` and `GET /api/opponents` (migration `0002_roster.sql`) back the squad and opposing-club dossiers, including per-player stats and scouting notes. The frontend does not call them yet — it still renders from placeholder data baked into the build (`web/build_src/data.py`).

### Known gaps between design and build

- No push notification delivery (only the underlying "who needs a nudge" logic).
- No integration with any external ticketing platform (SeatGeek, Ticketmaster, the club's own app) — "List Outside the 14ers" only tracks that a seat is listed; the admin or seat holder handles the actual transfer or sale themselves, outside SquadSeats.
- Frontend and backend are integrated everywhere except Home Team and Visitors: Landing (sign-in), "Find your syndicate" (create/join, plus skipping straight into a syndicate the signed-in guest slot already belongs to), the Settings profile card (name/phone/email), the header's "N seats · Sec/Row" readout, The 14ers ledger card (real package price/seat/member counts and real per-member balances), and Matchday/The 14er Pass/The Bench (real fixtures, real seats, claim/release/gift/resale-list, real bench notes and replies) are all built from the live API at runtime by `web/src/app.js` (`paintRealSyndicateDetail`, `paintRealFixtures`) rather than pre-rendered from `web/build_src/data.py`'s mock constants, which those screens no longer use at all. `src/sync.py`'s weekly roster/fixture sync creates real `fixtures` rows for a syndicate's upcoming home matches on its own, so a syndicate can see real fixtures without an admin manually adding any (`POST /api/groups/{id}/fixtures` still exists for adding one by hand). Home Team and Visitors are the two screens left rendering `web/build_src/data.py`'s placeholder roster/opponent content — wiring those up is the next milestone.

## Non-functional requirements

### Platform & performance

- Mobile-first, responsive PWA: one layout from a 390px phone up to a 1180px centred desktop shell, no breakpoint switch. Installable (`manifest.webmanifest`, `sw.js` app-shell cache).
- No build step or framework on the frontend — a dependency-free Python static-site generator pre-renders every screen and interactive state into one `index.html`; `web/src/app.js` toggles visibility for all of that, and separately builds real per-syndicate content (fixtures, seats, bench notes, the ledger) at runtime from the API, since which fixtures exist and who holds which seat isn't known until a real syndicate does.
- Backend is a single Cloudflare Python Worker over D1 (data) and KV (sessions) — no separate services to coordinate.

### Accessibility

Tap targets ≥ 44px; toggles are `role="switch"` with `aria-checked`; the Summit Touchline mix picker is a `radiogroup`; filter chips use a filled selected state rather than relying on `aria-selected` alone. Animation is dropped entirely under `prefers-reduced-motion`.

### Data & storage

- No object storage: player headshots and club crests are committed under `frontend/public/assets/images/` and served by Cloudflare Pages (`player_bios.image_path`), a deliberate choice to stay on Pages' free tier with no billing risk.
- Real per-syndicate/per-member data (balances, debts, seat assignments) must never be baked into the publicly-readable static build — it stays behind a runtime, session-authenticated fetch against the D1-backed API.

### Security

- Bearer-token sessions resolved to a user via `src/auth.py`; membership and admin checks gate write endpoints.
- Every pull request runs SAST (CodeQL, Semgrep, Gitleaks full-history secret scan, dependency review), a Terraform scan (dormant until `.tf` files exist), and a DAST baseline scan (ZAP, against a locally-served static build until a preview deployment exists) — see `docs/security-ci.md`.
- The Cloudflare API token used for deployment deliberately carries no zone/DNS permission.

### Deployment

- Deploys run through `.github/workflows/deploy.yml` on push to `main`, using the GitHub environment **"sb"** (holds `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`). The Worker deploys to Cloudflare Workers, the PWA to Cloudflare Pages, each independently detected and skipped if absent.
- All code changes land via pull request; nothing is pushed directly to `main`, and PRs require passing SAST/Terraform/DAST checks.
- Resource provisioning (D1, KV) is a separate manual workflow, `provision-cloudflare.yml`.

## Open questions & near-term scope

- **Frontend/backend wiring (feature next)** — no target date set; this is the largest remaining piece and touches every screen above except Landing, "Find your syndicate," and the Settings profile card, which are wired.
- **Push delivery** — the cron logic exists; the send mechanism (web push? provider?) is not chosen.
- **Weighted expense splits** — the formula for tier-weighted shares and bench-release credit is "still being decided" per `docs/backend.md`; `split_equally` is the only implementation today.
- **Roster/scouting data** — `GET /api/roster` and `GET /api/opponents` now back Home Team and Visitors with real tables (`roster_players`, `opponents`, `opponent_players`). The Denver Summit squad (`roster_players`) is the real 2026 roster as of 2026-09-21, kept current by the sync job below. `opponents` covers all 15 other NWSL clubs with real facts (real dates, real venue, the real result of the most recent meeting) as of 2026-09-22 -- see `seed/opponents_seed.sql`; no invented form/shape/"danger player" commentary, since none of that is published anywhere to verify. `opponent_players` has no rows seeded by hand (unlike the home roster, no local snapshot was transcribed for any opponent) -- it is populated entirely by `src/sync.py`'s `_sync_opponent_rosters`, using roster-page URLs the user verified directly for all 15 clubs, so real opponent rosters land the first time that job runs successfully against the deployed Worker rather than needing a follow-up transcription pass.
- **Roster and fixture data sync — built.** `src/sync.py` fetches Denver Summit's roster and schedule, opponent facts and opponent rosters from nwslsoccer.com, and player headshots from Wikipedia, matches them against `roster_players`, `fixtures`, `opponents` and `opponent_players`, updates only what drifted, and creates a new `fixtures` row (seats unassigned) for an upcoming home match no syndicate has one for yet -- see **Roster/fixture/opponent/headshot sync** in `docs/backend.md` for matching, creation, licensing and image storage. Triggered by `.github/workflows/sync-roster.yml` (`POST /api/admin/sync`) on every deploy to main and on its own weekly schedule, not a Cloudflare-side cron -- this repo's other automation (CI, deploy) already lives in GitHub Actions, so a run's logs and history live there too rather than in the Worker's own cron log. Still open: `nwslsoccer.com`'s page markup (a match-list widget for the schedule page, a plain HTML table for roster pages -- neither renders JSON-LD, despite both being assumed to at first; see `src/sync_sources.py`) is not a documented API and can change without notice; the sync raises and skips a job rather than writing a partial result when that happens (see the partial-parse checks in `fetch_nwsl_roster`/`fetch_nwsl_schedule`), so a markup change needs to be caught by watching the logs, not by an alert. Also still open: `web/build_src/data.py`'s `FIXTURES` and `OPPONENTS` (the static frontend build's own copies, transcribed by hand from the same sources) have no automated link to the sync job or to D1 -- the same disconnect the roster had, not yet resolved for fixtures or opponents either.
- **Joining a syndicate (invite codes) — built.** `POST /api/groups` mints a 16-character `invite_code` for a new syndicate; `POST /api/groups/join` redeems one, adding the caller as a plain member; `POST /api/groups/{id}/invite-code/rotate` (admin) replaces a leaked or unwanted code without disturbing existing members. See `docs/backend.md`. *Still open: removing a member outright — an admin can promote/demote or reassign a departed member's seats, but there is no route to drop their `group_members` row.*

This document reflects the repository as of 2026-09-21 (through PR #14, Cloudflare Pages provisioning). It should be revisited once the frontend/backend integration lands, since several "placeholder data" gaps above are expected to close then.
