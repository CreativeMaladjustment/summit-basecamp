import * as mock from './data/mock.js';

const KEY = 'shb.state.v1';

const initial = () => ({
  signedIn: false,
  // 'landing' | 'syndicate' | 'app'
  stage: 'landing',
  account: null,
  syndicateId: 'syn_north',
  seasonYear: 2026,
  tab: 'matchday',
  settingsOpen: false,
  fixtures: structuredClone(mock.fixtures),
  benchNotes: structuredClone(mock.benchNotes),
  photos: {},          // playerId -> data URL
  deviceState: 'auto', // 'auto' | 'ios-safari' | 'installed'
  prefs: {
    pushEnabled: false,
    checkin3Day: true,
    checkinTime: '10:00',
    benchAlerts: true,
    dailyBio: true,
    bioScope: 'home_first',
    bioTime: '08:00',
    displayName: 'You',
    phone: '',
    email: '',
  },
});

let state = load();
const listeners = new Set();

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return initial();
    return { ...initial(), ...JSON.parse(raw) };
  } catch {
    return initial();
  }
}

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* private mode, blocked storage — the app still works, it just forgets. */
  }
}

export function get() { return state; }

export function set(patch) {
  state = typeof patch === 'function' ? patch(state) : { ...state, ...patch };
  save();
  listeners.forEach((fn) => fn(state));
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function reset() {
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
  state = initial();
  listeners.forEach((fn) => fn(state));
}

// ---------- Selectors ----------

export const syndicate = () =>
  mock.syndicates.find((s) => s.id === state.syndicateId) ?? mock.syndicates[0];

export const seasonFixtures = () =>
  state.fixtures
    .filter((f) => f.season === state.seasonYear)
    .sort((a, b) => a.kickoff.localeCompare(b.kickoff));

export const nextFixture = () => {
  const now = new Date('2026-09-20T15:00:00');
  return seasonFixtures().find((f) => new Date(f.kickoff) > now) ?? seasonFixtures().at(-1);
};

export const isPast = (f) => new Date(f.kickoff) < new Date('2026-09-20T15:00:00');

/** Seats sitting on the bench or listed outside, across the season. */
export const openSeats = () =>
  seasonFixtures()
    .filter((f) => !isPast(f))
    .flatMap((f) =>
      f.seats
        .filter((s) => s.status === 'bench' || s.status === 'listed')
        .map((s) => ({ fixture: f, seat: s })),
    );

export const benchCount = () => openSeats().filter((o) => o.seat.status === 'bench').length;

export const noteFor = (fixtureId, seatNumber) =>
  state.benchNotes.find((n) => n.fixtureId === fixtureId && n.seatNumber === seatNumber);

export const ledgerFor = (year) => mock.ledger[year] ?? mock.ledger[2026];

/** Net position of the signed-in member: positive means the circle holds it. */
export const myBalanceCents = () => {
  const l = ledgerFor(state.seasonYear);
  return (l.paid[mock.me] ?? 0) - (l.owed[mock.me] ?? 0);
};

// ---------- Actions ----------

export function signIn(provider) {
  // The real Google/Apple OIDC redirect is the backend's job; this stands in
  // for the round trip so the signed-in views are reachable.
  set({ signedIn: true, stage: 'syndicate', account: { provider, name: 'You' } });
}

export function signOut() { reset(); }

export function chooseSyndicate(id) {
  set({ syndicateId: id, stage: 'app', tab: 'matchday' });
}

function patchSeat(fixtureId, seatNumber, patch) {
  set((s) => ({
    ...s,
    fixtures: s.fixtures.map((f) =>
      f.id !== fixtureId ? f : {
        ...f,
        seats: f.seats.map((seat) =>
          seat.number !== seatNumber ? seat : { ...seat, ...patch },
        ),
      },
    ),
  }));
}

/** Release to the Bench — posts a note thread with the chosen cost path. */
export function releaseToBench(fixtureId, seatNumber, { body, costPath, amountCents }) {
  const id = `bn_${Date.now()}`;
  set((s) => ({
    ...s,
    benchNotes: [
      {
        id, fixtureId, seatNumber,
        authorId: mock.me,
        postedAt: new Date().toISOString(),
        costPath, amountCents,
        body,
        replies: [],
      },
      ...s.benchNotes,
    ],
  }));
  patchSeat(fixtureId, seatNumber, { holder: null, status: 'bench', benchNoteId: id });
}

export function sendToGuest(fixtureId, seatNumber, guestName) {
  patchSeat(fixtureId, seatNumber, { holder: null, status: 'gifted', guestName });
}

export function listOutside(fixtureId, seatNumber, askCents) {
  patchSeat(fixtureId, seatNumber, { holder: null, status: 'listed', askCents });
}

/** Take the Pitch — claim an open seat. */
export function claimSeat(fixtureId, seatNumber, userId = mock.me) {
  patchSeat(fixtureId, seatNumber, { holder: userId, status: 'confirmed', guestName: null, askCents: null });
}

export function handOffTo(noteId, userId) {
  const note = state.benchNotes.find((n) => n.id === noteId);
  if (!note) return;
  claimSeat(note.fixtureId, note.seatNumber, userId);
}

export function addReply(noteId, body) {
  if (!body.trim()) return;
  set((s) => ({
    ...s,
    benchNotes: s.benchNotes.map((n) =>
      n.id !== noteId ? n : {
        ...n,
        replies: [...n.replies, { id: `r_${Date.now()}`, authorId: mock.me, at: new Date().toISOString(), body: body.trim() }],
      },
    ),
  }));
}

export function setPref(key, value) {
  set((s) => ({ ...s, prefs: { ...s.prefs, [key]: value } }));
}

export function setPhoto(playerId, dataUrl) {
  set((s) => ({ ...s, photos: { ...s.photos, [playerId]: dataUrl } }));
}
