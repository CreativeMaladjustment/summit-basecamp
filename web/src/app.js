// The entire runtime for a page Python already rendered. Every screen, every
// filter result, every toggle state and every Call-a-Sub sheet already
// exists in the DOM (see web/build_src/) — this file's job is to show and
// hide the right pre-rendered nodes and persist a little state, never to
// build HTML. The two exceptions, clearly marked below, are places nothing
// but the browser knows the content ahead of time: a typed reply and a
// dropped photo.

const KEY = 'shb.v2';

// The deployed Worker's own hostname -- see wrangler.jsonc's "name" comment
// for why a rename to it deploys a *new* Worker at a *new* hostname rather
// than relabeling this one. Update this by hand if that ever happens, the
// same manual step docs/deploy.md already asks for on CF_API_BASE_URL.
const API_BASE = 'https://summit-basecamp-api.shb-fe7.workers.dev';

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function save(state) {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* private mode */ }
}

const state = Object.assign({
  stage: 'landing',        // landing | syndicate | app
  tab: 'matchday',
  season: '2026',
  syndicateName: null,      // set once "Start a new syndicate" or "Join with code" succeeds
  groupId: null,             // the real POST /api/groups(/join) id behind syndicateName
  section: null,              // the syndicate's real section, e.g. "114"
  seatRow: null,               // the syndicate's real row, e.g. "8"
  mySeatLabel: null,           // this member's own real seat number, e.g. "3"
  prefs: { checkin3Day: true, benchAlerts: true, dailyBio: true, bioScope: 'home_first', pushEnabled: false },
  photos: {},                // playerId -> data URL, restored on load
  sessionToken: null,        // bearer token from POST /api/auth/session
  user: null,                // the full users row for the signed-in guest slot
}, load());

function persist() { save(state); }

// ---------- Stage / tab / season: pure visibility toggles ----------

function showStage(next) {
  state.stage = next;
  for (const id of ['stage-landing', 'stage-syndicate', 'stage-app']) {
    document.getElementById(id).hidden = id !== `stage-${next}`;
  }
  persist();
}

function showTab(tab) {
  state.tab = tab;
  for (const section of document.querySelectorAll('[data-tab]')) {
    section.hidden = section.dataset.tab !== tab;
  }
  for (const chip of document.querySelectorAll('[data-role="tab"]')) {
    chip.setAttribute('aria-selected', String(chip.dataset.value === tab));
  }
  // The season selector only affects the Hearth ledger — Matchday, Pitch and
  // Bench are pre-rendered for the current season only — so show it only
  // where it actually does something, rather than implying it switches the
  // whole app.
  const seasonRow = document.getElementById('season-row');
  if (seasonRow) seasonRow.hidden = tab !== 'hearth';
  window.scrollTo(0, 0);
  persist();
}

function showSeason(year) {
  state.season = year;
  for (const chip of document.querySelectorAll('[data-role="season"]')) {
    chip.setAttribute('aria-selected', String(chip.dataset.value === year));
  }
  for (const block of document.querySelectorAll('[data-season-block]')) {
    block.hidden = block.dataset.seasonBlock !== year;
  }
  persist();
}

// ---------- Sheets ----------

let openSheetId = null;

function openSheet(id) {
  closeSheet();
  const el = document.getElementById(id);
  if (!el) return;
  el.hidden = false;
  document.body.style.overflow = 'hidden';
  openSheetId = id;
}

function closeSheet() {
  if (!openSheetId) return;
  const el = document.getElementById(openSheetId);
  if (el) el.hidden = true;
  document.body.style.overflow = '';
  openSheetId = null;
}

function moneyCents(cents) {
  const dollars = cents / 100;
  return cents % 100 === 0 ? `$${dollars.toLocaleString('en-US')}` : `$${dollars.toFixed(2)}`;
}

// ---------- Photo drop: the other irreducible spot ----------

function readPhoto(file, onDone) {
  if (!file || !file.type.startsWith('image/')) return;
  const reader = new FileReader();
  reader.onload = () => onDone(reader.result);
  reader.readAsDataURL(file);
}

function wirePhotoSlots() {
  for (const slot of document.querySelectorAll('[data-photo-slot]')) {
    const playerId = slot.dataset.photoSlot;
    const paint = (url) => {
      slot.textContent = '';
      const img = document.createElement('img');
      img.src = url;
      img.alt = '';
      slot.append(img);
    };
    if (state.photos[playerId]) paint(state.photos[playerId]);

    slot.addEventListener('dragover', (e) => { e.preventDefault(); slot.classList.add('is-over'); });
    slot.addEventListener('dragleave', () => slot.classList.remove('is-over'));
    slot.addEventListener('drop', (e) => {
      e.preventDefault();
      slot.classList.remove('is-over');
      readPhoto(e.dataTransfer?.files?.[0], (url) => { state.photos[playerId] = url; persist(); paint(url); });
    });
    const pick = () => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.style.display = 'none';
      input.addEventListener('change', () => readPhoto(input.files[0], (url) => { state.photos[playerId] = url; persist(); paint(url); }));
      document.body.append(input);
      input.click();
      input.remove();
    };
    slot.addEventListener('click', pick);
    slot.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
  }
}

// ---------- Sign-in: shared-password gate over six fixed guest slots ------

// What a device remembers instead of the site password itself, once
// POST /api/auth/session has verified that password at least once -- an
// opaque, server-issued, independently revocable token (src/auth.py's
// start_device_trust), not the literal shared secret sitting in this
// browser's own storage for any script on the page to read. Kept separate
// from DEVICE_KEY -- shb.v2 (the state persisted under KEY) is wiped
// wholesale on sign-out, but this device's trust isn't tied to any one
// guest slot, so it should still skip straight to picking a user next time
// even after someone signs out.
const DEVICE_KEY = 'shb.device';

function loadDeviceToken() {
  try { return localStorage.getItem(DEVICE_KEY); } catch { return null; }
}

function saveDeviceToken(token) {
  try { localStorage.setItem(DEVICE_KEY, token); } catch { /* private mode */ }
}

function forgetDeviceToken() {
  try { localStorage.removeItem(DEVICE_KEY); } catch { /* private mode */ }
}

// Hides the password field entirely once this device is already trusted,
// so returning just means picking a guest slot.
function paintPasswordField() {
  const field = document.getElementById('password-field');
  if (field) field.hidden = !!loadDeviceToken();
}

// Static "Guest N" labels are what the build renders; this repaints them
// with whatever PATCH /api/me has since set each slot's name to, so a
// returning visitor sees real names rather than the placeholder ones.
async function loadGuestSlots() {
  const container = document.getElementById('guest-slots');
  if (!container) return;
  let guests;
  try {
    const res = await fetch(`${API_BASE}/api/auth/guests`);
    if (!res.ok) return;
    ({ guests } = await res.json());
  } catch {
    return; // offline -- the static "Guest N" labels stand in
  }
  for (const guest of guests) {
    const btn = container.querySelector(`[data-guest-id="${CSS.escape(guest.id)}"]`);
    if (btn) btn.textContent = guest.name;
  }
}

