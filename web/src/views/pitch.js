import { h, fill, money, matchDate, matchTime, avatar, badge, chipRow } from '../components/ui.js';
import { callASubSheet } from '../components/callasub.js';
import * as S from '../state.js';
import { members, me, tiers } from '../data/mock.js';

const FILTERS = [
  { value: 'all',   label: 'All Fixtures' },
  { value: 'mine',  label: 'My Matches' },
  { value: 'bench', label: 'On the Bench' },
];

let filter = 'all';

export function pitchView() {
  const wrap = h('div', { class: 'view shell', style: { paddingTop: '16px' } });

  const paint = () => {
    const rows = S.seasonFixtures().filter((f) => {
      if (filter === 'mine') return f.seats.some((s) => s.holder === me);
      if (filter === 'bench') return f.seats.some((s) => s.status === 'bench' || s.status === 'listed');
      return true;
    });

    fill(wrap,
      h('h1', { style: { fontSize: '22px', fontWeight: '800' } }, 'The Pitch'),
      h('p', { style: { margin: '4px 0 12px', fontSize: '14px', color: 'var(--ink-mute)' } },
        `Every home fixture in the ${S.get().seasonYear} package, in order.`),
      chipRow(FILTERS, filter, (v) => { filter = v; paint(); }),
      rows.length
        ? h('div', { class: 'grid-auto', style: { marginTop: '12px' } }, rows.map(fixtureRow))
        : h('p', { class: 'card', style: { marginTop: '12px', color: 'var(--ink-mute)' } }, 'Nothing here for this filter.'),
    );
  };

  paint();
  return wrap;
}

export function statusPill(f) {
  if (S.isPast(f)) return badge('Past', 'mute');
  const bench = f.seats.filter((s) => s.status === 'bench').length;
  const listed = f.seats.filter((s) => s.status === 'listed').length;
  if (bench) return badge(`${bench} seat${bench > 1 ? 's' : ''} on the bench`, 'ember');
  if (listed) return badge('Listed outside', 'ember');
  const names = f.seats
    .map((s) => (s.holder ? members[s.holder].name : s.guestName))
    .filter(Boolean)
    .join(' & ');
  return badge(`Starting · ${names}`, 'green');
}

function fixtureRow(f) {
  const past = S.isPast(f);
  const tier = tiers[f.tier];
  const mySeat = f.seats.find((s) => s.holder === me);
  const openSeat = f.seats.find((s) => s.status === 'bench');

  return h('article', {
    class: 'card',
    style: past ? { opacity: '.62' } : {},
  },
    h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' } },
      h('div', null,
        h('p', { class: 'eyebrow' }, `${matchDate(f.kickoff)} · ${matchTime(f.kickoff)}`),
        h('p', { style: { margin: '4px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '17px' } },
          `vs ${f.opponent}`),
        h('p', { style: { margin: '2px 0 0', fontSize: '13px', color: 'var(--ink-mute)' } }, f.venue),
      ),
      h('div', { style: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' } },
        // Rivalry tier reads gold; standard midweek stays quiet.
        f.tier === 'rivalry' ? badge('Rivalry', 'gold') : badge(tier.label, 'mute'),
        h('span', { style: { fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--ink-mute)' } },
          `${money(f.valueCents)} / seat`),
      ),
    ),
    h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', flexWrap: 'wrap' } },
      f.seats.map((s) => avatar(s.holder ? members[s.holder] : null)),
      statusPill(f),
    ),
    !past && (mySeat || openSeat)
      ? h('div', { style: { display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' } },
          mySeat ? h('button', {
            class: 'btn btn--ghost', type: 'button',
            onclick: () => callASubSheet(f, mySeat),
          }, 'Call a Sub') : null,
          openSeat ? h('button', {
            class: 'btn btn--primary', type: 'button',
            onclick: () => S.claimSeat(f.id, openSeat.number),
          }, 'Take the Pitch') : null,
        )
      : null,
  );
}
