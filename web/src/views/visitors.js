import { h, fill, badge, chipRow, photoSlot } from '../components/ui.js';
import * as S from '../state.js';
import { opponents } from '../data/mock.js';

let activeId = opponents[0].id;

/* The room down the tunnel from the Hearth: bare block walls, a bench an inch
   out of true, a team sheet taped over last week's. The dishevelment is
   cosmetic — tilts stay under 0.6°, nothing animates, and every piece of text
   sits on a solid surface at full contrast. */

const CONCRETE = 'repeating-linear-gradient(180deg, rgba(120,113,108,.07) 0 38px, rgba(120,113,108,.12) 38px 39px)';

export function visitorsView() {
  const wrap = h('div', { class: 'view shell', style: { paddingTop: '16px' } });

  const paint = () => {
    const op = opponents.find((o) => o.id === activeId) ?? opponents[0];

    fill(wrap,
      room(),
      h('div', { style: { marginTop: '14px' } },
        chipRow(opponents.map((o) => ({ value: o.id, label: o.chip })), activeId,
          (v) => { activeId = v; paint(); }, { stone: true }),
      ),
      dossier(op),
    );
  };

  paint();
  return wrap;
}

function room() {
  return h('section', {
    style: {
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--hairline-strong)',
      background: `${CONCRETE}, var(--surface-sunk)`,
      padding: '18px 16px',
      position: 'relative',
    },
  },
    // Taped sign, slightly off true.
    h('div', {
      style: {
        display: 'inline-block',
        transform: 'rotate(-0.5deg)',
        background: '#E7E2D4',
        color: '#1C1917',
        border: '1px solid #C9C2AE',
        padding: '6px 14px',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        letterSpacing: '.14em',
        fontWeight: '500',
      },
    }, 'AWAY · 5,280 FT'),

    h('h1', { style: { fontSize: '22px', fontWeight: '800', marginTop: '12px' } },
      "The Visiting Club's Dressing Room"),
    h('p', { style: { margin: '8px 0 0', fontSize: '14px', color: 'var(--ink-soft)', maxWidth: '58ch' } },
      'Down the tunnel from the Hearth: bare block walls, a bench an inch out of true, and a team sheet taped over last week’s. Everything you need on whoever is in town.'),

    // The team sheet: every club, both legs.
    h('div', {
      style: {
        marginTop: '16px',
        transform: 'rotate(0.4deg)',
        background: 'var(--surface)',
        border: '1px solid var(--hairline-strong)',
        padding: '14px',
        borderRadius: '4px',
      },
    },
      h('p', { class: 'eyebrow' }, 'Team sheet'),
      h('div', { style: { marginTop: '8px' } },
        opponents.map((o) => h('div', {
          style: {
            display: 'flex', justifyContent: 'space-between', gap: '10px',
            padding: '7px 0', borderBottom: '1px solid var(--hairline)', fontSize: '13px',
          },
        },
          h('span', { style: { fontWeight: '600' } }, o.club),
          h('span', { style: { fontFamily: 'var(--font-mono)', color: 'var(--ink-mute)', textAlign: 'right' } },
            `HOME ${o.homeDate} · AWAY ${o.awayDate}`),
        )),
      ),
      h('p', { style: { margin: '10px 0 0', fontSize: '12px', color: 'var(--ink-mute)' } },
        'Away dates are for travel planning only — they sit outside the season package.'),
    ),
  );
}

function dossier(op) {
  return h('section', { style: { marginTop: '14px' } },
    h('article', { class: 'card' },
      h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' } },
        h('div', null,
          h('h2', { style: { fontSize: '19px', fontWeight: '800' } }, op.club),
          h('p', { style: { margin: '4px 0 0', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--ink-mute)' } },
            `HOME ${op.homeDate} · AWAY ${op.awayDate}`),
          h('p', { style: { margin: '2px 0 0', fontSize: '13px', color: 'var(--ink-mute)' } },
            `Away leg at ${op.awayVenue} — outside the package.`),
        ),
        h('div', null,
          h('p', { class: 'eyebrow' }, 'Form'),
          h('p', { style: { margin: '4px 0 0', fontFamily: 'var(--font-mono)', fontWeight: '500', letterSpacing: '.18em' } }, op.form),
        ),
      ),

      h('div', { style: { display: 'flex', gap: '8px', marginTop: '14px', flexWrap: 'wrap' } },
        op.quickStats.map(([k, v]) => h('div', {
          class: 'card card--sunk',
          style: { padding: '8px 12px', borderRadius: '10px', flex: '1 1 96px' },
        },
          h('p', { class: 'eyebrow' }, k),
          h('p', { style: { margin: '2px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '18px' } }, v),
        )),
      ),

      h('div', {
        style: {
          marginTop: '14px', padding: '12px 14px', borderRadius: '10px',
          background: 'rgba(200,75,49,.1)', borderLeft: '3px solid var(--summit-sandstone)',
        },
      },
        h('p', { class: 'eyebrow', style: { color: 'var(--summit-sandstone)' } }, 'Halftime read'),
        h('p', { style: { margin: '5px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } }, op.halftime),
      ),

      h('p', { style: { margin: '14px 0 0', fontSize: '14px' } },
        h('strong', null, 'Shape: '), op.shape),
    ),

    h('p', { class: 'eyebrow', style: { margin: '16px 0 8px' } }, 'Dressing room occupants'),
    h('div', { class: 'grid-auto', style: { alignItems: 'start' } }, op.players.map(pegCard)),
  );
}

/** Each player reads as a kit peg you tap to pull the shirt off the hook. */
function pegCard(p) {
  let open = false;
  const card = h('article', {
    class: 'card',
    style: { transform: `rotate(${(p.num % 2 ? -0.35 : 0.3)}deg)` },
  });

  const paint = () => {
    fill(card,
      h('div', { style: { display: 'flex', gap: '12px' } },
        photoSlot(p.id, 84, S.get().photos[p.id], (url) => { S.setPhoto(p.id, url); paint(); }),
        h('div', { style: { flex: '1', minWidth: '0' } },
          h('p', { style: { margin: '0', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' } },
            badge(`#${p.num}`, 'gold'),
            h('a', {
              href: `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(p.name)}`,
              target: '_blank', rel: 'noopener noreferrer',
              style: { fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '15px' },
            }, p.name),
            p.danger ? badge('DANGER', 'ember') : null,
          ),
          h('p', { style: { margin: '3px 0 0', fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--ink-mute)' } }, p.pos),
          h('div', { style: { display: 'flex', gap: '10px', marginTop: '6px', flexWrap: 'wrap' } },
            h('a', { href: '#', style: { fontSize: '13px' }, onclick: (e) => e.preventDefault() }, 'Club bio ↗'),
            h('a', {
              href: `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(p.name)}`,
              target: '_blank', rel: 'noopener noreferrer',
              style: { fontSize: '13px' },
            }, 'Wikipedia ↗'),
          ),
        ),
      ),
      h('button', {
        class: 'btn btn--ghost btn--block',
        type: 'button',
        style: { marginTop: '10px' },
        'aria-expanded': String(open),
        onclick: () => { open = !open; paint(); },
      }, open ? 'Back on the hook' : 'Pull it off the hook'),
      open
        ? h('p', { style: { margin: '10px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } }, p.note)
        : null,
    );
  };

  paint();
  return card;
}