async function signIn(guestId) {
  const passwordInput = document.getElementById('site-password');
  const errorEl = document.getElementById('sign-in-error');
  const deviceToken = loadDeviceToken();
  if (errorEl) errorEl.hidden = true;

  let requestBody;
  if (deviceToken) {
    requestBody = { user_id: guestId, device_token: deviceToken };
  } else {
    const password = passwordInput ? passwordInput.value : '';
    if (!password) {
      if (errorEl) { errorEl.textContent = 'Enter the site password first.'; errorEl.hidden = false; }
      passwordInput?.focus();
      return;
    }
    requestBody = { user_id: guestId, password };
  }

  let res;
  try {
    res = await fetch(`${API_BASE}/api/auth/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });
  } catch {
    if (errorEl) { errorEl.textContent = 'Could not reach the server -- check your connection.'; errorEl.hidden = false; }
    return;
  }
  if (!res.ok) {
    // A remembered device token that no longer works (e.g. its 30 days ran
    // out) would otherwise fail silently on every future click -- forget
    // it and fall back to asking for the password again.
    if (deviceToken) {
      forgetDeviceToken();
      paintPasswordField();
    }
    const body = await res.json().catch(() => ({}));
    if (errorEl) { errorEl.textContent = body.error || 'Wrong password.'; errorEl.hidden = false; }
    return;
  }

  const { token, user, device_token: newDeviceToken } = await res.json();
  if (newDeviceToken) saveDeviceToken(newDeviceToken);
  state.sessionToken = token;
  state.user = user; // full row -- id, name, phone, contact_email, ...
  persist();

  // Whoever this guest slot really is (see update_me / migration 0010) may
  // already be a real member of a syndicate someone else set up -- ask the
  // backend rather than always dropping them on create/join. One match
  // skips this screen entirely; more than one lists them to pick from;
  // none, or the request failing, falls back to today's create/join screen.
  let groups = [];
  let groupsCheckFailed = false;
  try {
    const groupsRes = await fetch(`${API_BASE}/api/groups`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (groupsRes.ok) ({ groups } = await groupsRes.json());
    else groupsCheckFailed = true;
  } catch {
    groupsCheckFailed = true; // offline or unreachable -- fall through to create/join
  }

  if (groups.length === 1) {
    settleIntoSyndicate(groups[0], groups[0].seat_label || null);
    return;
  }
  showStage('syndicate');
  paintMySyndicates(groups);
  // Landing here with no syndicate listed looks identical whether someone
  // really has none yet or the membership check above just failed -- make
  // that distinction visible instead of silently falling back either way.
  const checkErrorEl = document.getElementById('syndicate-check-error');
  if (checkErrorEl) checkErrorEl.hidden = !groupsCheckFailed;
}

// ---------- Find your syndicate: join or create for real ----------

let myGroupsCache = [];

// Fills in the "Your syndicates" picker on the Find-your-syndicate screen
// with whatever GET /api/groups just returned -- only reached (see signIn)
// when that's 2+ real memberships, since exactly one skips this screen and
// settles straight into it instead.
function paintMySyndicates(groups) {
  myGroupsCache = groups;
  const container = document.getElementById('my-syndicates');
  const list = document.getElementById('my-syndicate-list');
  if (!container || !list) return;
  list.innerHTML = '';
  for (const group of groups) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn--primary btn--block';
    btn.dataset.role = 'select-syndicate';
    btn.dataset.groupId = group.id;
    btn.textContent = group.name;
    list.appendChild(btn);
  }
  container.hidden = groups.length === 0;
}

// Shared by both a successful join and a successful create -- the group
// this device is now "in". The 14ers ledger and this header's "N seats ·
// Sec/Row" readout are real, painted from the API by paintRealSyndicateDetail
// below; Matchday/Pitch/Bench still render fixed mock fixtures regardless of
// which real group this is -- see new_syndicate_sheet()'s own copy.
// mySeatLabel is only ever known at creation time (join has no seat-picking
// step yet), so it defaults to null here -- explicitly resetting it on every
// call rather than leaving a previous syndicate's seat label stuck around
// after joining a different one with none of its own.
function settleIntoSyndicate(group, mySeatLabel = null) {
  state.groupId = group.id;
  state.syndicateName = group.name;
  state.section = group.section || null;
  state.seatRow = group.seat_row || null;
  state.mySeatLabel = mySeatLabel;
  paintSyndicateName();
  paintSeatAssignment();
  persist();
  closeSheet();
  showStage('app');
  showTab('matchday');
  paintRealSyndicateDetail();
  paintRealFixtures();
}

function balanceLineText(cents) {
  if (cents === 0) return 'All square with the 14ers.';
  return cents > 0 ? `The circle holds your ${moneyCents(cents)}.` : `You hold the tab (${moneyCents(Math.abs(cents))}).`;
}

// One retry after a short pause, for a fetch whose failure would otherwise
// leave a *different*, fabricated-looking syndicate's demo numbers on
// screen indefinitely (see paintRealSyndicateDetail below) -- worth a
// second try before accepting that, since the most common real-world cause
// is a single dropped request, not a real outage.
async function fetchWithOneRetry(url, options) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const res = await fetch(url, options);
      if (res.ok) return res;
    } catch {
      // fall through to retry/give up below
    }
    if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 1200));
  }
  return null;
}

// Overwrites the 14ers ledger card and the header's "N seats · Sec/Row"
// readout -- both pre-rendered with invented demo numbers (web/build_src/
// data.py) -- with this syndicate's real GET /api/groups/{id} and
// .../ledger data: real price, real seat/member counts, and real per-member
// balances (net_balances/settle_plan; an evenly-split expense ledger, no
// tier weighting) instead of the mock weighted-by-tier breakdown. A no-op
// until there is a real syndicate and session to ask about. The group
// fetch gets one retry (fetchWithOneRetry) before giving up, since failing
// silently here doesn't just leave stale numbers on screen -- it leaves a
// *different*, wrong-looking syndicate's invented name and seat count
// displayed as if real, with nothing to say otherwise.
async function paintRealSyndicateDetail() {
  if (!state.groupId || !state.sessionToken) return;
  const authHeaders = { Authorization: `Bearer ${state.sessionToken}` };

  let group, members;
  const groupRes = await fetchWithOneRetry(`${API_BASE}/api/groups/${state.groupId}`, { headers: authHeaders });
  if (!groupRes) return;
  try {
    ({ group, members } = await groupRes.json());
  } catch {
    return;
  }

  let balances = {};
  let settlePlan = [];
  try {
    const ledgerRes = await fetch(`${API_BASE}/api/groups/${state.groupId}/ledger`, { headers: authHeaders });
    if (ledgerRes.ok) ({ balances, settle_plan: settlePlan } = await ledgerRes.json());
  } catch {
    // Leave balances/settlePlan empty -- everyone reads as square rather
    // than blocking the rest of this real data (group/members) from showing.
  }

  const holdsEl = document.getElementById('syndicate-holds');
  if (holdsEl) {
    const seatBits = [];
    if (group.section) seatBits.push(`Sec ${group.section}`);
    if (group.seat_row) seatBits.push(`Row ${group.seat_row}`);
    const seatWord = group.total_seats === 1 ? 'seat' : 'seats';
    holdsEl.textContent = `— ${group.total_seats} ${seatWord}` + (seatBits.length ? ` · ${seatBits.join(', ')}` : '');
  }

  // Real season chip/block -- there is exactly one, since a syndicate is a
  // single season's package with no year-over-year link to any other one.
  const year = String(group.season_year);
  state.season = year;
  const seasonChip = document.querySelector('[data-role="season"]');
  if (seasonChip) {
    seasonChip.textContent = `${year} Season`;
    seasonChip.dataset.value = year;
  }
  const seasonBlock = document.querySelector('[data-season-block]');
  if (seasonBlock) seasonBlock.dataset.seasonBlock = year;
  showSeason(year);

  const yearLabelEl = document.getElementById('ledger-package-year');
  if (yearLabelEl) yearLabelEl.textContent = `${year} package`;
  const priceEl = document.getElementById('ledger-package-price');
  if (priceEl) priceEl.textContent = moneyCents(group.package_cost_cents);
  const circleEl = document.getElementById('ledger-package-circle');
  if (circleEl) {
    const seatWord = group.total_seats === 1 ? 'seat' : 'seats';
    circleEl.textContent = `${group.total_seats} ${seatWord} · ${members.length} in the circle`;
  }
  // No real fixture is tied to a tier/cost yet (Matchday/Pitch are still the
  // demo schedule) -- nothing to weight, so this replaces the mock bars
  // rather than showing them against invented fixtures.
  const tiersEl = document.getElementById('ledger-package-tiers');
  if (tiersEl) {
    tiersEl.innerHTML = '';
    const note = document.createElement('p');
    note.style.cssText = 'margin:0;font-size:13px;color:var(--ink-mute)';
    note.textContent = 'No fixtures logged yet.';
    tiersEl.appendChild(note);
  }

  const debtsRowsEl = document.getElementById('ledger-debts-rows');
  const squaredListEl = document.getElementById('ledger-squared-list');
  if (debtsRowsEl && squaredListEl) {
    debtsRowsEl.innerHTML = '';
    squaredListEl.innerHTML = '';
    const membersById = Object.fromEntries(members.map((m) => [m.id, m]));
    if (settlePlan.length) {
      for (const transfer of settlePlan) {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--hairline)';
        const av = document.createElement('div');
        av.className = 'avatar';
        av.style.background = '#134E48';
        av.textContent = initials(membersById[transfer.from]?.name);
        const p = document.createElement('p');
        p.style.cssText = 'margin:0;flex:1;font-size:14px';
        const fromStrong = document.createElement('strong');
        fromStrong.textContent = membersById[transfer.from]?.name ?? 'Someone';
        const toStrong = document.createElement('strong');
        toStrong.textContent = membersById[transfer.to]?.name ?? 'someone';
        p.append(fromStrong, ' owes ', toStrong);
        const amount = document.createElement('span');
        amount.style.cssText = 'font-family:var(--font-mono);font-weight:500';
        amount.textContent = moneyCents(transfer.amount_cents);
        row.append(av, p, amount);
        debtsRowsEl.appendChild(row);
      }
    } else {
      const p = document.createElement('p');
      p.style.cssText = 'margin:0;font-size:14px;color:var(--ink-mute)';
      p.textContent = 'All square.';
      debtsRowsEl.appendChild(p);
    }
    const inSettlePlan = new Set(settlePlan.flatMap((t) => [t.from, t.to]));
    for (const member of members) {
      if (inSettlePlan.has(member.id)) continue;
      const p = document.createElement('p');
      p.style.cssText = 'margin:0 0 6px;font-size:14px;color:var(--ink-mute)';
      p.textContent = `${member.name} is all square.`;
      squaredListEl.appendChild(p);
    }
  }

  const myCents = balances[state.user?.id] || 0;
  const balanceLineEl = document.getElementById('ledger-balance-line');
  if (balanceLineEl) {
    const textEl = balanceLineEl.querySelector('[data-role="balance-text"]');
    if (textEl) textEl.textContent = balanceLineText(myCents);
    const settleBtn = balanceLineEl.querySelector('[data-open-sheet="sheet-settleup"]');
    if (settleBtn) {
      settleBtn.hidden = myCents === 0;
      settleBtn.dataset.settleAmount = String(Math.abs(myCents));
      settleBtn.dataset.settleOwed = myCents > 0 ? 'true' : 'false';
    }
  }
  // Matchday's own shorter link-to-Hearth strip -- same real balance, a
  // second real DOM node (layout-only difference, see matchday.py).
  const matchdayStrip = document.getElementById('matchday-balance-strip');
  if (matchdayStrip) {
    const textEl = matchdayStrip.querySelector('[data-role="matchday-balance-text"]');
    if (textEl) textEl.textContent = balanceLineText(myCents);
    matchdayStrip.hidden = false;
  }

  const historyEl = document.getElementById('ledger-history-rows');
  if (historyEl) {
    historyEl.innerHTML = '';
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'setting-row';
    row.dataset.role = 'season';
    row.dataset.value = year;
    row.style.cssText = 'width:100%;text-align:left;align-items:center;background:none;border:none;'
      + 'border-bottom:1px solid var(--hairline);cursor:pointer;font:inherit;color:inherit';
    const body = document.createElement('div');
    body.className = 'setting-row__body';
    const label = document.createElement('p');
    label.className = 'setting-row__label';
    label.textContent = `${year} Season`;
    const help = document.createElement('p');
    help.className = 'setting-row__help';
    help.textContent = settlePlan.length ? `${settlePlan.length} open transfer${settlePlan.length > 1 ? 's' : ''}` : 'Settled';
    body.append(label, help);
    const amount = document.createElement('span');
    amount.style.cssText = 'font-family:var(--font-mono);font-size:14px';
    amount.textContent = moneyCents(group.package_cost_cents);
    row.append(body, amount);
    historyEl.appendChild(row);
  }
}

// "Jason Miller" -> "JM"; a lone name -> its first two letters. Same shape
// as the mock MEMBERS dict's hand-picked initials, computed instead of
// invented since a real member's name is whatever they set it to.
function initials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return parts.length > 1
    ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

// ---------- Matchday / Pitch / Bench: a syndicate's real fixtures, seats
// and bench notes. Which fixtures exist and who holds which seat is real
// per-syndicate data that doesn't exist at build time, so -- unlike the
// rest of this static site -- these three screens are built here from the
// API rather than pre-rendered and just toggled. ----------

const QUICK_REPLIES = ["I'll take them", "We'll miss you", "Anyone else in?"];

let realFixturesCache = [];   // [{fixture, seats}], sorted by kickoff
let realBenchNotesCache = []; // [{...note, replies}], newest first
let callASubTarget = null;    // {allocationId, fixtureId, seatNumber, faceCents}

function matchDateLabel(iso) {
  const d = new Date(iso);
  return `${d.toLocaleDateString('en-US', { weekday: 'short' })}, ${d.toLocaleDateString('en-US', { month: 'short' })} ${d.getDate()}`;
}

function matchTimeLabel(iso) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

// D1's CURRENT_TIMESTAMP is UTC, space-separated ("2026-09-23 02:20:00")
// with no zone marker -- new Date() on that string is parsed as *local*
// time by most engines, which would skew every relative time by whatever
// this browser's UTC offset is. Coerced into an unambiguous UTC ISO string
// first. Fixture kickoff times, by contrast, are wall-clock local venue
// times a caller supplies directly (like the rest of this app's dates), so
// they're parsed as-is everywhere else.
function parseSqliteUtc(s) {
  if (!s) return new Date(NaN);
  const iso = s.includes('T') ? s : s.replace(' ', 'T');
  return new Date(iso.endsWith('Z') ? iso : iso + 'Z');
}

function relativeTime(iso) {
  const mins = Math.round((Date.now() - parseSqliteUtc(iso).getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function avatarEl(label, empty) {
  const av = document.createElement('div');
  av.className = empty ? 'avatar avatar--empty' : 'avatar';
  if (!empty) av.style.background = '#134E48';
  av.title = label;
  av.setAttribute('aria-label', label);
  av.textContent = empty ? '+' : initials(label);
  return av;
}

// Status decides the label first -- update_seat deliberately keeps
// assigned_user_id pointing at the original holder for a gifted or
// resale-listed seat (they're still the authorized actor for it), so
// checking assigned_user_id before status would show the donor's own name
// instead of the guest they gifted it to, or "Listed outside" for a seat
// they've listed but not actually vacated.
function seatHolderLabel(seat) {
  if (seat.status === 'gifted') return seat.guest_name || 'Guest';
  if (seat.status === 'resale_listed') return 'Listed outside';
  if (seat.status === 'on_bench') return 'On the bench';
  if (seat.assigned_user_id) return seat.assigned_user_name || 'Member';
  return 'Open';
}

// Same status-first reasoning as seatHolderLabel -- a resale-listed seat
// still carries its original holder's assigned_user_id, but visually reads
// as an open (dashed) avatar, same as on_bench, not a solid one implying
// the lister still occupies it.
function seatIsEmpty(seat) {
  if (seat.status === 'resale_listed' || seat.status === 'on_bench') return true;
  return !seat.assigned_user_id && !seat.guest_name;
}

function seatLineEl(seat, onDark) {
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;align-items:center;gap:8px';
  const label = seatHolderLabel(seat);
  wrap.appendChild(avatarEl(label, seatIsEmpty(seat)));
  const meta = document.createElement('div');
  const nameP = document.createElement('p');
  nameP.style.cssText = `margin:0;font-size:13px;font-weight:600;${onDark ? 'color:#fff' : ''}`;
  nameP.textContent = label;
  const seatP = document.createElement('p');
  seatP.style.cssText = `margin:0;font-size:11px;font-family:var(--font-mono);${onDark ? 'color:rgba(255,255,255,.62)' : 'color:var(--ink-mute)'}`;
  seatP.textContent = `Seat ${seat.seat_number}`;
  meta.append(nameP, seatP);
  wrap.appendChild(meta);
  return wrap;
}

async function paintRealFixtures() {
  if (!state.groupId || !state.sessionToken) return;
  const authHeaders = { Authorization: `Bearer ${state.sessionToken}` };

  let fixtures = [];
  try {
    const res = await fetch(`${API_BASE}/api/groups/${state.groupId}/fixtures`, { headers: authHeaders });
    if (!res.ok) return;
    ({ fixtures } = await res.json());
  } catch {
    return; // offline -- leave whatever was last painted (or the loading placeholder) as-is
  }

  const withSeats = await Promise.all(fixtures.map(async (fixture) => {
    try {
      const res = await fetch(`${API_BASE}/api/fixtures/${fixture.id}/seats`, { headers: authHeaders });
      const body = res.ok ? await res.json() : null;
      return { fixture, seats: body ? body.seats : [] };
    } catch {
      return { fixture, seats: [] };
    }
  }));
  withSeats.sort((a, b) => a.fixture.kickoff_at.localeCompare(b.fixture.kickoff_at));
  realFixturesCache = withSeats;

  let notes = [];
  try {
    const res = await fetch(`${API_BASE}/api/groups/${state.groupId}/bench-notes`, { headers: authHeaders });
    if (res.ok) ({ notes } = await res.json());
  } catch {
    // leave notes empty -- bench cards and the Matchday section just show without one
  }
  realBenchNotesCache = notes;

  paintMatchdayHero();
  paintPitchRows();
  paintBenchLists();
  paintBenchNotesSection();
  paintBenchCountBadge();
}

// Matches the backend's own list_listings filter (src/handlers.py) -- a
// seat still on_bench/resale_listed for a fixture whose kickoff has already
// passed isn't really "going spare" for anyone to claim, so it's excluded
// from the count and from Bench's own lists the same way the real listings
// endpoint would exclude it.
function isUpcoming(fixture) {
  return new Date(fixture.kickoff_at) >= new Date();
}

function paintBenchCountBadge() {
  const count = realFixturesCache
    .filter(({ fixture }) => isUpcoming(fixture))
    .reduce((n, { seats }) => n + seats.filter((s) => s.status === 'on_bench' || s.status === 'resale_listed').length, 0);
  for (const el of document.querySelectorAll('[data-bench-count]')) {
    el.textContent = String(count);
    el.hidden = count === 0;
    el.closest('button')?.classList.toggle('is-empty', count === 0);
  }
  const bell = document.querySelector('[data-role="goto-bench"]');
  if (bell) bell.setAttribute('aria-label', count ? `${count} seats need attention` : 'No pending requests');
}

function nextFixtureEntry() {
  // realFixturesCache is sorted by kickoff ascending -- with no fixture
  // still ahead of kickoff, the last (most recent) one stands in rather
  // than showing nothing, same call the old build-time mock made.
  const now = new Date();
  const upcoming = realFixturesCache.filter(({ fixture }) => new Date(fixture.kickoff_at) >= now);
  if (upcoming.length) return upcoming[0];
  return realFixturesCache.length ? realFixturesCache[realFixturesCache.length - 1] : null;
}

function paintMatchdayHero() {
  const hero = document.getElementById('matchday-hero');
  if (!hero) return;
  const entry = nextFixtureEntry();
  hero.innerHTML = '';
  if (!entry) {
    hero.className = 'card';
    hero.removeAttribute('style');
    const p = document.createElement('p');
    p.style.cssText = 'margin:0;color:var(--ink-mute)';
    p.textContent = 'No fixtures logged for this syndicate yet.';
    hero.appendChild(p);
    return;
  }
  const { fixture, seats } = entry;
  hero.className = '';
  hero.style.cssText = 'border-radius:var(--radius-lg);overflow:hidden;background:#134E48;color:#fff;'
    + 'border-top:3px solid #C84B31;padding:18px 16px;animation:ssUp .3s ease both';

  const topRow = document.createElement('div');
  topRow.style.cssText = 'display:flex;justify-content:space-between;gap:10px;align-items:flex-start';
  const left = document.createElement('div');
  const eyebrow = document.createElement('p');
  eyebrow.className = 'eyebrow';
  eyebrow.style.color = 'rgba(255,255,255,.66)';
  eyebrow.textContent = 'Next match';
  const title = document.createElement('h2');
  title.style.cssText = 'font-size:24px;font-weight:800;margin-top:4px;color:#fff';
  title.textContent = `Summit vs ${fixture.opponent}`;
  const sub = document.createElement('p');
  sub.style.cssText = 'margin:6px 0 0;font-size:14px;color:rgba(255,255,255,.8)';
  sub.textContent = `${matchDateLabel(fixture.kickoff_at)} · ${matchTimeLabel(fixture.kickoff_at)} · ${fixture.venue}`;
  left.append(eyebrow, title, sub);
  topRow.appendChild(left);
  if (fixture.tier === 'rivalry') {
    const badgeEl = document.createElement('span');
    badgeEl.className = 'badge badge--gold';
    badgeEl.textContent = 'Rivalry';
    topRow.appendChild(badgeEl);
  }
  hero.appendChild(topRow);

  const rosterLabel = document.createElement('p');
  rosterLabel.className = 'eyebrow';
  rosterLabel.style.cssText = 'color:rgba(255,255,255,.66);margin-top:16px';
  rosterLabel.textContent = 'Taking the pitch';
  hero.appendChild(rosterLabel);

  const roster = document.createElement('div');
  roster.style.cssText = 'display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:14px';
  for (const seat of seats) roster.appendChild(seatLineEl(seat, true));
  hero.appendChild(roster);

  const actions = document.createElement('div');
  actions.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;margin-top:16px';
  // status === 'confirmed' -- a gifted or resale-listed seat still carries
  // my assigned_user_id (see seatHolderLabel above), but it's already left
  // my hands; Call a Sub has nothing left to do with it.
  const mySeat = seats.find((s) => s.assigned_user_id === state.user?.id && s.status === 'confirmed');
  if (mySeat) {
    const btn = document.createElement('button');
    btn.className = 'btn btn--ember';
    btn.type = 'button';
    btn.dataset.callASub = mySeat.id;
    btn.dataset.openSheet = 'sheet-callasub';
    btn.textContent = 'Call a Sub';
    actions.appendChild(btn);
  }
  const ticketLink = document.createElement('a');
  ticketLink.className = 'btn btn--on-dark';
  ticketLink.href = 'https://www.ticketmaster.com/';
  ticketLink.target = '_blank';
  ticketLink.rel = 'noopener noreferrer';
  ticketLink.textContent = 'Open Official Ticketing App';
  actions.appendChild(ticketLink);
  hero.appendChild(actions);
}

function pitchStatusPill(seats) {
  const bench = seats.filter((s) => s.status === 'on_bench');
  const listed = seats.filter((s) => s.status === 'resale_listed');
  const span = document.createElement('span');
  if (bench.length) {
    span.className = 'badge badge--ember';
    span.textContent = `${bench.length} seat${bench.length > 1 ? 's' : ''} on the bench`;
    return span;
  }
  if (listed.length) {
    span.className = 'badge badge--ember';
    span.textContent = 'Listed outside';
    return span;
  }
  // Only 'confirmed' or 'gifted' seats can reach here (bench/listed already
  // returned above) -- seatHolderLabel gives the gifted guest's own name
  // rather than the donor's, same reasoning as everywhere else it's used.
  const names = seats.filter((s) => s.assigned_user_id || s.guest_name)
    .map((s) => seatHolderLabel(s)).join(' & ');
  span.className = 'badge badge--green';
  span.textContent = names ? `Starting · ${names}` : 'Starting';
  return span;
}

function pitchRowEl(fixture, seats) {
  // status === 'confirmed' -- same reasoning as the Matchday hero's own
  // mySeat check: a gifted or resale-listed seat still carries my
  // assigned_user_id, but it's already left my hands.
  const mySeat = seats.find((s) => s.assigned_user_id === state.user?.id && s.status === 'confirmed');
  const isBench = seats.some((s) => s.status === 'on_bench' || s.status === 'resale_listed');

  const row = document.createElement('article');
  row.className = 'card';
  row.dataset.fixtureRow = fixture.id;
  row.dataset.mine = String(!!mySeat);
  row.dataset.bench = String(isBench);

  const top = document.createElement('div');
  top.style.cssText = 'display:flex;justify-content:space-between;gap:10px;align-items:flex-start';
  const left = document.createElement('div');
  const eyebrow = document.createElement('p');
  eyebrow.className = 'eyebrow';
  eyebrow.textContent = `${matchDateLabel(fixture.kickoff_at)} · ${matchTimeLabel(fixture.kickoff_at)}`;
  const title = document.createElement('p');
  title.style.cssText = 'margin:4px 0 0;font-family:var(--font-display);font-weight:700;font-size:17px';
  title.textContent = `vs ${fixture.opponent}`;
  const venue = document.createElement('p');
  venue.style.cssText = 'margin:2px 0 0;font-size:13px;color:var(--ink-mute)';
  venue.textContent = fixture.venue;
  left.append(eyebrow, title, venue);
  top.appendChild(left);
  const tierBadge = document.createElement('span');
  const tierLabel = fixture.tier ? fixture.tier[0].toUpperCase() + fixture.tier.slice(1) : 'Standard';
  tierBadge.className = fixture.tier === 'rivalry' ? 'badge badge--gold' : 'badge badge--mute';
  tierBadge.textContent = tierLabel;
  top.appendChild(tierBadge);
  row.appendChild(top);

  const statusRow = document.createElement('div');
  statusRow.style.cssText = 'display:flex;align-items:center;gap:8px;margin-top:12px;flex-wrap:wrap';
  for (const seat of seats) statusRow.appendChild(avatarEl(seatHolderLabel(seat), seatIsEmpty(seat)));
  statusRow.appendChild(pitchStatusPill(seats));
  row.appendChild(statusRow);

  const actions = document.createElement('div');
  actions.style.cssText = 'display:flex;gap:8px;margin-top:12px;flex-wrap:wrap';
  let hasAction = false;
  if (mySeat) {
    hasAction = true;
    const btn = document.createElement('button');
    btn.className = 'btn btn--ghost';
    btn.type = 'button';
    btn.dataset.callASub = mySeat.id;
    btn.dataset.openSheet = 'sheet-callasub';
    btn.textContent = 'Call a Sub';
    actions.appendChild(btn);
  }
  const openSeat = seats.find((s) => s.status === 'on_bench');
  if (openSeat) {
    hasAction = true;
    const btn = document.createElement('button');
    btn.className = 'btn btn--primary';
    btn.type = 'button';
    btn.dataset.claimSeat = openSeat.id;
    btn.textContent = 'Take the Pitch';
    actions.appendChild(btn);
  }
  if (hasAction) row.appendChild(actions);

  return row;
}

function applyPitchFilter() {
  const active = document.querySelector('[data-role="pitch-filter"][aria-selected="true"]');
  const v = active ? active.dataset.value : 'all';
  let visible = 0;
  document.querySelectorAll('[data-fixture-row]').forEach((row) => {
    const show = v === 'all' || (v === 'mine' && row.dataset.mine === 'true') || (v === 'bench' && row.dataset.bench === 'true');
    row.hidden = !show;
    if (show) visible += 1;
  });
  const empty = document.getElementById('pitch-empty');
  if (empty) {
    empty.textContent = realFixturesCache.length
      ? 'Nothing here for this filter.'
      : 'No fixtures logged for this syndicate yet.';
    empty.hidden = visible > 0;
  }
}

function paintPitchRows() {
  const container = document.getElementById('pitch-rows');
  if (!container) return;
  container.innerHTML = '';
  for (const { fixture, seats } of realFixturesCache) container.appendChild(pitchRowEl(fixture, seats));
  applyPitchFilter();
}

// migrations/0012_bench_notes.sql keys a note by (fixture_id, seat_number)
// only -- there's no link to which specific release event it was posted
// about, so a seat claimed and released again *without* a new note would
// otherwise still surface the previous release's now-stale note (wrong
// body, wrong cost/amount, and a "Take the Pitch" button on a thread that
// isn't about the seat's current turn on the bench). A note only counts
// for the seat's *current* stay on the bench if it was posted at or after
// that seat's own last update -- the same PATCH that set status=on_bench
// either wrote a note in the same request or didn't, so a genuinely
// current note's posted_at can never be earlier than seat.updated_at.
function latestNoteFor(fixtureId, seatNumber, seat) {
  const matches = realBenchNotesCache.filter((n) => n.fixture_id === fixtureId && n.seat_number === seatNumber);
  if (!seat?.updated_at) return matches[0] || null; // realBenchNotesCache is newest-first
  const cutoff = parseSqliteUtc(seat.updated_at);
  return matches.find((n) => parseSqliteUtc(n.posted_at) >= cutoff) || null;
}

function benchCardEl(fixture, seat, claimable) {
  const note = latestNoteFor(fixture.id, seat.seat_number, seat);
  const free = !!note && note.cost_path === 'free';

  const card = document.createElement('article');
  card.className = 'card';
  card.style.borderLeft = `3px solid ${claimable ? 'var(--summit-sandstone)' : 'var(--hairline-strong)'}`;

  const top = document.createElement('div');
  top.style.cssText = 'display:flex;justify-content:space-between;gap:10px;align-items:flex-start';
  const left = document.createElement('div');
  const eyebrow = document.createElement('p');
  eyebrow.className = 'eyebrow';
  eyebrow.textContent = `${matchDateLabel(fixture.kickoff_at)} · ${matchTimeLabel(fixture.kickoff_at)}`;
  const title = document.createElement('p');
  title.style.cssText = 'margin:4px 0 0;font-family:var(--font-display);font-weight:700;font-size:17px';
  title.textContent = `vs ${fixture.opponent}`;
  const sub = document.createElement('p');
  sub.style.cssText = 'margin:2px 0 0;font-size:13px;color:var(--ink-mute)';
  sub.textContent = `Seat ${seat.seat_number}`;
  left.append(eyebrow, title, sub);
  top.appendChild(left);
  if (fixture.tier === 'rivalry') {
    const badgeEl = document.createElement('span');
    badgeEl.className = 'badge badge--gold';
    badgeEl.textContent = 'Rivalry';
    top.appendChild(badgeEl);
  }
  card.appendChild(top);

  if (note) {
    const noteP = document.createElement('p');
    noteP.style.cssText = 'margin:10px 0 0;font-size:14px;color:var(--ink-soft)';
    noteP.textContent = `“${note.body}” — ${note.author_name}`;
    card.appendChild(noteP);
  }

  const priceRow = document.createElement('div');
  priceRow.style.cssText = 'display:flex;align-items:center;gap:8px;margin-top:12px;flex-wrap:wrap';
  const priceBadge = document.createElement('span');
  if (claimable) {
    if (free) {
      priceBadge.className = 'badge badge--gold';
      priceBadge.textContent = 'On the house';
    } else {
      priceBadge.className = 'badge badge--green';
      priceBadge.textContent = `${moneyCents(note ? note.amount_cents : fixture.weighted_value_cents)} to take it`;
    }
  } else {
    priceBadge.className = 'badge badge--ember';
    priceBadge.textContent = `Asking ${moneyCents(seat.resale_price_cents ?? fixture.weighted_value_cents)}`;
  }
  priceRow.appendChild(priceBadge);
  card.appendChild(priceRow);

  if (claimable) {
    const btn = document.createElement('button');
    btn.className = 'btn btn--primary btn--block';
    btn.type = 'button';
    btn.style.marginTop = '12px';
    btn.dataset.claimSeat = seat.id;
    btn.textContent = 'Claim from Bench';
    card.appendChild(btn);
  } else {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;margin-top:12px;flex-wrap:wrap';
    const link = document.createElement('a');
    link.className = 'btn btn--ghost';
    link.href = 'https://seatgeek.com/';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View listing';
    row.appendChild(link);
    // Only the lister themselves can pull a resale-listed seat back --
    // update_seat's own permission rules refuse anyone else, so the
    // button isn't offered to a member it would just 403 for.
    if (seat.assigned_user_id === state.user?.id) {
      const pullBtn = document.createElement('button');
      pullBtn.className = 'btn btn--ghost';
      pullBtn.type = 'button';
      pullBtn.dataset.claimSeat = seat.id;
      pullBtn.textContent = 'Pull it back';
      row.appendChild(pullBtn);
    }
    card.appendChild(row);
  }

  return card;
}

function paintBenchLists() {
  const waitingSection = document.getElementById('bench-waiting');
  const waitingList = document.getElementById('bench-waiting-list');
  const listedSection = document.getElementById('bench-listed');
  const listedList = document.getElementById('bench-listed-list');
  const emptyEl = document.getElementById('bench-empty');
  if (!waitingList || !listedList) return;

  waitingList.innerHTML = '';
  listedList.innerHTML = '';
  let waitingCount = 0;
  let listedCount = 0;
  for (const { fixture, seats } of realFixturesCache.filter(({ fixture: f }) => isUpcoming(f))) {
    for (const seat of seats) {
      if (seat.status === 'on_bench') {
        waitingList.appendChild(benchCardEl(fixture, seat, true));
        waitingCount += 1;
      } else if (seat.status === 'resale_listed') {
        listedList.appendChild(benchCardEl(fixture, seat, false));
        listedCount += 1;
      }
    }
  }

  if (waitingSection) waitingSection.hidden = waitingCount === 0;
  if (listedSection) listedSection.hidden = listedCount === 0;
  if (emptyEl) emptyEl.hidden = waitingCount > 0 || listedCount > 0;
}

function benchNoteThreadEl(note, fixture, seat) {
  const card = document.createElement('article');
  card.className = 'card';

  const head = document.createElement('div');
  head.style.cssText = 'display:flex;justify-content:space-between;gap:8px;align-items:flex-start';
  const who = document.createElement('div');
  who.style.cssText = 'display:flex;gap:10px';
  who.appendChild(avatarEl(note.author_name, false));
  const meta = document.createElement('div');
  const nameP = document.createElement('p');
  nameP.style.cssText = 'margin:0;font-weight:600;font-size:14px';
  nameP.textContent = `${note.author_name} · ${fixture ? fixture.opponent : ''} · Seat ${note.seat_number}`;
  const whenP = document.createElement('p');
  whenP.className = 'eyebrow';
  whenP.style.marginTop = '2px';
  whenP.textContent = relativeTime(note.posted_at);
  meta.append(nameP, whenP);
  who.appendChild(meta);
  head.appendChild(who);
  const costBadge = document.createElement('span');
  costBadge.className = note.cost_path === 'repay' ? 'badge badge--green' : 'badge badge--gold';
  costBadge.textContent = note.cost_path === 'repay' ? `Get paid back · ${moneyCents(note.amount_cents)}` : 'On the house';
  head.appendChild(costBadge);
  card.appendChild(head);

  const bodyP = document.createElement('p');
  bodyP.style.cssText = 'margin:10px 0 0;font-size:15px';
  bodyP.textContent = note.body;
  card.appendChild(bodyP);

  if (note.replies.length) {
    const repliesBlock = document.createElement('div');
    repliesBlock.style.cssText = 'margin-top:12px;border-left:2px solid var(--hairline);padding-left:10px';
    for (const reply of note.replies) {
      const p = document.createElement('p');
      p.style.cssText = 'margin:0 0 6px;font-size:14px';
      const strong = document.createElement('strong');
      strong.textContent = `${reply.author_name}: `;
      p.append(strong, document.createTextNode(reply.body));
      repliesBlock.appendChild(p);
    }
    card.appendChild(repliesBlock);
  }

  const controls = document.createElement('div');
  controls.style.marginTop = '12px';
  const quickRow = document.createElement('div');
  quickRow.className = 'scroll-row';
  for (const q of QUICK_REPLIES) {
    const chip = document.createElement('button');
    chip.className = 'chip';
    chip.type = 'button';
    chip.dataset.quickReply = note.id;
    chip.dataset.text = q;
    chip.textContent = q;
    quickRow.appendChild(chip);
  }
  controls.appendChild(quickRow);

  const replyRow = document.createElement('div');
  replyRow.style.cssText = 'display:flex;gap:8px;margin-top:10px';
  const input = document.createElement('input');
  input.className = 'input';
  input.placeholder = 'Reply to the circle';
  input.setAttribute('aria-label', 'Reply');
  input.id = `reply-input-${note.id}`;
  const sendBtn = document.createElement('button');
  sendBtn.className = 'btn btn--ghost';
  sendBtn.type = 'button';
  sendBtn.style.flex = 'none';
  sendBtn.dataset.role = 'send-reply';
  sendBtn.dataset.note = note.id;
  sendBtn.textContent = 'Send';
  replyRow.append(input, sendBtn);
  controls.appendChild(replyRow);

  if (seat) {
    const claimBtn = document.createElement('button');
    claimBtn.className = 'btn btn--primary btn--block';
    claimBtn.type = 'button';
    claimBtn.style.marginTop = '10px';
    claimBtn.dataset.claimSeat = seat.id;
    claimBtn.textContent = 'Take the Pitch · ' + (note.cost_path === 'repay' ? moneyCents(note.amount_cents) : 'no cost');
    controls.appendChild(claimBtn);
  }
  card.appendChild(controls);

  return card;
}

function paintBenchNotesSection() {
  const section = document.getElementById('bench-notes-section');
  const list = document.getElementById('bench-notes-list');
  if (!section || !list) return;
  list.innerHTML = '';

  // One thread per seat currently on the bench, not one per note --
  // iterating notes directly could render the same seat twice if it was
  // claimed and released more than once (each release's note is kept, see
  // latestNoteFor), and a seat already claimed or pulled back has nothing
  // left to act on here even though its past notes stay in
  // realBenchNotesCache as real history.
  let shown = 0;
  for (const { fixture, seats } of realFixturesCache.filter(({ fixture: f }) => isUpcoming(f))) {
    for (const seat of seats) {
      if (seat.status !== 'on_bench') continue;
      const note = latestNoteFor(fixture.id, seat.seat_number, seat);
      if (!note) continue;
      list.appendChild(benchNoteThreadEl(note, fixture, seat));
      shown += 1;
    }
  }
  section.hidden = shown === 0;
}

function openCallASub(allocationId) {
  const entry = realFixturesCache.find(({ seats }) => seats.some((s) => s.id === allocationId));
  if (!entry) return;
  const seat = entry.seats.find((s) => s.id === allocationId);
  callASubTarget = {
    allocationId,
    fixtureId: entry.fixture.id,
    seatNumber: seat.seat_number,
    faceCents: entry.fixture.weighted_value_cents,
  };

  const contextText = `${entry.fixture.opponent} · Seat ${seat.seat_number}`;
  for (const id of ['callasub-context', 'release-context', 'guest-context', 'list-context']) {
    const el = document.getElementById(id);
    if (el) el.textContent = contextText;
  }
  const repayLabel = document.getElementById('cost-repay-label');
  if (repayLabel) repayLabel.textContent = `Get paid back · ${moneyCents(callASubTarget.faceCents)}`;
  const askPriceInput = document.getElementById('ask-price');
  if (askPriceInput) askPriceInput.value = String(Math.round(callASubTarget.faceCents / 100));
  const releaseNoteInput = document.getElementById('release-note');
  if (releaseNoteInput) releaseNoteInput.value = '';
  const guestNameInput = document.getElementById('guest-name');
  if (guestNameInput) guestNameInput.value = '';
  for (const id of ['release-error', 'guest-error', 'list-error']) {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  }
  openSheet('sheet-callasub');
}

async function patchSeat(allocationId, payload) {
  const res = await fetch(`${API_BASE}/api/seats/${allocationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.sessionToken}` },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || 'Could not update the seat.');
  }
  await paintRealFixtures();
}

async function claimRealSeat(allocationId) {
  try {
    await patchSeat(allocationId, { status: 'confirmed' });
  } catch {
    // No dedicated error slot next to every claim/pull-back button spread
    // across three screens, so a stale click (someone else just took it,
    // a 409) fails without a message rather than needing one -- but the
    // card itself must still catch up to what really happened, which
    // patchSeat's own re-paint never ran here since it only follows a
    // successful PATCH.
    paintRealFixtures();
  }
}

async function releaseSeatToBench(allocationId, note, costPath, faceCents) {
  const payload = { status: 'on_bench' };
  if (note) {
    payload.note = note;
    payload.cost_path = costPath;
    if (costPath === 'repay') payload.amount_cents = faceCents;
  }
  await patchSeat(allocationId, payload);
}

async function giftSeat(allocationId, guestName) {
  await patchSeat(allocationId, { status: 'gifted', guest_name: guestName });
}

async function listSeatForResale(allocationId, priceCents) {
  await patchSeat(allocationId, { status: 'resale_listed', resale_price_cents: priceCents });
}

async function postBenchNoteReply(noteId, body) {
  try {
    const res = await fetch(`${API_BASE}/api/bench-notes/${noteId}/replies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.sessionToken}` },
      body: JSON.stringify({ body }),
    });
    if (res.ok) await paintRealFixtures();
  } catch {
    // offline -- the reply just doesn't show; there is nothing local to
    // roll back since it was never optimistically added
  }
}

async function joinSyndicate(code) {
  const errorEl = document.getElementById('join-syndicate-error');
  let res;
  try {
    res = await fetch(`${API_BASE}/api/groups/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.sessionToken}` },
      body: JSON.stringify({ invite_code: code }),
    });
  } catch {
    if (errorEl) { errorEl.textContent = 'Could not reach the server -- check your connection.'; errorEl.hidden = false; }
    return;
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (errorEl) { errorEl.textContent = body.error || 'Could not join with that code.'; errorEl.hidden = false; }
    return;
  }
  const { group } = await res.json();
  settleIntoSyndicate(group);
}

// ---------- Settings ----------

function setPref(name, value) {
  state.prefs[name] = value;
  persist();
}

function wireToggle(btn) {
  btn.addEventListener('click', () => {
    const on = btn.getAttribute('aria-checked') !== 'true';
    btn.setAttribute('aria-checked', String(on));
    const name = btn.dataset.pref;
    setPref(name, on);
    if (name === 'checkin3Day') document.getElementById('checkin-time-row').hidden = !on;
    if (name === 'dailyBio') document.getElementById('bio-scope-block').hidden = !on;
  });
}

function iosDeviceState() {
  const ua = navigator.userAgent;
  const isIos = /iPad|iPhone|iPod/.test(ua) || (ua.includes('Macintosh') && 'ontouchend' in document);
  const standalone = window.navigator.standalone === true || window.matchMedia?.('(display-mode: standalone)').matches;
  return { isIos, standalone };
}

function paintDeviceBanner() {
  const { isIos, standalone } = iosDeviceState();
  const which = isIos && !standalone ? 'ios-safari' : (state.prefs.pushEnabled ? 'active' : 'prompt');
  for (const el of document.querySelectorAll('[data-device-banner]')) {
    el.hidden = el.dataset.deviceBanner !== which;
  }
}

function hydratePrefs() {
  // The switches, dependent rows and bio-scope radios are pre-rendered with
  // their default values; when a returning visitor's persisted prefs differ
  // from those defaults, reflect the real state before anything is clicked.
  for (const btn of document.querySelectorAll('.switch[data-pref]')) {
    btn.setAttribute('aria-checked', String(!!state.prefs[btn.dataset.pref]));
  }
  const checkinRow = document.getElementById('checkin-time-row');
  if (checkinRow) checkinRow.hidden = !state.prefs.checkin3Day;
  const bioScopeBlock = document.getElementById('bio-scope-block');
  if (bioScopeBlock) bioScopeBlock.hidden = !state.prefs.dailyBio;
  for (const btn of document.querySelectorAll('[data-role="bio-scope"]')) {
    const on = btn.dataset.value === state.prefs.bioScope;
    btn.setAttribute('aria-checked', String(on));
    btn.style.borderColor = on ? 'var(--summit-green)' : '';
    btn.style.background = on ? 'var(--surface-sunk)' : '';
  }
}

// Shared by the Settings "Group & profile" card's name/phone/email fields --
// each saves itself independently on change, same PATCH /api/me endpoint
// signIn() already uses for the sign-in-time rename.
async function patchMe(fields) {
  if (!state.sessionToken) return;
  try {
    const res = await fetch(`${API_BASE}/api/me`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.sessionToken}` },
      body: JSON.stringify(fields),
    });
    if (!res.ok) return;
    const { user } = await res.json();
    state.user = user;
    persist();
  } catch { /* offline -- the typed value stands locally until this saves */ }
}

