import { h, svg, icons, money, matchDate, matchTime, badge } from '../components/ui.js';
import * as S from '../state.js';
import { members, me } from '../data/mock.js';

export function benchView() {
  const open = S.openSeats();
  const onBench = open.filter((o) => o.seat.status === 'bench');
  const listed = open.filter((o) => o.seat.status === 'listed');

  return h('div', { class: 'view shell', style: { paddingTop: '16px' } },
    h('h1', { style: { fontSize: '22px', fontWeight: '800' } }, 'The Bench'),
    h('p', { style: { margin: '4px 0 14px', fontSize: '14px', color: 'var(--ink-mute)' } },
      'Seats nobody is holding, and anything the circle has listed outside.'),

    section('Waiting for a sub', onBench, (o) => seatCard(o, true)),
    section('Listed outside the Hearth', listed, (o) => seatCard(o, false)),

    !open.length
      ? h('p', { class: 'card', style: { color: 'var(--ink-mute)' } }, 'The bench is empty — every seat has someone on it.')
      : null,
  );
}

function section(title, rows, render) {
  if (!rows.length) return null;
  return h('section', { style: { marginBottom: '18px' } },
    h('h2', { style: { fontSize: '15px', margin: '0 0 8px' } }, title),
    h('div', { class: 'grid-auto' }, rows.map(render)),
  );
}

function seatCard({ fixture, seat }, claimable) {
  const note = S.noteFor(fixture.id, seat.number);
  const free = note?.costPath === 'free';

  return h('article', {
    class: 'card',
    style: { borderLeft: `3px solid ${claimable ? 'var(--summit-sandstone)' : 'var(--hairline-strong)'}` },
  },
    h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' } },
      h('div', null,
        h('p', { class: 'eyebrow' }, `${matchDate(fixture.kickoff)} · ${matchTime(fixture.kickoff)}`),
        h('p', { style: { margin: '4px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '17px' } },
          `vs ${fixture.opponent}`),
        h('p', { style: { margin: '2px 0 0', fontSize: '13px', color: 'var(--ink-mute)' } },
          `Seat ${seat.number} · Sec ${S.syndicate().seats[0].section}, Row ${S.syndicate().seats[0].row}`),
      ),
      fixture.tier === 'rivalry' ? badge('Rivalry', 'gold') : null,
    ),

    note ? h('p', { style: { margin: '10px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } },
      `“${note.body}” — ${members[note.authorId]?.name ?? 'Someone'}`) : null,

    h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', flexWrap: 'wrap' } },
      claimable
        ? (free ? badge('On the house', 'gold') : badge(`${money(note?.amountCents ?? fixture.valueCents)} to take it`, 'green'))
        : badge(`Asking ${money(seat.askCents ?? fixture.valueCents)}`, 'ember'),
    ),

    claimable
      ? h('button', {
          class: 'btn btn--primary btn--block', type: 'button', style: { marginTop: '12px' },
          onclick: () => S.claimSeat(fixture.id, seat.number, me),
        }, 'Claim from Bench')
      : h('div', { style: { display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' } },
          h('a', {
            class: 'btn btn--ghost',
            href: 'https://seatgeek.com/', target: '_blank', rel: 'noopener noreferrer',
          }, svg(icons.external, { size: 16 }), 'View listing'),
          h('button', {
            class: 'btn btn--ghost', type: 'button',
            onclick: () => S.claimSeat(fixture.id, seat.number, me),
          }, 'Pull it back'),
        ),
  );
}
