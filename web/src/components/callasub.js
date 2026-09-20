import { h, svg, icons, money, openSheet, closeSheet } from './ui.js';
import * as S from '../state.js';

/** The three pathways a seat can leave your hands. */
export function callASubSheet(fixture, seat) {
  const path = (icon, tint, name, help, onPick) => h('button', {
    class: 'path', type: 'button', onclick: onPick,
  },
    h('div', { class: 'path__icon', style: { background: tint } }, svg(icon, { size: 19, stroke: '#fff' })),
    h('div', null,
      h('p', { class: 'path__name', style: { margin: '0' } }, name),
      h('p', { class: 'path__help' }, help),
    ),
  );

  openSheet(h('div', null,
    h('p', { class: 'eyebrow' }, `${fixture.opponent} · Seat ${seat.number}`),
    h('h2', { class: 'sheet__title' }, 'Call a sub'),
    h('p', { class: 'sheet__sub' }, "Pick how the seat leaves your hands. Nothing moves on the tab until you confirm."),
    path(icons.users, '#134E48', 'Release to the Bench',
      'Pings the circle to see who wants to step onto the pitch.',
      () => releaseForm(fixture, seat)),
    path(icons.gift, '#1D6960', 'Send to Guest',
      'Direct transfer to someone outside the circle. The seat stays accounted for.',
      () => guestForm(fixture, seat)),
    path(icons.tag, '#C84B31', 'List Outside the Hearth',
      'Flag it for SeatGeek or Ticketmaster at a target face value.',
      () => listForm(fixture, seat)),
    h('button', { class: 'btn btn--ghost btn--block', type: 'button', onclick: closeSheet }, 'Never mind'),
  ));
}

/** Release to the Bench: a note to the circle plus an explicit cost choice. */
function releaseForm(fixture, seat) {
  let costPath = 'repay';
  const face = fixture.valueCents;

  const note = h('textarea', {
    class: 'textarea',
    id: 'release-note',
    placeholder: "Out of town that weekend — seat's free if anyone wants it.",
  });

  const choice = (value, title, help) => {
    const btn = h('button', {
      class: 'path', type: 'button',
      'aria-pressed': String(costPath === value),
      onclick: () => {
        costPath = value;
        for (const b of group.querySelectorAll('button')) {
          b.setAttribute('aria-pressed', String(b.dataset.value === value));
          b.style.borderColor = b.dataset.value === value ? 'var(--summit-green)' : '';
          b.style.background = b.dataset.value === value ? 'var(--surface-sunk)' : '';
        }
      },
      dataset: { value },
    },
      h('div', null,
        h('p', { class: 'path__name', style: { margin: '0' } }, title),
        h('p', { class: 'path__help' }, help),
      ),
    );
    if (costPath === value) {
      btn.style.borderColor = 'var(--summit-green)';
      btn.style.background = 'var(--surface-sunk)';
    }
    return btn;
  };

  const group = h('div', { role: 'group', 'aria-label': 'Cost' },
    choice('repay', `Get paid back · ${money(face)}`, 'Face value moves to whoever takes the seat.'),
    choice('free', 'On the house · no cost', "You eat it. Nobody's tab moves."),
  );

  openSheet(h('div', null,
    h('p', { class: 'eyebrow' }, `${fixture.opponent} · Seat ${seat.number}`),
    h('h2', { class: 'sheet__title' }, 'Release to the Bench'),
    h('p', { class: 'sheet__sub' }, 'Leave a note for the circle. Anyone can reply, and whoever takes it steps onto the pitch.'),
    h('label', { class: 'field__label', for: 'release-note' }, 'Note to the circle'),
    note,
    h('p', { class: 'field__label', style: { marginTop: '10px' } }, 'Cost'),
    group,
    h('button', {
      class: 'btn btn--primary btn--block',
      type: 'button',
      style: { marginTop: '6px' },
      onclick: () => {
        S.releaseToBench(fixture.id, seat.number, {
          body: note.value.trim() || 'Seat is open — who wants it?',
          costPath,
          amountCents: costPath === 'repay' ? face : 0,
        });
        closeSheet();
      },
    }, 'Post to the Bench'),
    h('button', { class: 'btn btn--ghost btn--block', type: 'button', style: { marginTop: '8px' }, onclick: closeSheet }, 'Back'),
  ));
}

function guestForm(fixture, seat) {
  const name = h('input', { class: 'input', id: 'guest-name', placeholder: 'Name or email' });
  openSheet(h('div', null,
    h('p', { class: 'eyebrow' }, `${fixture.opponent} · Seat ${seat.number}`),
    h('h2', { class: 'sheet__title' }, 'Send to Guest'),
    h('p', { class: 'sheet__sub' }, "A straight gift. The seat stays accounted for and nobody's tab moves."),
    h('label', { class: 'field__label', for: 'guest-name' }, 'Who is taking it'),
    name,
    h('button', {
      class: 'btn btn--primary btn--block',
      type: 'button',
      style: { marginTop: '12px' },
      onclick: () => {
        S.sendToGuest(fixture.id, seat.number, name.value.trim() || 'Guest');
        closeSheet();
      },
    }, 'Send the seat'),
    h('button', { class: 'btn btn--ghost btn--block', type: 'button', style: { marginTop: '8px' }, onclick: closeSheet }, 'Back'),
  ));
}

function listForm(fixture, seat) {
  const ask = h('input', {
    class: 'input', id: 'ask', type: 'number', min: '0', step: '1',
    value: String(Math.round(fixture.valueCents / 100)),
  });
  openSheet(h('div', null,
    h('p', { class: 'eyebrow' }, `${fixture.opponent} · Seat ${seat.number}`),
    h('h2', { class: 'sheet__title' }, 'List Outside the Hearth'),
    h('p', { class: 'sheet__sub' }, 'Flags the seat as listed on an external exchange. You still handle the listing there.'),
    h('label', { class: 'field__label', for: 'ask' }, 'Target face value (USD)'),
    ask,
    h('button', {
      class: 'btn btn--ember btn--block',
      type: 'button',
      style: { marginTop: '12px' },
      onclick: () => {
        S.listOutside(fixture.id, seat.number, Math.max(0, Number(ask.value) || 0) * 100);
        closeSheet();
      },
    }, 'Mark as listed'),
    h('button', { class: 'btn btn--ghost btn--block', type: 'button', style: { marginTop: '8px' }, onclick: closeSheet }, 'Back'),
  ));
}
