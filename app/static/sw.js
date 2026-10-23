/**
 * ABOO PERFUMES — PWA Service Worker
 * Provides offline caching, lightning-fast static resource loading, and PWA installability.
 */

const CACHE_NAME = "aboo-perfumes-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/images/pwa-icon.svg",
  "/static/images/aboo-logo.svg",
  "/static/images/pwa-icon-192.png",
  "/static/images/pwa-icon-512.png",
  "/static/images/apple-touch-icon.png",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch((err) => {
        console.warn("Service worker cache.addAll warning:", err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Let API requests pass directly to network
  if (event.request.url.includes("/api/")) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).catch(() => {
        if (event.request.mode === "navigate") {
          return caches.match("/");
        }
      });
    })
  );
});
