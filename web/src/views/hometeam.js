import { h, fill, svg, icons, badge, chipRow, photoSlot } from '../components/ui.js';
import * as S from '../state.js';
import { squad, positions } from '../data/mock.js';

let filter = 'Whole squad';

export function homeTeamView() {
  const wrap = h('div', { class: 'view shell', style: { paddingTop: '16px' } });

  const paint = () => {
    const rows = filter === 'Whole squad' ? squad : squad.filter((p) => p.pos === filter);
    fill(wrap,
      h('h1', { style: { fontSize: '22px', fontWeight: '800' } }, 'The Locker Room'),
      h('p', { style: { margin: '4px 0 12px', fontSize: '14px', color: 'var(--ink-mute)' } },
        'Denver Summit FC, top to bottom. Tap a player to pull their card off the peg.'),
      chipRow(positions, filter, (v) => { filter = v; paint(); }),
      // Cards sit at their natural height rather than stretching to an
      // expanded neighbour.
      h('div', {
        class: 'grid-auto',
        style: { marginTop: '12px', alignItems: 'start' },
      }, rows.map(playerCard)),
    );
  };

  paint();
  return wrap;
}

function playerCard(p) {
  let open = false;
  const card = h('article', { class: 'card' });

  const paint = () => {
    fill(card,
      h('div', { style: { display: 'flex', gap: '12px' } },
        photoSlot(p.id, 92, S.get().photos[p.id], (url) => { S.setPhoto(p.id, url); paint(); }),
        h('div', { style: { minWidth: '0', flex: '1' } },
          h('p', { style: { margin: '0', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' } },
            badge(`#${p.num}`, 'gold'),
            h('a', {
              href: `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(p.name)}`,
              target: '_blank', rel: 'noopener noreferrer',
              style: { fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '16px' },
            }, p.name),
          ),
          h('p', { style: { margin: '3px 0 0', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--ink-mute)' } },
            p.pos),
          h('div', { style: { display: 'flex', gap: '10px', marginTop: '8px', flexWrap: 'wrap' } },
            h('a', {
              href: 'https://www.denversummitfc.com/roster',
              target: '_blank', rel: 'noopener noreferrer',
              style: { fontSize: '13px' },
            }, 'Club bio ↗'),
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
        style: { marginTop: '12px' },
        'aria-expanded': String(open),
        onclick: () => { open = !open; paint(); },
      }, open ? 'Close' : 'Scouting note'),
      open
        ? h('div', { style: { marginTop: '12px', animation: 'ssPop .18s ease both' } },
            h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
              p.stats.map(([k, v]) => h('div', {
                class: 'card card--sunk',
                style: { padding: '8px 12px', borderRadius: '10px', flex: '1 1 92px' },
              },
                h('p', { class: 'eyebrow' }, k),
                h('p', { style: { margin: '2px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '17px' } }, v),
              )),
            ),
            h('p', { style: { margin: '10px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } }, p.note),
          )
        : null,
    );
  };

  paint();
  return card;
}
