# SquadSeats Requirements Document

_As of 2026-09-21_

## Purpose

SquadSeats (internally "Summit Hearth & Bench") is a mobile-first progressive web app (PWA) for a season-ticket syndicate: a small group of fans (a "circle") who co-own a season package for one club (modeled on Denver Summit FC) and need to coordinate who sits in which seat at which fixture, hand off seats they can't use, and split the shared costs fairly.

The product solves three problems syndicates otherwise track by spreadsheet and group chat:

1. **Seat allocation** — who holds which seat for which match, and what happens when a seat-holder can't go (release to the bench, gift it to a guest, or list it externally).
2. **Liquidity** — surfacing seats that are free ("on the bench") so another member can claim them before a match, rather than a seat going empty.
3. **Expense splitting** — the shared package cost and match-day extras, split by a weighted formula (rivalry/cup fixtures cost more than standard ones), with a running ledger and a one-tap settle-up.

## Current state

The repository (`creativemaladjustment/summit-hearth-and-bench`) has both halves scaffolded and merged to `main`: a Cloudflare Python Worker API over D1 (`src/`, `migrations/0001_initial.sql`, `docs/backend.md`) and a pre-rendered Python-generated PWA (`web/`, `web/README.md`). The two are not yet wired together — the frontend currently renders from mock data baked in at build time (`web/build_src/data.py`); replacing that with live calls to the Worker API is the largest piece of work still ahead. This document describes requirements grounded in what is actually built, not the original design brief's full aspirational scope.

## User roles

| Role | Defined by | Can do |
| --- | --- | --- |
| Admin | `group_members.role = 'admin'`, the syndicate's creator by default | Everything a member can, plus add fixtures (`POST /api/groups/{id}/fixtures`). *No API route exists to add, remove, or promote members* — the only write to `group_members` is the one row inserted for the creator when a group is created (`src/handlers.py`); this is a gap, not a built admin capability. |
| Member | `group_members.role = 'member'` | Belongs to one or more syndicates (`groups`); claims, releases, gifts or lists their own seats; records and settles expenses; sets their own notification preferences |
| Guest | `seat_allocations.guest_name`, no `users` row | Receives a gifted seat; not a syndicate member, has no login or ledger entry |

A single person can be a member of several syndicates (`group_members` is keyed by `group_id, user_id`), each with its own roster, fixtures and ledger — there is no cross-syndicate view beyond "Find your syndicate" and per-syndicate switching implied by `GET /api/groups`.

Sign-in is Google or Apple OIDC (`users.auth_provider`); there is no email/password path and no anonymous browsing beyond the Landing and "Find your syndicate" screens.

## Core features by screen

| Screen | Purpose | Backed by |
| --- | --- | --- |
| Landing | Hearth & Bench lockup, tonight's Hearthside Notes as teasers, Continue with Google / Apple | `POST /api/auth/session` (OIDC exchange — **not implemented**, returns 501) |
| Find your syndicate | Join by invite code, see circles you've been invited to, or start a new one | `GET /api/groups`, `POST /api/groups` (creating a syndicate is built; joining an existing one by invite code is **not** — see Open questions) |
| Matchday | Next Match hero, Hearthside Notes carousel, bench note threads, balance line | `GET /api/groups/{id}/fixtures`, `GET /api/groups/{id}/ledger`, `GET /api/bios/today` |
| The Pitch | Every home fixture in the season, filtered by All / My Matches / On the Bench | `GET /api/groups/{id}/fixtures`, `GET /api/fixtures/{id}/seats` |
| The Bench | Seats waiting for a sub, plus anything listed on an external resale exchange | `GET /api/groups/{id}/listings` |
| The Hearth | Package cost, weighted tier split, simplified debts, Settle Up, season history | `GET /api/groups/{id}/ledger`, `POST /api/groups/{id}/expenses`, `POST /api/groups/{id}/settle` |
| Home Team | Full squad roster with position filters, stats and scouting notes | `GET /api/roster` (frontend still renders from `web/build_src/data.py`, not wired yet) |
| Visitors | The visiting club's dressing room: dossiers, halftime reads, danger flags | `GET /api/opponents` (frontend still renders from `web/build_src/data.py`, not wired yet) |
| Campfire Settings | Push permissions, matchday alerts, Hearthside Notes mix, profile | `GET/PUT /api/preferences` |

### Seat handoff ("Call a Sub")

