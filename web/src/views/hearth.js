import { h, svg, icons, money, avatar, badge, openSheet, closeSheet } from '../components/ui.js';
import * as S from '../state.js';
import { members, me, seasons, tiers, settleApps } from '../data/mock.js';

export function hearthView() {
  const year = S.get().seasonYear;
  const l = S.ledgerFor(year);
  const mine = S.myBalanceCents();

  return h('div', { class: 'view shell', style: { paddingTop: '16px' } },
    h('h1', { style: { fontSize: '22px', fontWeight: '800' } }, 'The Hearth'),
    h('p', { style: { margin: '4px 0 12px', fontSize: '14px', color: 'var(--ink-mute)' } },
      'What the season costs, who is carrying it, and how to square up.'),

    balanceLine(mine),

    h('div', { class: 'grid-auto', style: { marginTop: '12px' } },
      packageCard(l, year),
      debtsCard(l),
      historyCard(),
    ),
  );
}

/** The one balance statement in the app, gold-bordered. */
function balanceLine(cents) {
  const text = cents === 0
    ? 'All warm at the Hearth.'
    : cents > 0
      ? `The circle holds your ${money(cents)}.`
      : `You hold the tab (${money(Math.abs(cents))}).`;

  return h('div', {
    class: 'card',
    style: { border: '1px solid var(--summit-sunshine)', background: 'rgba(246,190,0,.08)' },
  },
    h('p', { style: { margin: '0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '18px' } }, text),
    cents !== 0
      ? h('button', {
          class: 'btn btn--primary', type: 'button', style: { marginTop: '12px' },
          onclick: settleSheet,
        }, 'Settle Up')
      : null,
  );
}

function packageCard(l, year) {
  const byTier = S.seasonFixtures().reduce((acc, f) => {
    acc[f.tier] = (acc[f.tier] ?? 0) + f.valueCents * f.seats.length;
    return acc;
  }, {});

  return h('article', { class: 'card' },
    h('h2', { class: 'card__title' }, `${year} package`),
    h('p', { style: { margin: '0', fontFamily: 'var(--font-display)', fontWeight: '800', fontSize: '28px' } },
      money(l.packageCents)),
    h('p', { style: { margin: '2px 0 14px', fontSize: '13px', color: 'var(--ink-mute)' } },
      `${S.syndicate().seats.length} seats · ${S.syndicate().memberIds.length} in the circle`),

    h('p', { class: 'eyebrow' }, 'Weighted by tier'),
    h('div', { style: { marginTop: '8px' } },
      Object.entries(byTier).map(([tier, cents]) => {
        const pct = Math.round((cents / Object.values(byTier).reduce((a, b) => a + b, 0)) * 100);
        return h('div', { style: { marginBottom: '10px' } },
          h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: '13px' } },
            h('span', null, `${tiers[tier].label} · ×${tiers[tier].weight}`),
            h('span', { style: { fontFamily: 'var(--font-mono)' } }, `${money(cents)} · ${pct}%`),
          ),
          h('div', { style: { height: '6px', borderRadius: '999px', background: 'var(--surface-sunk)', marginTop: '5px' } },
            h('div', {
              style: {
                width: `${pct}%`, height: '100%', borderRadius: '999px',
                background: tier === 'rivalry' ? 'var(--summit-sunshine)' : 'var(--summit-green)',
              },
            }),
          ),
        );
      }),
    ),
  );
}

/** Simplified debts: the fewest transfers that square the circle. */
function debtsCard(l) {
  return h('article', { class: 'card' },
    h('h2', { class: 'card__title' }, 'Who holds the tab'),
    l.debts.length
      ? h('div', null, l.debts.map((d) => h('div', {
          style: {
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '10px 0', borderBottom: '1px solid var(--hairline)',
          },
        },
          avatar(members[d.from]),
          h('p', { style: { margin: '0', flex: '1', fontSize: '14px' } },
            h('strong', null, members[d.from].name),
            ' owes ',
            h('strong', null, members[d.to].name),
          ),
          h('span', { style: { fontFamily: 'var(--font-mono)', fontWeight: '500' } }, money(d.cents)),
        )))
      : h('p', { style: { margin: '0', fontSize: '14px', color: 'var(--ink-mute)' } }, 'All square.'),

    h('p', { class: 'eyebrow', style: { marginTop: '14px' } }, 'Everyone else'),
    h('div', { style: { marginTop: '8px' } },
      S.syndicate().memberIds
        .filter((id) => !l.debts.some((d) => d.from === id || d.to === id))
        .map((id) => h('p', { style: { margin: '0 0 6px', fontSize: '14px', color: 'var(--ink-mute)' } },
          `${members[id].name} is all square.`)),
    ),
  );
}

/** Tickets carry across years, first season to the next. */
function historyCard() {
  return h('article', { class: 'card' },
    h('h2', { class: 'card__title' }, 'Season history'),
    seasons.map((y) => {
      const l = S.ledgerFor(y.year);
      return h('button', {
        class: 'setting-row',
        type: 'button',
        style: { width: '100%', textAlign: 'left', alignItems: 'center', background: 'none', border: 'none', borderBottom: '1px solid var(--hairline)', cursor: 'pointer', font: 'inherit', color: 'inherit' },
        onclick: () => S.set({ seasonYear: y.year }),
      },
        h('div', { class: 'setting-row__body' },
          h('p', { class: 'setting-row__label' }, y.label),
          h('p', { class: 'setting-row__help' },
            l.debts.length ? `${l.debts.length} open transfer${l.debts.length > 1 ? 's' : ''}` : 'Settled'),
        ),
        h('span', { style: { fontFamily: 'var(--font-mono)', fontSize: '14px' } }, money(y.packageCents)),
      );
    }),
  );
}

/** Settle Up: deep links with the amount and memo already filled in. */
function settleSheet() {
  const cents = Math.abs(S.myBalanceCents());
  const owed = S.myBalanceCents() > 0;
  const next = S.nextFixture();
  const memo = `SquadSeats: Match vs. ${next?.short ?? 'Summit'}`;
  const amount = (cents / 100).toFixed(2);

  openSheet(h('div', null,
    h('p', { class: 'eyebrow' }, 'Settle up'),
    h('h2', { class: 'sheet__title' }, money(cents)),
    h('p', { class: 'sheet__sub' },
      owed ? 'What the circle owes you. Send the request and it lands with the amount filled in.'
           : 'What you owe. Each button opens with the amount and memo already set.'),
    h('div', { class: 'card card--sunk', style: { marginBottom: '14px' } },
      h('p', { class: 'eyebrow' }, 'Memo'),
      h('p', { style: { margin: '4px 0 0', fontFamily: 'var(--font-mono)', fontSize: '13px' } }, memo),
    ),
    settleApps.map((app) => h('a', {
      class: 'btn btn--ghost btn--block',
      style: { marginBottom: '8px' },
      href: app.link(amount, memo),
      target: '_blank',
      rel: 'noopener noreferrer',
    }, app.name, svg(icons.external, { size: 15 }))),
    h('button', { class: 'btn btn--primary btn--block', type: 'button', style: { marginTop: '6px' }, onclick: closeSheet }, 'Done'),
  ));
}