function hydrateProfile() {
  const nameInput = document.getElementById('display-name');
  if (nameInput && state.user?.name) nameInput.value = state.user.name;
  const phoneInput = document.getElementById('phone');
  if (phoneInput && state.user?.phone) phoneInput.value = state.user.phone;
  const emailInput = document.getElementById('email');
  if (emailInput && state.user?.contact_email) emailInput.value = state.user.contact_email;
}

function paintPreview() {
  const checkinTime = document.getElementById('checkin-time')?.value ?? '10:00';
  const bioTime = document.getElementById('bio-time')?.value ?? '08:00';
  const el1 = document.getElementById('preview-checkin-time');
  const el2 = document.getElementById('preview-bio-time');
  if (el1) el1.textContent = label12(checkinTime);
  if (el2) el2.textContent = label12(bioTime);
  const scopeLabel = document.querySelector(`[data-role="bio-scope"][data-value="${state.prefs.bioScope}"] .path__name`)?.textContent ?? '';
  const scopeEl = document.getElementById('preview-scope-label');
  if (scopeEl) scopeEl.textContent = `Mix: ${scopeLabel}.`;
}

// Every element carrying the syndicate's name -- the header readout and
// the Settings profile card -- shares this data-role so both update
// together, whether that's on load (a name set in an earlier session) or
// right after "Start a new syndicate" is submitted.
function paintSyndicateName() {
  if (!state.syndicateName) return;
  for (const node of document.querySelectorAll('[data-role="syndicate-name"]')) {
    node.textContent = state.syndicateName;
  }
}

