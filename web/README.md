# Summit Hearth & Bench — PWA

The front end for the season-ticket syndicate app: the screens and flows from
the `SquadSeats.dc.html` design export, built for real.

## Running it

No build step and no dependencies. Serve the directory over HTTP:

```sh
cd web
python3 -m http.server 8788
# then open http://localhost:8788/
```

A plain `file://` open mostly works but skips the service worker, so prefer the
server. Deploying is a straight upload of this directory to Cloudflare Pages.

## What's here

| Screen | What it does |
| --- | --- |
| Landing | Hearth & Bench lockup, tonight's Hearthside Notes as teasers, Continue with Google / Apple |
| Find your syndicate | Invite code, the circles you've been invited to, or start a new one |
| Matchday | Next Match hero, Hearthside Notes carousel, bench note threads, balance line |
| The Pitch | Every home fixture in the season, filtered by All / My Matches / On the Bench |
| The Bench | Seats waiting for a sub and anything listed on an external exchange |
| The Hearth | Package cost, weighted tier split, simplified debts, Settle Up, season history |
| Home Team | Full squad with position filters, stats and scouting notes |
| Visitors | The visiting club's dressing room: dossiers, halftime reads, danger flags |
| Campfire Settings | Push permissions, matchday alerts, Hearthside Notes mix, profile |

Three ways a seat can leave your hands, from the **Call a Sub** sheet:

- **Release to the Bench** — posts a note to the circle with an explicit cost
  choice, either *get paid back* at face value or *on the house* at no cost.
- **Send to Guest** — a direct gift; nobody's tab moves.
- **List Outside the Hearth** — flags it for SeatGeek or Ticketmaster.

## Layout

One responsive layout rather than two builds. A 390px phone gets a single
column with horizontally scrolling tab rows and sheets docked to the bottom; it
reflows continuously up to a 1180px centred shell where sections become
`auto-fit` grids and sheets centre as modal cards. There is no breakpoint
switch.

## Structure

```
index.html            entry point
manifest.webmanifest  PWA manifest
sw.js                 app-shell cache
src/app.js            renders the current stage and tab
src/state.js          store, selectors and actions; persists to localStorage
src/data/mock.js      placeholder syndicate, fixture and roster data
src/components/       shared UI, header, Call a Sub sheet
src/views/            one module per screen
src/styles/           tokens, base, components
```

## Data and the backend

Everything the app shows comes from `src/data/mock.js`, held in `src/state.js`
and persisted to `localStorage`. Sign-in sets a flag rather than running the
real Google/Apple OIDC round trip. Player names, jersey numbers, stats and
fixture dates are invented placeholders — swap in the real roster and the
published fixture list when they exist, and point the club bio links at real
URLs.

Wiring this to the Cloudflare Workers + D1 backend means replacing the reads in
`src/state.js` selectors and the writes in its actions with API calls; the views
do not touch the data module directly.

## Colours

The Denver Summit FC palette, from the design export, lives in
`src/styles/tokens.css`:

| Token | Value | Used for |
| --- | --- | --- |
| Evergreen | `#134E48` / `#1D6960` | Primary surfaces, active nav, hero cards |
| Sandstone | `#C84B31` | Call a Sub, urgent alerts, unclaimed bench seats |
| Sunshine | `#F6BE00` | Badges, jersey numbers, the balance line |
| Snow | `#F8F7F2` | Light canvas |
| Forest dark | `#0A1413` | Dark canvas |

Light and dark come from `light-dark()` against `color-scheme`, so the app
follows the system setting with no toggle.

## Accessibility

Targets are at least 44px, toggles are `role="switch"` with `aria-checked`,
the mix picker is a `radiogroup`, and filter chips carry a filled selected
state rather than relying on `aria-selected` alone. The Visitors room's
dishevelment is cosmetic: tilts stay under 0.6°, nothing animates, and all
text sits on solid surfaces at full contrast. Animation is dropped entirely
under `prefers-reduced-motion`.
