// MareNav3D - service worker: precache app + zone batimetriche (offline); cache-first per CDN (globe.gl/Plotly/texture)
const CACHE = 'marenav3d-v1';
const ASSETS = [
  './', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png',
  './data/manifest.json',
  './data/tirreno.bin', './data/adriatico.bin', './data/ionio.bin',
  './data/ligure.bin', './data/sardo.bin', './data/sicilia.bin'
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
  e.respondWith(
    caches.match(e.request, {ignoreSearch: true}).then(r =>
      r || fetch(e.request).then(resp => {
        try { const cp = resp.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); } catch (_) {}
        return resp;
      }).catch(() => caches.match('./index.html'))
    )
  );
});
