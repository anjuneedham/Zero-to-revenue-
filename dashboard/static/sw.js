// App-shell cache so the installed app opens instantly and shows a shell offline.
// Never caches /api/*, /mcp/*, or anything with a login token.
const SHELL = "z2r-shell-v6";
const FILES = ["/", "/css/fonts.css", "/css/app.css", "/js/core.js", "/js/overview.js", "/js/scout.js", "/js/operator.js", "/js/treasury.js",
  "/js/plan.js", "/js/main.js", "/data/plan.json", "/manifest.webmanifest", "/icon-192.png", "/icon-512.png"];
self.addEventListener("install", e => e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.startsWith("/api/") || u.pathname.startsWith("/mcp")) return;
  if (u.pathname.startsWith("/fonts/")) {  // fonts never change: cache first
    e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); return r; })));
    return;
  }
  e.respondWith(fetch(e.request).then(r => { if (r.ok) { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); } return r; })
    .catch(() => caches.match(e.request).then(hit => hit || (e.request.mode === "navigate" ? caches.match("/") : Response.error()))));
});
