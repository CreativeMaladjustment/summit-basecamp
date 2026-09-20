import { h, fill, svg, icons, toggle } from '../components/ui.js';
import * as S from '../state.js';
import { syndicates } from '../data/mock.js';

const SCOPES = [
  { value: 'home_first',  label: 'Home Squad First', help: 'Mostly Denver Summit FC starters and prospects, with marquee visiting stars leading up to matchday.' },
  { value: 'summit_only', label: 'Summit FC Only',   help: 'Exclusively our home squad roster.' },
  { value: 'full_nwsl',   label: 'Full NWSL Circuit', help: 'Equal mix across all league teams.' },
];

const TIMES = ['07:00', '08:00', '09:00', '10:00', '11:00', '12:00', '17:00', '18:00'];

export function settingsView() {
  const wrap = h('div', { class: 'view shell', style: { paddingTop: '16px' } });

  const paint = () => {
    const p = S.get().prefs;
    fill(wrap,
      h('h1', { style: { fontSize: '22px', fontWeight: '800' } }, 'Campfire Settings'),
      h('p', { style: { margin: '4px 0 14px', fontSize: '14px', color: 'var(--ink-mute)' } },
        'What reaches you, when, and on which device.'),

      deviceBanner(p, paint),

      h('div', { class: 'grid-auto', style: { alignItems: 'start' } },
        matchdaySection(p, paint),
        notesSection(p, paint),
        profileSection(p, paint),
        previewSection(p),
      ),
    );
  };

  paint();
  return wrap;
}

/** iOS Safari in a tab cannot take web push until the app is installed. */
function isIosSafari() {
  const state = S.get().deviceState;
  if (state === 'ios-safari') return true;
  if (state === 'installed') return false;
  const ua = navigator.userAgent;
  const ios = /iPad|iPhone|iPod/.test(ua) || (ua.includes('Macintosh') && 'ontouchend' in document);
  const standalone = window.navigator.standalone === true
    || window.matchMedia?.('(display-mode: standalone)').matches;
  return ios && !standalone;
}

function deviceBanner(p, repaint) {
  if (isIosSafari()) {
    return h('div', {
      class: 'card',
      style: { borderLeft: '3px solid var(--summit-sandstone)', background: 'rgba(200,75,49,.08)', marginBottom: '12px' },
    },
      h('div', { style: { display: 'flex', gap: '10px' } },
        svg(icons.share, { size: 20, stroke: 'var(--summit-sandstone)' }),
        h('p', { style: { margin: '0', fontSize: '14px', color: 'var(--ink-soft)' } },
          'To get instant alerts on iPhone, tap ',
          h('strong', null, 'Share'),
          ' (box with arrow) and select ',
          h('strong', null, 'Add to Home Screen'),
          ', then open the app from your home screen to enable push notifications.'),
      ),
    );
  }

  return h('div', { class: 'card', style: { marginBottom: '12px' } },
    p.pushEnabled
      ? h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px' } },
          h('span', {
            'aria-hidden': 'true',
            style: { width: '10px', height: '10px', borderRadius: '50%', background: '#16A34A', flex: 'none' },
          }),
          h('p', { style: { margin: '0', fontWeight: '600' } }, 'Notifications Active'),
        )
      : h('button', {
          class: 'btn btn--primary btn--block',
          type: 'button',
          onclick: async () => {
            try { await Notification?.requestPermission?.(); } catch { /* not available */ }
            S.setPref('pushEnabled', true);
            repaint();
          },
        }, 'Enable Push Notifications'),
  );
}

function matchdaySection(p, repaint) {
  return h('section', { class: 'card' },
    h('h2', { class: 'card__title' }, 'Matchday & roster alerts'),

    h('div', { class: 'setting-row' },
      h('div', { class: 'setting-row__body' },
        h('p', { class: 'setting-row__label' }, '3-Day Roster Check-in'),
        h('p', { class: 'setting-row__help' },
          "Get a notification 72 hours before kickoff to confirm you're attending or call a sub before the Bench fills up."),
        p.checkin3Day
          ? h('label', { style: { display: 'block', marginTop: '10px' } },
              h('span', { class: 'field__label' }, 'Delivered at'),
              h('select', {
                class: 'select',
                style: { maxWidth: '160px' },
                onchange: (e) => { S.setPref('checkinTime', e.target.value); repaint(); },
              }, TIMES.map((t) => h('option', { value: t, selected: t === p.checkinTime }, label12(t)))),
            )
          : null,
      ),
      toggle(p.checkin3Day, '3-Day Roster Check-in', (v) => { S.setPref('checkin3Day', v); repaint(); }),
    ),

    h('div', { class: 'setting-row' },
      h('div', { class: 'setting-row__body' },
        h('p', { class: 'setting-row__label' }, 'Emergency Bench Alerts'),
        h('p', { class: 'setting-row__help' },
          'Immediate ping whenever a syndicate member calls a sub or lists a ticket in the Firepit.'),
      ),
      toggle(p.benchAlerts, 'Emergency Bench Alerts', (v) => { S.setPref('benchAlerts', v); repaint(); }, { ember: true }),
    ),
  );
}

