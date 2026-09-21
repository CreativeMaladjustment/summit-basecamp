// The entire runtime for a page Python already rendered. Every screen, every
// filter result, every toggle state and every Call-a-Sub sheet already
// exists in the DOM (see web/build_src/) — this file's job is to show and
// hide the right pre-rendered nodes and persist a little state, never to
// build HTML. The two exceptions, clearly marked below, are places nothing
// but the browser knows the content ahead of time: a typed reply and a
// dropped photo.

const KEY = 'shb.v2';

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
  claimedSeats: [],         // seat keys claimed from the bench
  releasedSeats: [],        // seats you gave up via Call a Sub
  prefs: { checkin3Day: true, benchAlerts: true, dailyBio: true, bioScope: 'home_first', pushEnabled: false },
  photos: {},                // playerId -> data URL, restored on load
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

// ---------- Seats: flip which pre-rendered variant is visible ----------

function seatNodes(key) {
  return document.querySelectorAll(`[data-seat="${CSS.escape(key)}"]`);
}

function setSeatState(key, toState) {
  for (const node of seatNodes(key)) {
    node.hidden = node.dataset.state !== toState;
  }
}

function claimSeat(key, handOffId) {
  setSeatState(key, 'claimed');
  if (!state.claimedSeats.includes(key)) state.claimedSeats.push(key);
  // The card in Bench and the row's claim button in Pitch live inside a
  // [data-seat] wrapper too, so hide the whole card once claimed.
  for (const card of document.querySelectorAll(`[data-bench-card][data-seat="${CSS.escape(key)}"]`)) {
    card.hidden = true;
  }
  for (const btn of document.querySelectorAll(`[data-claim-seat="${CSS.escape(key)}"]`)) {
    btn.hidden = true;
  }
  // Claiming from the Matchday bench-note thread flips that note's own
  // controls off and shows who took it, in addition to the generic
  // [data-seat] toggling above.
  if (handOffId) {
    const controls = document.getElementById(`active-controls-${handOffId}`);
    if (controls) controls.hidden = true;
    const takenLine = document.getElementById(`taken-line-${handOffId}`);
    if (takenLine) {
      takenLine.textContent = 'You took the seat.';
      takenLine.hidden = false;
    }
  }
  refreshBenchCount();
  persist();
}

// outcome: 'released' (open to the whole circle), 'gifted' (a named guest)
// or 'listed' (an external exchange) — only 'released' also reveals the
// seat's claimable Bench card, keyed separately (see seats.py/bench.py) so
// gifting or listing a seat never makes it wrongly appear open to claim.
function releaseSeat(key, outcome) {
  setSeatState(key, 'released');
  if (outcome === 'released') setSeatState(`${key}:listing`, 'open');
  if (!state.releasedSeats.includes(key)) state.releasedSeats.push(key);
  refreshBenchCount();
  persist();
}

function refreshBenchCount() {
  const openCards = document.querySelectorAll('[data-bench-card]:not([hidden])');
  const count = openCards.length;
  for (const el of document.querySelectorAll('[data-bench-count]')) {
    el.textContent = String(count);
    el.closest('button')?.classList.toggle('is-empty', count === 0);
  }
  const waiting = document.getElementById('bench-waiting');
  if (waiting) {
    const visibleCards = waiting.querySelectorAll('[data-bench-card]:not([hidden])');
    waiting.hidden = visibleCards.length === 0;
  }
  const listed = document.getElementById('bench-listed');
  if (listed) {
    const visibleListed = listed.querySelectorAll('[data-bench-card]:not([hidden])');
    listed.hidden = visibleListed.length === 0;
  }
  const empty = document.getElementById('bench-empty');
  if (empty) {
    const anyVisible = document.querySelectorAll('#bench-waiting [data-bench-card]:not([hidden]), #bench-listed [data-bench-card]:not([hidden])').length;
    empty.hidden = anyVisible > 0;
  }
}

// ---------- Bench notes: the one place a whole new card is built in JS,
// because its text is whatever the person just typed. ----------

function moneyCents(cents) {
  const dollars = cents / 100;
  return cents % 100 === 0 ? `$${dollars.toLocaleString('en-US')}` : `$${dollars.toFixed(2)}`;
}

function addBenchNoteCard({ fixtureId, seatNumber, opponent, short, body, costPath, amountCents }) {
  const list = document.getElementById('bench-notes-list');
  const section = document.getElementById('bench-notes-section');
  if (!list || !section) return;

  const card = document.createElement('article');
  card.className = 'card';

  const head = document.createElement('div');
  head.style.cssText = 'display:flex;justify-content:space-between;gap:8px;align-items:flex-start';
  const who = document.createElement('div');
  who.style.cssText = 'display:flex;gap:10px';
  const av = document.createElement('div');
  av.className = 'avatar';
  av.style.background = '#134E48';
  av.textContent = 'YO';
  const meta = document.createElement('div');
  const name = document.createElement('p');
  name.style.cssText = 'margin:0;font-weight:600;font-size:14px';
  name.textContent = `You · ${short} · Seat ${seatNumber}`;
  const when = document.createElement('p');
  when.className = 'eyebrow';
  when.style.marginTop = '2px';
  when.textContent = 'just now';
  meta.append(name, when);
  who.append(av, meta);

  const costBadge = document.createElement('span');
  costBadge.className = costPath === 'repay' ? 'badge badge--green' : 'badge badge--gold';
  costBadge.textContent = costPath === 'repay' ? `Get paid back · ${moneyCents(amountCents)}` : 'On the house';
  head.append(who, costBadge);

  const text = document.createElement('p');
  text.style.cssText = 'margin:10px 0 0;font-size:15px';
  text.textContent = body; // textContent, never innerHTML — this is user input

  card.append(head, text);
  list.prepend(card);
  section.hidden = false;
}