// Settings' "Seat assignment" card -- the real section/row/seat this device
// last created or was told about, once any of the three is known. Parts
// that were never set (e.g. a syndicate created with no section given)
// just don't appear, rather than showing "Sec null". Captured once, before
// this ever writes to the node, so joining or creating a *different*
// syndicate later with no seat details restores the static build's own
// placeholder instead of leaving the previous syndicate's real seat
// showing.
let staticSeatAssignmentText = null;

function paintSeatAssignment() {
  const nodes = document.querySelectorAll('[data-role="seat-assignment"]');
  if (staticSeatAssignmentText === null && nodes.length) {
    staticSeatAssignmentText = nodes[0].textContent;
  }
  const parts = [];
  if (state.section) parts.push(`Sec ${state.section}`);
  if (state.seatRow) parts.push(`Row ${state.seatRow}`);
  if (state.mySeatLabel) parts.push(`Seat ${state.mySeatLabel}`);
  const text = parts.length ? parts.join(', ') : staticSeatAssignmentText;
  for (const node of nodes) {
    node.textContent = text;
  }
}

function label12(hhmm) {
  const [h24, m] = hhmm.split(':').map(Number);
  const suffix = h24 >= 12 ? 'PM' : 'AM';
  const hr = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${hr}:${String(m).padStart(2, '0')} ${suffix}`;
}

// ---------- Wiring ----------

function main() {
  // A stage past Landing means signed in, in this build -- but pre-PR
  // localStorage (the old fake "Continue with Google" flow) could have
  // persisted 'syndicate' or 'app' with no sessionToken at all. Restoring
  // that stage as-is would skip the password screen entirely for a
  // returning visitor, so a non-landing stage always needs a session to
  // come back to, same as reaching one in the first place does now.
  if (state.stage !== 'landing' && !state.sessionToken) state.stage = 'landing';
  showStage(state.stage);
  showTab(state.tab);
  showSeason(state.season);
  wirePhotoSlots();
  hydratePrefs();
  paintDeviceBanner();
  paintPreview();
  paintSyndicateName();
  paintSeatAssignment();
  paintPasswordField();
  loadGuestSlots();
  hydrateProfile();
  paintRealSyndicateDetail();
  paintRealFixtures();

  document.querySelectorAll('.switch[data-pref]').forEach(wireToggle);
  document.getElementById('checkin-time')?.addEventListener('change', paintPreview);
  document.getElementById('bio-time')?.addEventListener('change', paintPreview);

  document.getElementById('display-name')?.addEventListener('change', (e) => {
    const name = e.target.value.trim();
    if (name) patchMe({ name });
  });
  document.getElementById('phone')?.addEventListener('change', (e) => {
    patchMe({ phone: e.target.value.trim() }); // '' clears it, same as the API allows
  });
  document.getElementById('email')?.addEventListener('change', (e) => {
    patchMe({ contact_email: e.target.value.trim() });
  });

  document.body.addEventListener('click', (e) => {
    // Clicking the backdrop itself (not its sheet card) closes it. Checked
    // before the closest() match below, since the backdrop carries
    // data-role="sheet" itself and would otherwise match that selector.
    if (e.target.dataset?.role === 'sheet' || e.target.classList?.contains('sheet-backdrop')) {
      closeSheet();
      return;
    }

    const el = e.target.closest('[data-role],[data-open-sheet],[data-close-sheet],[data-claim-seat],[data-call-a-sub],[data-carousel],[data-carousel-dot],[data-cost-choice],[data-quick-reply]');
    if (!el) return;

    if (el.dataset.callASub) { openCallASub(el.dataset.callASub); return; }
    if (el.dataset.openSheet) { openSheet(el.dataset.openSheet); return; }
    if (el.dataset.closeSheet !== undefined) { closeSheet(); return; }
    if (el.dataset.claimSeat) { claimRealSeat(el.dataset.claimSeat); return; }

    switch (el.dataset.role) {
      case 'guest-login':
        signIn(el.dataset.guestId);
        return;
      case 'select-syndicate': {
        const group = myGroupsCache.find((g) => g.id === el.dataset.groupId);
        if (group) settleIntoSyndicate(group, group.seat_label || null);
        return;
      }
      case 'join-syndicate': {
        if (el.disabled) return; // a request is already in flight
        const codeInput = document.getElementById('invite');
        const code = codeInput ? codeInput.value.trim() : '';
        const errorEl = document.getElementById('join-syndicate-error');
        if (errorEl) errorEl.hidden = true;
        if (!code) {
          if (errorEl) { errorEl.textContent = 'Enter an invite code first.'; errorEl.hidden = false; }
          codeInput?.focus();
          return;
        }
        el.disabled = true;
        joinSyndicate(code).finally(() => { el.disabled = false; });
        return;
      }
      case 'sign-out':
        // Only the signed-in identity goes away -- the syndicate itself
        // (its name), and everything else about this device's demo state,
        // isn't this one person's to erase just by picking a different
        // guest slot next. The remembered device trust (DEVICE_KEY) is a
        // separate key entirely and is untouched either way.
        state.sessionToken = null;
        state.user = null;
        state.stage = 'landing';
        persist();
        location.reload();
        return;
      case 'tab':
        showTab(el.dataset.value);
        return;
      case 'tab-toggle-settings':
        showTab(state.tab === 'settings' ? 'matchday' : 'settings');
        return;
      case 'goto-bench':
        showTab('bench');
        return;
      case 'goto-hearth':
        showTab('hearth');
        return;
      case 'season':
        showSeason(el.dataset.value);
        return;
      case 'pitch-filter': {
        document.querySelectorAll('[data-role="pitch-filter"]').forEach((c) => c.setAttribute('aria-selected', String(c === el)));
        applyPitchFilter();
        return;
      }
      case 'hometeam-filter': {
        document.querySelectorAll('[data-role="hometeam-filter"]').forEach((c) => c.setAttribute('aria-selected', String(c === el)));
        const v = el.dataset.value;
        document.querySelectorAll('[data-position]').forEach((card) => {
          card.hidden = v !== 'Whole squad' && card.dataset.position !== v;
        });
        return;
      }
      case 'opponent': {
        document.querySelectorAll('[data-role="opponent"]').forEach((c) => c.setAttribute('aria-selected', String(c === el)));
        document.querySelectorAll('[data-opponent-block]').forEach((b) => { b.hidden = b.dataset.opponentBlock !== el.dataset.value; });
        return;
      }
      case 'bio-scope': {
        document.querySelectorAll('[data-role="bio-scope"]').forEach((btn) => {
          const on = btn === el;
          btn.setAttribute('aria-checked', String(on));
          btn.style.borderColor = on ? 'var(--summit-green)' : '';
          btn.style.background = on ? 'var(--surface-sunk)' : '';
        });
        setPref('bioScope', el.dataset.value);
        paintPreview();
        return;
      }
      case 'expand': {
        const target = document.getElementById(el.dataset.target);
        const open = target.hidden;
        target.hidden = !open;
        el.setAttribute('aria-expanded', String(open));
        el.textContent = open ? el.dataset.labelClose : el.dataset.labelOpen;
        return;
      }
      case 'trivia-toggle': {
        const answer = el.parentElement.querySelector('[data-role="trivia-answer"]');
        const open = answer.hidden;
        answer.hidden = !open;
        el.setAttribute('aria-expanded', String(open));
        el.textContent = open ? 'Hide' : 'Tap to reveal';
        return;
      }
      case 'enable-push':
        if (window.Notification?.requestPermission) {
          Notification.requestPermission()
            .then((permission) => {
              setPref('pushEnabled', permission === 'granted');
              paintDeviceBanner();
            })
            .catch(() => {
              setPref('pushEnabled', false);
              paintDeviceBanner();
            });
        } else {
          // No Notification API to ask permission of. An installed iOS PWA
          // still gets push via its own entitlements without this API — but
          // anywhere else there's nothing to enable, so don't claim success.
          const { isIos, standalone } = iosDeviceState();
          setPref('pushEnabled', isIos && standalone);
          paintDeviceBanner();
        }
        return;
      case 'send-reply': {
        const noteId = el.dataset.note;
        const input = document.getElementById(`reply-input-${noteId}`);
        if (!input || !input.value.trim()) return;
        const text = input.value.trim();
        input.value = '';
        postBenchNoteReply(noteId, text);
        return;
      }
      case 'post-release': {
        if (!callASubTarget) return;
        const errorEl = document.getElementById('release-error');
        if (errorEl) errorEl.hidden = true;
        const note = document.getElementById('release-note').value.trim();
        const costPath = document.querySelector('#sheet-release [data-cost-choice][aria-pressed="true"]')?.dataset.costChoice ?? 'repay';
        el.disabled = true;
        releaseSeatToBench(callASubTarget.allocationId, note, costPath, callASubTarget.faceCents)
          .then(() => closeSheet())
          .catch((err) => { if (errorEl) { errorEl.textContent = err.message; errorEl.hidden = false; } })
          .finally(() => { el.disabled = false; });
        return;
      }
      case 'post-guest': {
        if (!callASubTarget) return;
        const errorEl = document.getElementById('guest-error');
        if (errorEl) errorEl.hidden = true;
        const guestName = document.getElementById('guest-name').value.trim();
        if (!guestName) {
          if (errorEl) { errorEl.textContent = 'Enter who is taking the seat.'; errorEl.hidden = false; }
          return;
        }
        el.disabled = true;
        giftSeat(callASubTarget.allocationId, guestName)
          .then(() => closeSheet())
          .catch((err) => { if (errorEl) { errorEl.textContent = err.message; errorEl.hidden = false; } })
          .finally(() => { el.disabled = false; });
        return;
      }
      case 'post-list': {
        if (!callASubTarget) return;
        const errorEl = document.getElementById('list-error');
        if (errorEl) errorEl.hidden = true;
        const askDollars = Number(document.getElementById('ask-price').value);
        if (!askDollars || askDollars <= 0) {
          if (errorEl) { errorEl.textContent = 'Enter a target face value first.'; errorEl.hidden = false; }
          return;
        }
        el.disabled = true;
        listSeatForResale(callASubTarget.allocationId, Math.round(askDollars * 100))
          .then(() => closeSheet())
          .catch((err) => { if (errorEl) { errorEl.textContent = err.message; errorEl.hidden = false; } })
          .finally(() => { el.disabled = false; });
        return;
      }
    }

    if (el.dataset.costChoice) {
      const group = el.closest('[data-role="cost-group"]');
      group.querySelectorAll('[data-cost-choice]').forEach((btn) => {
        const on = btn === el;
        btn.setAttribute('aria-pressed', String(on));
        btn.style.borderColor = on ? 'var(--summit-green)' : '';
        btn.style.background = on ? 'var(--surface-sunk)' : '';
      });
      return;
    }

    if (el.dataset.quickReply) {
      postBenchNoteReply(el.dataset.quickReply, el.dataset.text);
      return;
    }

    if (el.dataset.carousel) {
      const card = el.closest('[data-role="touchline-carousel"]');
      const count = Number(card.dataset.count);
      const current = Number(card.querySelector('[data-carousel-slide]:not([hidden])').dataset.carouselSlide);
      const next = el.dataset.carousel === 'next' ? (current + 1) % count : (current - 1 + count) % count;
      card.querySelectorAll('[data-carousel-slide]').forEach((s) => { s.hidden = Number(s.dataset.carouselSlide) !== next; });
      card.querySelectorAll('[data-carousel-dot]').forEach((d) => {
        const active = Number(d.dataset.carouselDot) === next;
        d.style.width = active ? '18px' : '6px';
        d.style.background = active ? 'var(--summit-green)' : 'var(--hairline-strong)';
      });
      return;
    }
  });

  // Settle Up needs the amount from whichever "Settle Up" button opened it.
  // Each app link's real href is written here, at sheet-open time, since
  // that's the only moment the amount and memo are both known — clicking
  // then just follows a normal target="_blank" link.
  document.body.addEventListener('click', (e) => {
    const trigger = e.target.closest('[data-open-sheet="sheet-settleup"]');
    if (!trigger) return;
    const cents = Number(trigger.dataset.settleAmount || 0);
    const owed = trigger.dataset.settleOwed === 'true';
    const opponent = document.querySelector('[data-tab="matchday"] h2')?.textContent?.replace('Summit vs ', '') ?? 'Summit';
    const memo = `SquadSeats: Match vs. ${opponent}`;
    const amount = (cents / 100).toFixed(2);
    document.getElementById('settle-amount').textContent = moneyCents(cents);
    document.getElementById('settle-sub').textContent = owed
      ? 'What the circle owes you. Send the request and it lands with the amount filled in.'
      : 'What you owe. Each button opens with the amount and memo already set.';
    document.getElementById('settle-memo').textContent = memo;
    const links = {
      venmo: `https://venmo.com/?txn=${owed ? 'charge' : 'pay'}&amount=${amount}&note=${encodeURIComponent(memo)}`,
      cashapp: 'https://cash.app/$/summitbasecamp',
      zelle: 'https://www.zellepay.com/',
    };
    for (const [app, href] of Object.entries(links)) {
      const a = document.querySelector(`[data-settle-app="${app}"]`);
      if (a) a.href = href;
    }
  });

  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSheet(); });

  // A real <form>, not a bare button, so pressing Enter in the name field
  // submits it and the browser's own required-field validation applies.
  // preventDefault stops the GET-navigation a plain form submit would try,
  // since this now sends the same fields to the real POST /api/groups.
  document.getElementById('new-syndicate-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const nameInput = document.getElementById('new-syn-name');
    const name = nameInput.value.trim();
    if (!name) { nameInput.focus(); return; }

    // Guards against a double-click or two quick Enter presses creating two
    // real syndicates before either request settles -- re-enabled in the
    // finally below on every exit path, success or failure alike.
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
      if (submitBtn.disabled) return;
      submitBtn.disabled = true;
    }

    try {
      const errorEl = document.getElementById('new-syndicate-error');
      if (errorEl) errorEl.hidden = true;
      const seasonYear = Number(document.getElementById('new-syn-season').value) || 2026;
      const totalSeats = Number(document.getElementById('new-syn-seats').value) || 1;
      const costInput = document.getElementById('new-syn-cost');
      const packageCostCents = costInput.value ? Math.round(Number(costInput.value) * 100) : 0;
      const section = document.getElementById('new-syn-section').value.trim();
      const seatRow = document.getElementById('new-syn-row').value.trim();
      const seatLabels = document.getElementById('new-syn-seat-labels').value.trim();
      const mySeatLabel = document.getElementById('new-syn-my-seat').value.trim();

      let res;
      try {
        res = await fetch(`${API_BASE}/api/groups`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${state.sessionToken}` },
          body: JSON.stringify({
            name, season_year: seasonYear, total_seats: totalSeats, package_cost_cents: packageCostCents,
            section, seat_row: seatRow, seat_labels: seatLabels, my_seat_label: mySeatLabel,
          }),
        });
      } catch {
        if (errorEl) { errorEl.textContent = 'Could not reach the server -- check your connection.'; errorEl.hidden = false; }
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (errorEl) { errorEl.textContent = body.error || 'Could not create the syndicate.'; errorEl.hidden = false; }
        return;
      }
      const { group } = await res.json();
      settleIntoSyndicate(group, mySeatLabel || null);
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

document.addEventListener('DOMContentLoaded', main);

if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => { /* offline support is a bonus */ });
  });
}