function notesSection(p, repaint) {
  return h('section', { class: 'card' },
    h('h2', { class: 'card__title' }, 'Hearthside Notes'),

    h('div', { class: 'setting-row' },
      h('div', { class: 'setting-row__body' },
        h('p', { class: 'setting-row__label' }, 'Daily Player Bio & Lore'),
        h('p', { class: 'setting-row__help' },
          'Receive one daily flashcard profile to learn league players and tactical matchups.'),
      ),
      toggle(p.dailyBio, 'Daily Player Bio and Lore', (v) => { S.setPref('dailyBio', v); repaint(); }),
    ),

    p.dailyBio
      ? h('div', null,
          h('div', { role: 'radiogroup', 'aria-label': 'Which players you see', style: { marginTop: '12px' } },
            SCOPES.map((s) => h('button', {
              class: 'path',
              type: 'button',
              role: 'radio',
              'aria-checked': String(p.bioScope === s.value),
              style: p.bioScope === s.value
                ? { borderColor: 'var(--summit-green)', background: 'var(--surface-sunk)' }
                : {},
              onclick: () => { S.setPref('bioScope', s.value); repaint(); },
            },
              h('div', null,
                h('p', { class: 'path__name', style: { margin: '0' } }, s.label),
                h('p', { class: 'path__help' }, s.help),
              ),
            )),
          ),
          h('label', { style: { display: 'block', marginTop: '6px' } },
            h('span', { class: 'field__label' }, 'Preferred delivery time'),
            h('select', {
              class: 'select',
              style: { maxWidth: '160px' },
              onchange: (e) => { S.setPref('bioTime', e.target.value); repaint(); },
            }, TIMES.map((t) => h('option', { value: t, selected: t === p.bioTime }, label12(t)))),
          ),
        )
      : null,
  );
}

function profileSection(p, repaint) {
  const syn = S.syndicate();
  const seat = syn.seats[0];
  return h('section', { class: 'card' },
    h('h2', { class: 'card__title' }, 'Group & profile'),
    h('label', { class: 'field' },
      h('span', { class: 'field__label' }, 'Display name'),
      h('input', {
        class: 'input', value: p.displayName,
        onchange: (e) => S.setPref('displayName', e.target.value),
      }),
    ),
    h('div', { class: 'card card--sunk', style: { marginBottom: '12px' } },
      h('p', { class: 'eyebrow' }, 'Seat assignment'),
      h('p', { style: { margin: '4px 0 0', fontWeight: '600' } },
        `Sec ${seat.section}, Row ${seat.row}, Seat ${seat.number}`),
      h('p', { style: { margin: '2px 0 0', fontSize: '13px', color: 'var(--ink-mute)' } }, syn.name),
    ),
    h('p', { style: { margin: '0 0 10px', fontSize: '13px', color: 'var(--ink-mute)' } },
      'Fallback contacts, used only for critical ticket transfers.'),
    h('label', { class: 'field' },
      h('span', { class: 'field__label' }, 'Phone'),
      h('input', { class: 'input', type: 'tel', value: p.phone, placeholder: '(303) 555-0142',
        onchange: (e) => S.setPref('phone', e.target.value) }),
    ),
    h('label', { class: 'field' },
      h('span', { class: 'field__label' }, 'Email'),
      h('input', { class: 'input', type: 'email', value: p.email, placeholder: 'you@example.com',
        onchange: (e) => S.setPref('email', e.target.value) }),
    ),
    h('button', {
      class: 'btn btn--ghost btn--block', type: 'button',
      onclick: () => { S.signOut(); },
    }, 'Sign out'),
  );
}

/** What the alerts will actually look like on a lock screen. */
function previewSection(p) {
  const next = S.nextFixture();
  const scope = SCOPES.find((s) => s.value === p.bioScope);

  const lockCard = (title, body, when) => h('div', {
    class: 'card card--sunk',
    style: { marginBottom: '10px', borderRadius: '14px' },
  },
    h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '8px' } },
      h('p', { style: { margin: '0', fontWeight: '700', fontSize: '14px' } }, title),
      h('span', { class: 'eyebrow' }, when),
    ),
    h('p', { style: { margin: '6px 0 0', fontSize: '13px', color: 'var(--ink-soft)' } }, body),
  );

  return h('section', { class: 'card' },
    h('h2', { class: 'card__title' }, 'Sample alert preview'),
    lockCard(
      '🏔️ Match Check-in',
      `Denver Summit FC vs. ${next?.opponent ?? 'Bay FC'} is in 3 days. Are you taking the pitch? [ Confirm Seat ] or [ Call a Sub ]`,
      label12(p.checkinTime),
    ),
    lockCard(
      '⚽ Hearthside Scout',
      `Meet visiting forward Marisol Vega (Portland Thorns) — 3 key stats & tactical tendencies ahead of Saturday's clash.`,
      label12(p.bioTime),
    ),
    h('p', { style: { margin: '4px 0 0', fontSize: '12px', color: 'var(--ink-mute)' } },
      `Mix: ${scope?.label ?? ''}.`),
  );
}

function label12(hhmm) {
  const [h24, m] = hhmm.split(':').map(Number);
  const suffix = h24 >= 12 ? 'PM' : 'AM';
  const hr = h24 % 12 === 0 ? 12 : h24 % 12;
  return `${hr}:${String(m).padStart(2, '0')} ${suffix}`;
}
