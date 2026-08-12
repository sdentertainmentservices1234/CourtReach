# Closed-phone push notifications — setup

Pops a notification on your phone **even when the app is closed and the phone is
locked** — the moment a case you're tracking (your own, or your chamber's) gets close.

Built on **Web Push (VAPID)**, delivered by the **same Cloudflare worker** CourtReach
already uses for the board relay (`BOARD_PROXY`, `sd-board.*.workers.dev` — shared with
SD-Chamber's own board, but CourtReach's push keys/subscribers are kept completely
separate from theirs, just living in the same worker).

**Autonomous, not a relay.** Unlike a simpler "some open app notices and asks the
worker to fan it out" design, this worker checks the board **on its own schedule**,
independent of whether you (or anyone) has the app open anywhere. That's the only way
it actually covers a solo advocate — if your phone is the only device and it's locked,
nothing else exists to notice your case got close unless the worker is doing it itself.

---

## One-time setup (~20 min)

### 1. Generate the VAPID key pair

Already done for you this round. The **public** half is safe to commit and is already
baked into `courtreach.html` (`VAPID_PUBLIC_KEY`) — nothing to do there.

The **private** half is a real secret and is deliberately **not written in this file**
(or anywhere else in the repo) — even in a private repo, a secret committed to git
history is there forever, findable by anyone who ever gets read access, long after you
might rotate it. It was given to you directly in chat, not as a file. Paste it straight
into the Cloudflare Worker's **Secrets** in step 2 below and nowhere else. If you've
lost it, generate a fresh pair (any VAPID keygen tool) and update both the worker
secret and `VAPID_PUBLIC_KEY` in `courtreach.html` to match — they have to be the same
pair.

### 2. Cloudflare — add a KV namespace and secrets to the worker

Dashboard → **Workers & Pages** → the `sd-board` worker (same one BOARD_PROXY already
points at) → **Settings**:

- **Bindings → KV namespace binding** → create a new namespace (name it e.g.
  `cr-push-subs`) → bind it with **Variable name `CR_SUBS`** (exactly — the worker code
  looks for this name specifically, kept separate from SD-Chamber's own `SUBS` binding).
- **Variables and Secrets** → add these **Secrets**:
  - `CR_VAPID_PUBLIC`  = `BN9wPypVjBf04WZHnjoeNSBj885wrdi6w_gSX3SUr4jncPEfPB9xmdoCL7-HptWiaik9vnkIb8KtYyUsSZYWK-Q`
    (same value as `VAPID_PUBLIC_KEY` in `courtreach.html` — public, safe either place)
  - `CR_VAPID_PRIVATE` = the private key given to you in chat (see step 1 — not in this file)
  - `CR_VAPID_SUBJECT` = `mailto:you@yourdomain` (any contact mailto/URL — shown to
    push services, not to users)
  - `CR_FIRESTORE_SA_KEY` = the **full JSON contents** of a `courtreach-ee02b`
    service-account key file, pasted as one value. This is what lets the worker read
    tracked cases directly. If you still have the service-account key you generated
    for the day-sheet sync (`DAYSHEET-SYNC-SETUP.md`, step 3 — same `courtreach-ee02b`
    project), you can reuse that exact file rather than generating a new one.
    Otherwise: Firebase console → **courtreach-ee02b** → gear icon → **Project
    settings → Service accounts → Generate new private key**.

### 3. Deploy the updated worker

Paste the updated `worker.js` (in `~/Projects/DisplayBoard/board-dev/worker.js` on this
laptop — same shared worker source, now with CourtReach's `/cr-push-*` endpoints and
its own scheduled watcher added alongside SD-Chamber's existing code) into the worker's
editor → **Deploy**. Everything SD-Chamber already has keeps working unchanged; this
only adds new code paths.

### 4. Add the Cron Trigger

Same worker → **Settings → Triggers → Cron Triggers → Add Cron Trigger**:

```
*/1 3-11 * * 1-5
```

Every minute, roughly 8:30am–4:30pm IST, Monday–Friday (Cloudflare Cron is always UTC;
adjust the hour range if you want a wider or narrower window — Cloudflare's minimum
granularity is once a minute, no faster).

### 5. On your phone, once

- **Install CourtReach to the Home Screen** if you haven't (Safari → Share → *Add to
  Home Screen*). **Mandatory on iPhone** — iOS 16.4+ only allows push from an installed
  web app, never from a Safari tab.
- Open the installed app → **Settings → Notifications** → turn **Case alerts** on →
  **Allow** when the system asks.

Test: lock your phone with a case you're tracking close to reaching (or wait for one
to naturally get close) — a notification should arrive within a minute or so of it
crossing into range, phone locked or not.

---

## How it works / limits (read this)

- Turning the toggle on registers this device (`/cr-push-subscribe`, keyed by your uid,
  stored in the `CR_SUBS` KV namespace) and separately keeps the existing fast in-page
  alert for while the app is actually open (unchanged, same 6-second board poll as
  before — the push path is a *second*, slower layer for when nothing's open).
- The Cron Trigger fetches the live board and `court-updates.json` itself, reads each
  subscribed user's tracked cases (and, if they're in a chamber, every colleague's
  chamber-shared ones) directly from Firestore via the service-account key, runs the
  same proximity engine CourtReach's own UI uses, and pushes to anyone whose case just
  got closer since the last check (never repeats the same distance twice in a row).
- **Deliberate v1 scope** — flagged, not silently dropped:
  - Honours a case's own declared status (My cases → mark over/passover) for
    strikethrough/passover handling, but **not** the live board's own OVER/PASS OVER
    remark column the way the in-app view also does — that needs an extra per-court
    fetch this first version doesn't do yet.
  - No Regular-list "reset from a high item back to 101" refinement — the simpler
    "current item exceeds the Misc total" signal is used instead.
  - Both are addable in a follow-up round once this base version is confirmed working
    on a real phone.
- iOS may batch/delay pushes slightly when the phone is idle for a long time; not
  second-perfect, but working within the cron's own ~1 minute cadence.
- Turning the toggle **off** unsubscribes that device.

## Files

- `courtreach.html` — `VAPID_PUBLIC_KEY`, `syncPushSub()/dropPushSub()`, wired into the
  existing `toggleNotify()`.
- `sw.js` — the service worker's `push`/`notificationclick` handlers (new file —
  CourtReach had no service worker before this).
- `~/Projects/DisplayBoard/board-dev/worker.js` — the shared worker's source. The
  CourtReach section is clearly marked (search `COURTREACH — autonomous closed-phone
  push`) and includes an embedded copy of `board-engine.js`'s classify() logic (the
  dashboard editor can't import across repos, so it's a manual paste — re-sync it here
  if `board-engine.js` ever changes) plus the Firestore REST + service-account auth
  code.
