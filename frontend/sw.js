const CACHE_NAME = 'it-inventory-v7';
const ASSETS = [
  '/',
  '/index.html',
  '/frontend/style.css',
  '/frontend/UI_controller.js',
  '/static/logo/KOCSH.png',
  '/static/logo/favicon/web-app-manifest-192x192.png',
  '/static/logo/favicon/web-app-manifest-512x512.png',
  '/frontend/manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
