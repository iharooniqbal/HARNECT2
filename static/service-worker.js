const CACHE_NAME = 'harnect-cache-v1';
const APP_SHELL = [
  '/',
  '/static/style.css',       // adjust if your main CSS has different name
  '/static/script.js',       // adjust if your main JS filename differs
  // add other static assets you need cached, e.g. logos
];

// Install: cache app shell files
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL);
    })
  );
});

// Activate: cleanup old caches
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

// Fetch: respond with cached resources, fallback to network
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).catch(() => {
        // optionally return a fallback HTML page for navigation requests
      });
    })
  );
});
