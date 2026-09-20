import { h, fill, svg, icons, money, matchDate, matchTime, relative, avatar, badge } from '../components/ui.js';
import { callASubSheet } from '../components/callasub.js';
import * as S from '../state.js';
import { members, me, tiers, quickReplies, hearthsideNotes } from '../data/mock.js';

export function matchdayView() {
  const fixture = S.nextFixture();
  const notes = S.get().benchNotes;

  return h('div', { class: 'view shell', style: { paddingTop: '16px' } },
    h('div', { class: 'grid-auto', style: { gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' } },
      fixture ? heroCard(fixture) : h('div', { class: 'card' }, 'No fixtures left this season.'),
      hearthsideNotesCard(),
    ),
    notes.length
      ? h('section', { style: { marginTop: '12px' } },
          h('h2', { style: { fontSize: '15px', margin: '0 0 8px' } }, 'Bench notes'),
          h('div', { class: 'grid-auto' }, notes.map(noteThread)),
        )
      : null,
    balancesStrip(),
  );
}

/** Evergreen hero with a sandstone ember along the top edge. */
function heroCard(f) {
  const tier = tiers[f.tier];
  const mySeat = f.seats.find((s) => s.holder === me);

  const roster = h('div', { style: { display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '14px' } },
    f.seats.map((seat) => h('div', {
      style: { display: 'flex', alignItems: 'center', gap: '8px' },
    },
      avatar(seat.holder ? members[seat.holder] : null, { lg: true }),
      h('div', null,
        h('p', { style: { margin: '0', fontSize: '13px', fontWeight: '600', color: '#fff' } },
          seat.holder ? members[seat.holder].name
            : seat.status === 'gifted' ? (seat.guestName ?? 'Guest')
            : seat.status === 'listed' ? 'Listed outside'
            : 'On the bench'),
        h('p', { style: { margin: '0', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'rgba(255,255,255,.62)' } },
          `Seat ${seat.number}`),
      ),
    )),
  );

  return h('article', {
    style: {
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      background: '#134E48',
      color: '#fff',
      borderTop: '3px solid #C84B31',
      padding: '18px 16px',
      animation: 'ssUp .3s ease both',
    },
  },
    h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'flex-start' } },
      h('div', null,
        h('p', { class: 'eyebrow', style: { color: 'rgba(255,255,255,.66)' } }, 'Next match'),
        h('h2', { style: { fontSize: '24px', fontWeight: '800', marginTop: '4px', color: '#fff' } },
          `Summit vs ${f.opponent}`),
        h('p', { style: { margin: '6px 0 0', fontSize: '14px', color: 'rgba(255,255,255,.8)' } },
          `${matchDate(f.kickoff)} · ${matchTime(f.kickoff)} · ${f.venue}`),
      ),
      f.tier === 'rivalry' ? badge('Rivalry', 'gold') : null,
    ),
    h('p', { class: 'eyebrow', style: { color: 'rgba(255,255,255,.66)', marginTop: '16px' } }, 'Taking the pitch'),
    roster,
    h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '16px' } },
      mySeat
        ? h('button', {
            class: 'btn btn--ember',
            type: 'button',
            onclick: () => callASubSheet(f, mySeat),
          }, 'Call a Sub')
        : null,
      h('a', {
        class: 'btn btn--on-dark',
        href: 'https://www.ticketmaster.com/',
        target: '_blank',
        rel: 'noopener noreferrer',
      }, svg(icons.external, { size: 16 }), 'Open Official Ticketing App'),
    ),
  );
}

