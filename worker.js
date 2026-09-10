const CACHE = "lila-shell-v9";
const ASSETS = [
  "/",
  "/src/styles.css?v=9",
  "/src/main.js?v=9",
  "/src/api.js?v=9",
  "/src/components.js?v=9",
  "/src/format.js?v=9",
  "/manifest.webmanifest",
  "/assets/lila-icon-192.png",
  "/assets/lila-icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then(async (cache) => {
      await Promise.all(ASSETS.map(async (asset) => {
        const response = await fetch(asset, { cache: "no-store" });
        if (!response.ok) throw new Error(`Unable to cache ${asset}: ${response.status}`);
        await cache.put(asset, response);
      }));
      await self.skipWaiting();
    }),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key.startsWith("lila-shell-") && key !== CACHE).map((key) => caches.delete(key)),
    )).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        }
        return response;
      })
      .catch(() => caches.match(event.request).then((cached) => cached || caches.match("/"))),
  );
});
