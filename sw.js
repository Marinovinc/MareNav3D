// MareNav3D - service worker: precache app (offline); cache-first per CDN (MapLibre GL / pmtiles / Protomaps basemaps / Plotly / geotiff)
// v3: HTML network-first (app sempre aggiornata online), CDN/icone cache-first; rotte/tracce/catture in localStorage
// NB: i .pmtiles e le richieste Range passano diretti alla rete (vedi fetch handler) - non vanno in cache
const CACHE = 'marenav3d-v32';
const ASSETS = [
  './', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'
];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const req = e.request;
  // MAI in cache: richieste Range (rompono i lettori a range, es. PMTiles) e i file .pmtiles -> passano diretti alla rete
  if (req.headers.has('range') || new URL(req.url).pathname.endsWith('.pmtiles')) return;
  // cacheabile solo se risposta valida e NON opaca (no 4xx/5xx/opache stale in eterno)
  const cacheable = resp => resp && resp.ok && resp.type !== 'opaque';
  const isHTML = req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html');
  if (isHTML) {
    // network-first: online ricevi sempre l'app aggiornata; offline ripieghi sulla cache
    e.respondWith(
      fetch(req).then(resp => { if (cacheable(resp)) { try { const cp = resp.clone(); caches.open(CACHE).then(c => c.put(req, cp)); } catch (_) {} } return resp; })
        .catch(() => caches.match(req, {ignoreSearch: true}).then(r => r || caches.match('./index.html')))
    );
  } else {
    // cache-first per CDN/icone/asset statici. NIENTE ignoreSearch: le API WCS EMODnet hanno
    // lo stesso path e cambiano solo nella query (il bbox) -> ignoreSearch restituiva sempre la
    // stessa tile per qualsiasi area (3D sempre identico). Match esatto sull'URL completo.
    e.respondWith(
      caches.match(req).then(r =>
        r || fetch(req).then(resp => {
          if (cacheable(resp)) { try { const cp = resp.clone(); caches.open(CACHE).then(c => c.put(req, cp)); } catch (_) {} }
          return resp;
        }).catch(() => caches.match('./index.html'))
      )
    );
  }
});
