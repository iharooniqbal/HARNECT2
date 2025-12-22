// ================= CACHE CONFIGURATION =================
const CACHE_NAME = 'harnect-cache-v1';
const APP_SHELL = [
  '/',
  '/static/style.css',
  '/static/script.js',
];


// ================= INSTALL EVENT =================
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL);
    })
  );
});


// ================= ACTIVATE EVENT =================
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      )
    )
  );
});


// ================= FETCH EVENT =================
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).catch(() => {
      });
    })
  );
});
