/* CourtReach — service worker.
   Deliberately minimal: its ONLY job is closed-phone push (see PUSH-SETUP.md). No fetch
   handler, no offline cache — CourtReach has never had a caching layer, and adding one for
   the first time here risks reintroducing exactly the kind of staleness bugs (stale icon,
   stale layout fix) this app has spent real effort chasing out. A service worker with no
   "fetch" listener intercepts nothing; every page load still goes straight to the network,
   unchanged from before this file existed. */
self.addEventListener("install", () => { self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(self.clients.claim()); });

// A push from CourtReach's worker — shows even with the app fully closed. Payload is JSON
// {title, body, tag}. This is what makes a locked phone light up when a tracked case is
// reaching, without the app being open (owner: "I want notifications to come even when the
// phone is locked").
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : "" }; }
  const title = d.title || "CourtReach";
  const opts = {
    body: d.body || "", tag: d.tag || "cr", renotify: true, data: d,
    icon: "icon-192-v2.png", badge: "icon-192-v2.png",
    vibrate: [160, 90, 160],
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});
// Tapping the notification focuses the app if it's already open somewhere, else opens it.
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil((async () => {
    const cs = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of cs) { if ("focus" in c) return c.focus(); }
    if (self.clients.openWindow) return self.clients.openWindow("./index.html");
  })());
});
