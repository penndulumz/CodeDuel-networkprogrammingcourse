const CACHE_NAME = "codeduel-offline-submit-v5";
const OFFLINE_ASSETS = [
  "/static/offline-submit.html",
  "/static/js/offline-submit.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(OFFLINE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key.startsWith("codeduel-offline-submit-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);
  if (event.request.method !== "GET" || requestUrl.origin !== self.location.origin) return;

  if (OFFLINE_ASSETS.includes(requestUrl.pathname)) {
    event.respondWith(
      caches.match(event.request, { ignoreSearch: true }).then((cached) => cached || fetch(event.request))
    );
  }
});
