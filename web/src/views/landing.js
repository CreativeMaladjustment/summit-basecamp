import { h, svg, icons, badge } from '../components/ui.js';
import * as S from '../state.js';
import { syndicates, hearthsideNotes } from '../data/mock.js';

export function landingView() {
  return h('div', {
    class: 'view',
    style: { minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '28px 16px 40px' },
  },
    h('div', { style: { width: 'min(100%, 520px)' } },
      lockup(),

      h('h1', {
        style: { margin: '26px 0 0', fontSize: '34px', fontWeight: '800', lineHeight: '1.08', letterSpacing: '-.025em' },
      }, 'Two seats. Five friends. One ledger nobody argues about.'),
      h('p', { style: { margin: '12px 0 0', fontSize: '16px', color: 'var(--ink-soft)' } },
        'Share a season ticket package without the group chat arithmetic. Claim a match, call a sub, and settle up when the season ends.'),

      h('p', { class: 'eyebrow', style: { marginTop: '28px' } }, 'Tonight at the Hearth'),
      h('div', { style: { marginTop: '10px' } }, hearthsideNotes.map(teaser)),

      h('div', { style: { marginTop: '24px' } },
        h('button', {
          class: 'btn btn--primary btn--block',
          type: 'button',
          onclick: () => S.signIn('google'),
        }, 'Continue with Google'),
        h('button', {
          class: 'btn btn--ghost btn--block',
          type: 'button',
          style: { marginTop: '10px' },
          onclick: () => S.signIn('apple'),
        }, 'Continue with Apple'),
        h('p', { style: { margin: '14px 0 0', fontSize: '13px', color: 'var(--ink-mute)', textAlign: 'center' } },
          'Sign-in runs on OIDC through Google and Apple. No passwords, and nothing for us to lose.'),
      ),
    ),
  );
}

function lockup() {
  return h('div', { style: { display: 'flex', alignItems: 'center', gap: '12px' } },
    h('div', {
      'aria-hidden': 'true',
      style: { width: '46px', height: '46px', borderRadius: '13px', background: '#134E48', flex: 'none', display: 'grid', placeItems: 'center' },
    }, svg(icons.mark, { size: 23, stroke: '#F6BE00' })),
    h('div', null,
      h('p', { style: { margin: '0', fontFamily: 'var(--font-display)', fontWeight: '800', fontSize: '19px', letterSpacing: '-.015em' } },
        'Summit Hearth & Bench'),
      h('p', { class: 'eyebrow', style: { marginTop: '2px' } }, 'Season tickets, shared'),
    ),
  );
}

function teaser(note) {
  if (note.kind === 'trivia') {
    return h('article', { class: 'card', style: { marginBottom: '10px' } },
      h('p', { class: 'eyebrow' }, 'Trivia'),
      h('p', { style: { margin: '6px 0 0', fontFamily: 'var(--font-display)', fontWeight: '700', fontSize: '16px' } }, note.question),
      h('p', { style: { margin: '8px 0 0', fontSize: '13px', color: 'var(--ink-mute)' } }, 'Sign in to flip the card.'),
    );
  }
  return h('article', { class: 'card', style: { marginBottom: '10px' } },
    h('p', { class: 'eyebrow' }, note.eyebrow),
    h('p', { style: { margin: '6px 0 0', display: 'flex', alignItems: 'center', gap: '8px' } },
      note.num ? badge(`#${note.num}`, 'gold') : null,
      h('strong', { style: { fontFamily: 'var(--font-display)', fontSize: '16px' } }, note.name),
    ),
    h('p', { style: { margin: '8px 0 0', fontSize: '14px', color: 'var(--ink-soft)' } }, note.body),
  );
}

/** Step two: pick the syndicate you were invited to, or start one. */
export function syndicateView() {
  const code = h('input', { class: 'input', id: 'invite', placeholder: 'e.g. NORTH-114' });

  return h('div', {
    class: 'view',
    style: { minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '28px 16px 40px' },
  },
    h('div', { style: { width: 'min(100%, 520px)' } },
      lockup(),
      h('h1', { style: { margin: '26px 0 0', fontSize: '28px', fontWeight: '800', letterSpacing: '-.02em' } },
        'Find your syndicate'),
      h('p', { style: { margin: '10px 0 0', fontSize: '15px', color: 'var(--ink-soft)' } },
        'Join the circle that holds the seats, or start one and invite the rest.'),

      h('div', { class: 'card', style: { marginTop: '20px' } },
        h('label', { class: 'field__label', for: 'invite' }, 'Invite code'),
        code,
        h('button', {
          class: 'btn btn--primary btn--block',
          type: 'button',
          style: { marginTop: '10px' },
          onclick: () => S.chooseSyndicate(syndicates[0].id),
        }, 'Join with code'),
      ),

      h('p', { class: 'eyebrow', style: { marginTop: '22px' } }, "You've been invited to"),
      h('div', { style: { marginTop: '10px' } },
        syndicates.map((s) => h('button', {
          class: 'path',
          type: 'button',
          onclick: () => S.chooseSyndicate(s.id),
        },
          h('div', { class: 'path__icon', style: { background: '#134E48' } }, svg(icons.users, { size: 19, stroke: '#fff' })),
          h('div', null,
            h('p', { class: 'path__name', style: { margin: '0' } }, s.name),
            h('p', { class: 'path__help' }, `${s.holds} · invited by ${s.invitedBy}`),
          ),
        )),
      ),

      h('button', {
        class: 'btn btn--ghost btn--block',
        type: 'button',
        style: { marginTop: '10px' },
        onclick: () => S.set({ stage: 'app', tab: 'settings' }),
      }, 'Start a new syndicate'),
    ),
  );
}
