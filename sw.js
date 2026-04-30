const CACHE_NAME = 'keydata-v2.8'; // Versiyonu UI_controller'ın ile eşleşecek şekilde güncelle
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './style.css',
  './frontend/UI_controller.js',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// Kurulum: Statik dosyaları önbelleğe al
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE)));
});

// Aktivasyon: Eski önbellekleri temizle
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
});

// Fetch: İnternet yoksa önbellekten getir
self.addEventListener('fetch', (event) => {
  // Sadece GET isteklerini önbellekle (API'ler genellikle POST olduğu için hariç tutulmalı)
  if (event.request.method === 'GET') {
    event.respondWith(
      caches.match(event.request).then((response) => response || fetch(event.request))
    );
  }
});