A seat holder who can't attend a fixture has three ways to give up their seat, all going through `PATCH /api/seats/{id}`:

1. **Release to the Bench** — posts a note to the circle with an explicit cost choice: *get paid back* at face value, or *on the house* at no cost. Status becomes `on_bench`.
2. **Send to Guest** — a direct gift to a named guest (`guest_name`); nobody's ledger balance moves. Status becomes `gifted`.
3. **List Outside the Hearth** — flags the seat as listed on an external exchange (SeatGeek/Ticketmaster) with a `resale_price_cents`. Status becomes `resale_listed`. This is a tracking flag only: SquadSeats has no API integration with any ticketing platform (SeatGeek, Ticketmaster, the club's own app, etc.) — the admin or seat holder must actually transfer or sell the ticket on that platform themselves, outside the app.

### Expense splitting

An expense (`POST /api/groups/{id}/expenses`) writes one `transactions` row per member owing a share (all sharing a `split_id` so the split can be shown or reversed as a unit); the payer owes nothing so gets no row. Splits are currently equal only — `split_equally` in `src/splits.py`. Weighting by fixture tier, and crediting members who release a seat to the bench, are named in `docs/backend.md` as decided-but-not-built.

## Functional requirements

1. **Authentication.** Sign in with Google or Apple; a session is a bearer token resolved server-side to a `users` row (`src/auth.py`). In development, `X-Dev-User` substitutes for the OIDC round trip. *Gap: the token exchange itself (`POST /api/auth/session`) is unbuilt — verifying the provider's ID token against its JWKS and writing a session into KV.*
2. **Syndicate management.** A member creates a syndicate (name, season, total seats, package cost) and becomes its admin (`POST /api/groups`). Each syndicate has its own roster, fixtures and ledger. *Gap: there is no API route for another member to join an existing syndicate at all — by invite code or otherwise; `group_members` is only ever written once, for the creator, at creation time.*
3. **Fixture & seat management.** An admin adds fixtures (opponent, kickoff time, venue, tier). Seats are created with the fixture and default to `confirmed`, assigned to each member's `default_seat_number`.
4. **Seat handoff.** A seat holder can release, gift, or externally list a seat they can't use (see Seat handoff above); every seat has exactly one current status (`confirmed`, `on_bench`, `gifted`, `resale_listed`).
5. **Bench liquidity.** Seats `on_bench` or `resale_listed` are surfaced via `GET /api/groups/{id}/listings` so another member can claim them before kickoff. A daily cron (10:00) finds seats still on the bench 3 days out for a nudge — *the nudge is logged, not delivered; push send is unbuilt.*
6. **Expense tracking & settlement.** Any member records an expense, split (currently equally) across the syndicate; the ledger (`GET /api/groups/{id}/ledger`) shows unsettled transactions, net balances per member, and a simplified settle-up plan. `POST /api/groups/{id}/settle` marks a member's debt settled.
7. **Player bios.** One scheduled bio per day (`player_bios.scheduled_date`), surfaced via `GET /api/bios/today`; a cron job (08:00) schedules the next unscheduled bio for today if none is set. `player_bios` rows are hand-entered today; see **Roster and fixture data sync** under Open questions for the planned automated source.
8. **Notification preferences.** Each member controls 3-day check-in alerts, bench alerts, and the scope of daily bios (home team only / Summit only / league-wide) via `GET/PUT /api/preferences`.
9. **Rosters (Home Team / Visitors).** `GET /api/roster` and `GET /api/opponents` (migration `0002_roster.sql`) back the squad and opposing-club dossiers, including per-player stats and scouting notes. The frontend does not call them yet — it still renders from placeholder data baked into the build (`web/build_src/data.py`).

### Known gaps between design and build

- No push notification delivery (only the underlying "who needs a nudge" logic).
- No integration with any external ticketing platform (SeatGeek, Ticketmaster, the club's own app) — "List Outside the Hearth" only tracks that a seat is listed; the admin or seat holder handles the actual transfer or sale themselves, outside SquadSeats.
- Frontend and backend are not yet integrated — the PWA ships with mock data compiled in at build time (`web/build_src/data.py`), even though every screen but Landing and OIDC now has a live endpoint behind it (fixtures, ledger, listings, bios, roster, opponents). Wiring it to the live API (build-time fetch for public data, runtime session-authenticated fetch for per-member data like balances and seat assignments) is the next major milestone.

## Non-functional requirements

### Platform & performance

- Mobile-first, responsive PWA: one layout from a 390px phone up to a 1180px centred desktop shell, no breakpoint switch. Installable (`manifest.webmanifest`, `sw.js` app-shell cache).
- No build step or framework on the frontend — a dependency-free Python static-site generator pre-renders every screen and interactive state into one `index.html`; `src/app.js` (~450 lines) only toggles visibility and handles the few genuinely dynamic inputs (free-text replies, dropped photos).
- Backend is a single Cloudflare Python Worker over D1 (data) and KV (sessions) — no separate services to coordinate.

### Accessibility

Tap targets ≥ 44px; toggles are `role="switch"` with `aria-checked`; the Hearthside Notes mix picker is a `radiogroup`; filter chips use a filled selected state rather than relying on `aria-selected` alone. Animation is dropped entirely under `prefers-reduced-motion`.

### Data & storage

- No object storage: player headshots and club crests are committed under `frontend/public/assets/images/` and served by Cloudflare Pages (`player_bios.image_path`), a deliberate choice to stay on Pages' free tier with no billing risk.
- Real per-syndicate/per-member data (balances, debts, seat assignments) must never be baked into the publicly-readable static build — it stays behind a runtime, session-authenticated fetch against the D1-backed API.

### Security

- Bearer-token sessions resolved to a user via `src/auth.py`; membership and admin checks gate write endpoints.
- Every pull request runs SAST (CodeQL, Semgrep, Gitleaks full-history secret scan, dependency review), a Terraform scan (dormant until `.tf` files exist), and a DAST baseline scan (ZAP, against a locally-served static build until a preview deployment exists) — see `docs/security-ci.md`.
- The Cloudflare API token used for deployment deliberately carries no zone/DNS permission.

### Deployment

- Deploys run through `.github/workflows/deploy.yml` on push to `main`, using the GitHub environment **"shb"** (holds `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`). The Worker deploys to Cloudflare Workers, the PWA to Cloudflare Pages, each independently detected and skipped if absent.
- All code changes land via pull request; nothing is pushed directly to `main`, and PRs require passing SAST/Terraform/DAST checks.
- Resource provisioning (D1, KV) is a separate manual workflow, `provision-cloudflare.yml`.

## Open questions & near-term scope

- **Frontend/backend wiring (feature next)** — no target date set; this is the largest remaining piece and touches every screen above.
- **OIDC sign-in** — which providers' JWKS endpoints, and token lifetime/refresh strategy, are undecided.
- **Push delivery** — the cron logic exists; the send mechanism (web push? provider?) is not chosen.
- **Weighted expense splits** — the formula for tier-weighted shares and bench-release credit is "still being decided" per `docs/backend.md`; `split_equally` is the only implementation today.
- **Roster/scouting data** — `GET /api/roster` and `GET /api/opponents` now back Home Team and Visitors with real tables (`roster_players`, `opponents`, `opponent_players`); the squad and dossiers seeded there are still the same invented names as the old frontend mock, not a real NWSL roster — see the data sync item below.
- **Roster and fixture data sync — built.** A weekly Worker cron (`0 5 * * 1`, `src/sync.py`) fetches Denver Summit's roster and schedule from nwslsoccer.com and player headshots from Wikipedia, matches them against `roster_players`, `fixtures` and `opponents`, and updates only what drifted; see **Roster/fixture/headshot sync** in `docs/backend.md` for how matching, licensing and image storage work. Chosen over a GitHub Actions workflow so the job stays behind the existing D1 binding instead of a second deployment path with its own credentials. Still open: `nwslsoccer.com`'s page markup is scraped via embedded JSON-LD, which is not a documented API and can change without notice — the sync logs and skips a job rather than failing loudly when that happens, so a markup change needs to be caught by watching the logs, not by an alert.
- **Joining a syndicate (invite codes and membership management)** — there is no API route at all for a member to join an existing syndicate, or for an admin to add, remove, or promote one; `group_members` is written to only once, for the creator, when `POST /api/groups` runs. "Find your syndicate" implies an invite-code mechanism, but its generation and redemption, plus general membership management, are both unbuilt.

This document reflects the repository as of 2026-09-21 (through PR #14, Cloudflare Pages provisioning). It should be revisited once the frontend/backend integration lands, since several "placeholder data" gaps above are expected to close then.
