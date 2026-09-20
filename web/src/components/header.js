import { h, svg, icons, money } from './ui.js';
import * as S from '../state.js';
import { syndicates, seasons } from '../data/mock.js';

export const TABS = [
  { id: 'matchday', label: 'Matchday' },
  { id: 'pitch',    label: 'The Pitch' },
  { id: 'bench',    label: 'The Bench' },
  { id: 'hearth',   label: 'The Hearth' },
  { id: 'hometeam', label: 'Home Team' },
  { id: 'visitors', label: 'Visitors' },
];

export function header() {
  const s = S.get();
  const syn = S.syndicate();
  const benchCount = S.benchCount();

  const lockup = h('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', minWidth: '0' } },
    h('div', {
      'aria-hidden': 'true',
      style: {
        width: '40px', height: '40px', borderRadius: '12px',
        background: '#134E48', flex: 'none', display: 'grid', placeItems: 'center',
      },
    }, svg(icons.mark, { size: 21, stroke: '#F6BE00' })),
    h('div', { style: { minWidth: '0' } },
      h('p', {
        style: {
          margin: '0', fontFamily: 'var(--font-display)', fontWeight: '800',
          fontSize: '17px', letterSpacing: '-.015em',
        },
      }, 'Hearth & Bench'),
      h('p', { class: 'eyebrow', style: { marginTop: '1px' } }, 'Season tickets, shared'),
    ),
  );

  const notifications = S.openSeats().length;
  const bell = h('button', {
    class: 'btn btn--ghost',
    type: 'button',
    style: { minHeight: '40px', padding: '0 12px', position: 'relative' },
    'aria-label': notifications
      ? `${notifications} seats need attention`
      : 'No pending requests',
    onclick: () => S.set({ tab: 'bench' }),
  },
    svg(icons.bell, { size: 18 }),
    notifications ? h('span', { class: 'badge badge--ember' }, String(notifications)) : null,
  );

  const gear = h('button', {
    class: 'btn btn--ghost',
    type: 'button',
    style: { minHeight: '40px', padding: '0 12px' },
    'aria-label': 'Campfire settings',
    'aria-pressed': String(s.tab === 'settings'),
    onclick: () => S.set({ tab: s.tab === 'settings' ? 'matchday' : 'settings' }),
  }, svg(icons.settings, { size: 18 }));

  // Group switcher. The balance badge deliberately does not live here — it
  // reads once, in The Hearth.
  const switcher = h('label', { class: 'sr-only', for: 'syn-switch' }, 'Syndicate');
  const select = h('select', {
    id: 'syn-switch',
    class: 'select',
    style: { maxWidth: '100%', fontWeight: '600', minHeight: '40px' },
    onchange: (e) => S.set({ syndicateId: e.target.value }),
  }, syndicates.map((x) =>
    h('option', { value: x.id, selected: x.id === syn.id }, `${x.name} — ${x.holds}`),
  ));

  const seasonRow = h('div', { class: 'scroll-row', style: { marginTop: '8px' }, role: 'tablist', 'aria-label': 'Season' },
    seasons.map((y) => h('button', {
      class: 'chip',
      type: 'button',
      role: 'tab',
      'aria-selected': String(y.year === s.seasonYear),
      onclick: () => S.set({ seasonYear: y.year }),
    }, y.label)),
  );

  const tabs = h('nav', { class: 'scroll-row', style: { marginTop: '10px' }, 'aria-label': 'Sections' },
    TABS.map((t) => h('button', {
      class: 'chip',
      type: 'button',
      role: 'tab',
      'aria-selected': String(t.id === s.tab),
      onclick: () => S.set({ tab: t.id }),
    },
      t.label,
      t.id === 'bench' && benchCount
        ? h('span', {
            class: 'badge badge--ember',
            style: { marginLeft: '6px' },
          }, String(benchCount))
        : null,
    )),
  );

  return h('header', {
    style: {
      borderBottom: '1px solid var(--hairline)',
      background: 'var(--surface)',
      position: 'sticky', top: '0', zIndex: '20',
      paddingTop: '12px', paddingBottom: '10px',
    },
  },
    h('div', { class: 'shell' },
      h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' } },
        lockup,
        h('div', { style: { display: 'flex', gap: '6px', flex: 'none' } }, bell, gear),
      ),
      h('div', { style: { marginTop: '10px' } }, switcher, select),
      seasonRow,
      tabs,
    ),
  );
}
