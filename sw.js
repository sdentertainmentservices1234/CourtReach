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
  e.waitUntil((async () => {
    // Is the app already on screen? A chat message arriving while you are looking at the chat
    // tab does not need to buzz the phone — you can see it. The notification is still SHOWN,
    // because a push handler that shows nothing gets the browser's own "this site was updated
    // in the background" notice instead, which is worse; it is just shown quietly.
    const cs = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    const onScreen = cs.some(c => c.visibilityState === "visible");
    const quiet = onScreen && d.kind === "chat";
    const title = d.title || "CourtReach";
    // icon: the full-colour app icon, shown large inside the notification on Android.
    // badge: a DIFFERENT asset on purpose — Android's status-bar icon discards all colour
    // and tints the remaining alpha, so handing it the opaque full-colour icon rendered as
    // a plain grey square (owner: "I want proper app icon to come in the notification
    // panels"). notif-badge.png is a white-on-transparent silhouette of the chevron mark,
    // which is the shape that API actually wants. iOS ignores both fields and always shows
    // the installed app's own icon — which is the correct outcome there, and needs the app
    // added to the Home Screen.
    await self.registration.showNotification(title, {
      body: d.body || "", tag: d.tag || "cr", renotify: !quiet, data: d,
      icon: "icon-192-v2.png", badge: "notif-badge.png",
      silent: quiet,
      vibrate: quiet ? undefined : [160, 90, 160],
    });
    // Number on the Home Screen icon while the app is CLOSED. The count is how many
    // notifications are currently outstanding — tags mean one per conversation, so it reads
    // as "threads waiting for you", not "messages", which is what a chat badge means anyway.
    // Only set here, never cleared: the app clears it on open, because only the app knows
    // what has actually been read.
    try {
      if ("setAppBadge" in self.navigator) {
        const open = await self.registration.getNotifications();
        if (open.length) await self.navigator.setAppBadge(open.length);
      }
    } catch (_) {}
  })());
});
// Tapping the notification focuses the app if it's already open somewhere, else opens it —
// and for a chat message, asks the page to switch to the Chat tab, so tapping lands you in
// the conversation rather than wherever you happened to leave the app.
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const kind = (e.notification.data && e.notification.data.kind) || "";
  e.waitUntil((async () => {
    const cs = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of cs) {
      if ("focus" in c) {
        try { if (kind === "chat") c.postMessage({ crOpen: "chat" }); } catch (_) {}
        return c.focus();
      }
    }
    if (self.clients.openWindow) return self.clients.openWindow(kind === "chat" ? "./index.html#chat" : "./index.html");
  })());
});
