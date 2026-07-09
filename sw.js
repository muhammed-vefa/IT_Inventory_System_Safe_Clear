const CACHE_NAME = 'it-inventory-v39';
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
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', event => {
  // Sadece GET isteklerini önbellekle/network-first yap.
  // POST, PUT, DELETE gibi işlemler direkt ağa gitsin.
  if (event.request.method !== 'GET') {
      event.respondWith(fetch(event.request));
      return;
  }

  // API istekleri cache'lenmesin, hep ağdan gitsin (Edge vs. uyumluluğu)
  if (event.request.url.includes('/api/')) {
      event.respondWith(fetch(event.request));
      return;
  }

  event.respondWith(
    fetch(event.request)
      .then(networkResponse => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, responseToCache);
            });
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request);
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
    }).then(() => self.clients.claim())
  );
});