function addReply(noteId, text) {
  const container = document.getElementById(`replies-${noteId}`);
  if (!container || !text.trim()) return;
  container.hidden = false;
  const p = document.createElement('p');
  p.style.cssText = 'margin:0 0 6px;font-size:14px';
  const strong = document.createElement('strong');
  strong.textContent = 'You: ';
  p.append(strong, document.createTextNode(text.trim()));
  container.append(p);
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

function label12(hhmm) {
  const [h24, m] = hhmm.split(':').map(Number);
  const suffix = h24 >= 12 ? 'PM' : 'AM';
  const hr = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${hr}:${String(m).padStart(2, '0')} ${suffix}`;
}

// ---------- Wiring ----------

function main() {
  showStage(state.stage);
  showTab(state.tab);
  showSeason(state.season);
  for (const key of state.claimedSeats) setSeatState(key, 'claimed');
  for (const key of state.releasedSeats) setSeatState(key, 'released');
  refreshBenchCount();
  wirePhotoSlots();
  hydratePrefs();
  paintDeviceBanner();
  paintPreview();

  document.querySelectorAll('.switch[data-pref]').forEach(wireToggle);
  document.getElementById('checkin-time')?.addEventListener('change', paintPreview);
  document.getElementById('bio-time')?.addEventListener('change', paintPreview);

  document.body.addEventListener('click', (e) => {
    // Clicking the backdrop itself (not its sheet card) closes it. Checked
    // before the closest() match below, since the backdrop carries
    // data-role="sheet" itself and would otherwise match that selector.
    if (e.target.dataset?.role === 'sheet' || e.target.classList?.contains('sheet-backdrop')) {
      closeSheet();
      return;
    }

    const el = e.target.closest('[data-role],[data-open-sheet],[data-close-sheet],[data-claim-seat],[data-carousel],[data-carousel-dot],[data-cost-choice],[data-quick-reply]');
    if (!el) return;

    if (el.dataset.openSheet) { openSheet(el.dataset.openSheet); return; }
    if (el.dataset.closeSheet !== undefined) { closeSheet(); return; }
    if (el.dataset.claimSeat) { claimSeat(el.dataset.claimSeat, el.dataset.handOff); return; }

    switch (el.dataset.role) {
      case 'sign-in':
        showStage('syndicate');
        return;
      case 'join-syndicate':
        showStage('app');
        showTab('matchday');
        return;
      case 'start-new-syndicate':
        showStage('app');
        showTab('settings');
        return;
      case 'sign-out':
        localStorage.removeItem(KEY);
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
        const v = el.dataset.value;
        let visible = 0;
        document.querySelectorAll('[data-fixture-row]').forEach((row) => {
          const show = v === 'all' || (v === 'mine' && row.dataset.mine === 'true') || (v === 'bench' && row.dataset.bench === 'true');
          row.hidden = !show;
          if (show) visible += 1;
        });
        const empty = document.getElementById('pitch-empty');
        if (empty) empty.hidden = visible > 0;
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
        const input = document.getElementById(`reply-input-${el.dataset.note}`);
        if (!input) return;
        addReply(el.dataset.note, input.value);
        input.value = '';
        return;
      }
      case 'post-release': {
        addBenchNoteCard({
          fixtureId: el.dataset.fixture,
          seatNumber: el.dataset.seat,
          opponent: el.dataset.opponent,
          short: el.dataset.short,
          body: document.getElementById(`release-note-${el.dataset.fixture}-${el.dataset.seat}`).value.trim()
            || 'Seat is open — who wants it?',
          costPath: document.querySelector(`#sheet-release-${el.dataset.fixture}-${el.dataset.seat} [data-cost-choice][aria-pressed="true"]`)?.dataset.costChoice ?? 'repay',
          amountCents: Number(el.dataset.faceCents),
        });
        releaseSeat(`${el.dataset.fixture}-${el.dataset.seat}`, 'released');
        closeSheet();
        return;
      }
      case 'post-guest':
        // Guest name / list price are free text with no further screen that
        // needs to reflect them beyond the hero, so releasing the seat is
        // the whole state change.
        releaseSeat(el.dataset.seat, 'gifted');
        closeSheet();
        return;
      case 'post-list':
        releaseSeat(el.dataset.seat, 'listed');
        closeSheet();
        return;
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
      addReply(el.dataset.quickReply, el.dataset.text);
      return;
    }

    if (el.dataset.carousel) {
      const card = el.closest('[data-role="hearthside-carousel"]');
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
      cashapp: 'https://cash.app/$/summithearthbench',
      zelle: 'https://www.zellepay.com/',
    };
    for (const [app, href] of Object.entries(links)) {
      const a = document.querySelector(`[data-settle-app="${app}"]`);
      if (a) a.href = href;
    }
  });

  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSheet(); });

  document.getElementById('syn-switch')?.addEventListener('change', persist);
}

document.addEventListener('DOMContentLoaded', main);

if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => { /* offline support is a bonus */ });
  });
}
