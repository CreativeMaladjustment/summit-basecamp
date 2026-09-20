// Cache-first for the app shell so an installed Hearth & Bench opens offline.
const CACHE = 'shb-v1';
const SHELL = [
  './',
  './index.html',
  './icon.svg',
  './manifest.webmanifest',
  './src/styles/tokens.css',
  './src/styles/base.css',
  './src/styles/components.css',
  './src/app.js',
  './src/state.js',
  './src/data/mock.js',
  './src/components/ui.js',
  './src/components/header.js',
  './src/components/callasub.js',
  './src/views/landing.js',
  './src/views/matchday.js',
  './src/views/pitch.js',
  './src/views/bench.js',
  './src/views/hearth.js',
  './src/views/hometeam.js',
  './src/views/visitors.js',
  './src/views/settings.js',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then((hit) => hit ?? fetch(e.request)),
  );
});