/** Hearthside Notes: swipeable key player, tactical note and tap-to-reveal trivia. */
function hearthsideNotesCard() {
  let index = 0;
  const wrap = h('article', { class: 'card', style: { display: 'flex', flexDirection: 'column' } });

  const paint = () => {
    const note = hearthsideNotes[index];
    fill(wrap,
      h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
        svg(icons.flame, { size: 16, stroke: 'var(--summit-sandstone)' }),
        h('p', { class: 'eyebrow' }, 'Hearthside Notes'),
      ),
      h('div', { style: { flex: '1', marginTop: '10px', animation: 'ssPop .2s ease both' } }, body(note)),
      h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '14px', gap: '10px' } },
        h('div', { style: { display: 'flex', gap: '6px' } },
          hearthsideNotes.map((_, i) => h('span', {
            'aria-hidden': 'true',
            style: {
              width: i === index ? '18px' : '6px', height: '6px', borderRadius: '999px',
              background: i === index ? 'var(--summit-green)' : 'var(--hairline-strong)',
              transition: 'width .2s ease',
            },
          })),
        ),
        h('div', { style: { display: 'flex', gap: '6px' } },
          h('button', {
            class: 'btn btn--ghost', type: 'button', style: { minHeight: '36px', padding: '0 12px' },
            'aria-label': 'Previous note',
            onclick: () => { index = (index - 1 + hearthsideNotes.length) % hearthsideNotes.length; paint(); },
          }, '‹'),
          h('button', {
            class: 'btn btn--ghost', type: 'button', style: { minHeight: '36px', padding: '0 12px' },
            'aria-label': 'Next note',
            onclick: () => { index = (index + 1) % hearthsideNotes.length; paint(); },
          }, '›'),
        ),
      ),
    );
  };

  const body = (note) => {
    if (note.kind === 'player') {
      return h('div', { style: { display: 'flex', gap: '12px' } },
        h('div', {
          'aria-hidden': 'true',
          style: {
            width: '64px', height: '64px', borderRadius: '12px', flex: 'none',
            background: 'repeating-linear-gradient(135deg, var(--surface-sunk) 0 8px, var(--hairline) 8px 16px)',
          },
        }),
        h('div', null,
          h('p', { class: 'eyebrow' }, note.eyebrow),
          h('p', { style: { margin: '4px 0 0', display: 'flex', alignItems: 'center', gap: '8px' } },
            badge(`#${note.num}`, 'gold'),
            h('strong', { style: { fontFamily: 'var(--font-display)', fontSize: '16px' } }, note.name),
          ),
          h('p', { style: { margin: '2px 0 0', fontSize: '12px', color: 'var(--ink-mute)' } }, note.pos),
          h('p', { style: { margin: '8px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } }, note.body),
        ),
      );
    }
    if (note.kind === 'tactics') {
      return h('div', null,
        h('p', { class: 'eyebrow' }, note.eyebrow),
        h('p', { style: { margin: '6px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '16px' } }, note.name),
        h('p', { style: { margin: '8px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } }, note.body),
      );
    }
    // Trivia: tap to reveal.
    let shown = false;
    const answer = h('p', { style: { margin: '10px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } });
    const btn = h('button', {
      class: 'btn btn--ghost btn--block',
      type: 'button',
      style: { marginTop: '10px' },
      'aria-expanded': 'false',
      onclick: () => {
        shown = !shown;
        answer.textContent = shown ? note.answer : '';
        btn.textContent = shown ? 'Hide' : 'Tap to reveal';
        btn.setAttribute('aria-expanded', String(shown));
      },
    }, 'Tap to reveal');
    return h('div', null,
      h('p', { class: 'eyebrow' }, note.eyebrow),
      h('p', { style: { margin: '6px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '16px' } }, note.question),
      answer,
      btn,
    );
  };

  paint();
  return wrap;
}

/** A released seat's note thread: note, cost badge, replies, hand-off. */
function noteThread(note) {
  const fixture = S.get().fixtures.find((f) => f.id === note.fixtureId);
  const seat = fixture?.seats.find((s) => s.number === note.seatNumber);
  const author = members[note.authorId];
  const taken = seat?.status === 'confirmed';

  const replyBox = h('input', { class: 'input', placeholder: 'Reply to the circle', 'aria-label': 'Reply' });

  return h('article', { class: 'card' },
    h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'flex-start' } },
      h('div', { style: { display: 'flex', gap: '10px' } },
        avatar(author),
        h('div', null,
          h('p', { style: { margin: '0', fontWeight: '600', fontSize: '14px' } },
            `${author.name} · ${fixture?.short ?? ''} · Seat ${note.seatNumber}`),
          h('p', { class: 'eyebrow', style: { marginTop: '2px' } }, relative(note.postedAt)),
        ),
      ),
      note.costPath === 'repay'
        ? badge(`Get paid back · ${money(note.amountCents)}`, 'green')
        : badge('On the house', 'gold'),
    ),
    h('p', { style: { margin: '10px 0 0', fontSize: '15px' } }, note.body),

    note.replies.length
      ? h('div', { style: { marginTop: '12px', borderLeft: '2px solid var(--hairline)', paddingLeft: '10px' } },
          note.replies.map((r) => h('p', { style: { margin: '0 0 6px', fontSize: '14px' } },
            h('strong', null, `${members[r.authorId]?.name ?? 'Someone'}: `),
            r.body,
          )),
        )
      : null,

    taken
      ? h('p', { style: { margin: '12px 0 0', fontSize: '14px', color: 'var(--summit-green)', fontWeight: '600' } },
          `${members[seat.holder]?.name ?? 'Someone'} took the seat.`)
      : h('div', null,
          h('div', { class: 'scroll-row', style: { marginTop: '12px' } },
            quickReplies.map((q) => h('button', {
              class: 'chip', type: 'button',
              onclick: () => S.addReply(note.id, q),
            }, q)),
          ),
          h('div', { style: { display: 'flex', gap: '8px', marginTop: '10px' } },
            replyBox,
            h('button', {
              class: 'btn btn--ghost', type: 'button', style: { flex: 'none' },
              onclick: () => S.addReply(note.id, replyBox.value),
            }, 'Send'),
          ),
          h('button', {
            class: 'btn btn--primary btn--block', type: 'button', style: { marginTop: '10px' },
            onclick: () => S.handOffTo(note.id, me),
          }, note.costPath === 'repay' ? `Take the Pitch · ${money(note.amountCents)}` : 'Take the Pitch · no cost'),
        ),
  );
}

function balancesStrip() {
  const cents = S.myBalanceCents();
  const line = cents === 0
    ? 'All warm at the Hearth.'
    : cents > 0
      ? `The circle holds your ${money(cents)}.`
      : `You hold the tab (${money(Math.abs(cents))}).`;

  return h('button', {
    class: 'card',
    type: 'button',
    style: {
      marginTop: '12px', width: '100%', textAlign: 'left', cursor: 'pointer',
      borderLeft: '3px solid var(--summit-sunshine)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px',
    },
    onclick: () => S.set({ tab: 'hearth' }),
  },
    h('div', null,
      h('p', { class: 'eyebrow' }, 'The Hearth'),
      h('p', { style: { margin: '4px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '16px' } }, line),
    ),
    svg(icons.arrowRight, { size: 18 }),
  );
}
