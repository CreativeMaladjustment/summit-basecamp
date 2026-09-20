import * as S from './state.js';
import { h } from './components/ui.js';
import { closeSheet } from './components/ui.js';
import { header } from './components/header.js';
import { landingView, syndicateView } from './views/landing.js';
import { matchdayView } from './views/matchday.js';
import { pitchView } from './views/pitch.js';
import { benchView } from './views/bench.js';
import { hearthView } from './views/hearth.js';
import { homeTeamView } from './views/hometeam.js';
import { visitorsView } from './views/visitors.js';
import { settingsView } from './views/settings.js';

const VIEWS = {
  matchday: matchdayView,
  pitch: pitchView,
  bench: benchView,
  hearth: hearthView,
  hometeam: homeTeamView,
  visitors: visitorsView,
  settings: settingsView,
};

const root = document.getElementById('app');

function render() {
  const s = S.get();
  const scroll = window.scrollY;
  root.textContent = '';

  if (!s.signedIn) {
    root.append(landingView());
  } else if (s.stage === 'syndicate') {
    root.append(syndicateView());
  } else {
    root.append(header(), (VIEWS[s.tab] ?? matchdayView)());
    window.scrollTo(0, scroll);
  }
}

S.subscribe(render);
render();

// Tear a sheet down if the view underneath it changes out from under it.
window.addEventListener('pagehide', closeSheet);

if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {
      /* Offline support is a bonus; the app runs without it. */
    });
  });
}
