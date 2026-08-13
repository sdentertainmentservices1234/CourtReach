# Closed-phone push notifications — setup

Pops a notification on your phone **even when the app is closed and the phone is
locked** — the moment a case you're tracking (your own, or your chamber's) gets close.

Built on **Web Push (VAPID)**, delivered by **CourtReach's own Cloudflare worker**
(`worker.js` in this repo), which also serves the board relay (`BOARD_PROXY`).

**This used to run inside SD-Chamber's `sd-board` worker and no longer does.** That was
defensible while the worker was only a stateless relay for public board data. It stopped
being defensible once push landed: this worker holds a KV namespace, VAPID keys and a
Firebase **service-account key** — full admin on `courtreach-ee02b` — and runs its own
cron. Sharing meant CourtReach's production credentials sat behind whoever could edit the
chamber's worker, that CourtReach shared a process with SD-Chamber's unauthenticated
`/push-send` endpoint, and that shipping a fix for one app meant redeploying the other's.
The repos were split for exactly this reason; the worker had not been split with them.

The board-proxy half is now duplicated in both workers rather than shared. That is fine:
it is stateless, holds no secrets, and each worker's own edge cache keeps the load on the
Supreme Court's site to roughly the couple of fetches a minute it was before.

**Autonomous, not a relay.** Unlike a simpler "some open app notices and asks the
worker to fan it out" design, this worker checks the board **on its own schedule**,
independent of whether you (or anyone) has the app open anywhere. That's the only way
it actually covers a solo advocate — if your phone is the only device and it's locked,
nothing else exists to notice your case got close unless the worker is doing it itself.

## Two different things, on purpose

**Case alerts are polled.** The cron watcher below re-reads the Supreme Court board every
minute and works out whether anything of yours got close. It has to be a poll: nobody is
sitting there ready to tell us a court moved on.

**Chat messages announce themselves.** When you send a message, your app calls
`/cr-push-chat` the instant the message is saved, and the recipients' phones light up in
about a second. Polling would have been wrong here — a minute-late message in a courtroom
is worse than useless — and unnecessary, because the sender's app is open by definition.
Owner: *"people will not use the app if messages are not popping on their locked phone
screen like whatsapp does."*

The chat endpoint takes only a collection name and a document id. Everything else is read
back out of Firestore by the worker: the message must already exist, its `by` must be the
caller, and the recipient list is derived from the stored document. So nobody can push
words somebody never said, push as somebody else, or aim a notification at a person
outside the conversation. The `team` thread also skips the senior, exactly as the in-app
badge does — they asked not to be pulled into every message, and a push that ignored that
would undo the point of the thread.

---

## One-time setup (~20 min)

### 1. Generate the VAPID key pair

Already done — a fresh pair was generated 2026-08-14. The **public** half is safe to
commit and is already baked into `courtreach.html` (`VAPID_PUBLIC_KEY`) — nothing to do
there.

The **private** half is a real secret and is deliberately **not written in this file**,
or anywhere else in the repo: even in a private repo, a secret committed to git history
is there forever, findable by anyone who ever gets read access, long after you rotate
it. It is on this laptop only, in the session scratchpad. Paste it into the Cloudflare
Worker's `CR_VAPID_PRIVATE` secret and nowhere else.

The earlier pair was abandoned rather than hunted down: its private half had been handed
over in chat and never written to a file. Rotating cost nothing, because
`/cr-push-subscribe` had never actually been deployed on the old shared worker — a POST
to it returned board HTML — so no live subscription was ever signed by the old key.

To regenerate at any time, on a Mac with no Node:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out vapid.pem
```

then extract the 32-byte private scalar and the 65-byte uncompressed public point
(`04 || X || Y`) and base64url-encode each with the padding stripped. Both halves must
be replaced together — `VAPID_PUBLIC_KEY` in `courtreach.html` and `CR_VAPID_PUBLIC` /
`CR_VAPID_PRIVATE` in the worker are one pair and are useless mismatched.

### 2. Cloudflare — create CourtReach's worker, then add a KV namespace and secrets

Dashboard → **Workers & Pages → Create → Worker**. Name it **`courtreach`** (the name
becomes the hostname, so it ends up at `courtreach.<your-subdomain>.workers.dev`). Paste
this repo's `worker.js` into the editor and **Deploy** once, so the worker exists — then
→ **Settings**:

- **Bindings → KV namespace binding** → create a new namespace (name it e.g.
  `cr-push-subs`) → bind it with **Variable name `CR_SUBS`** (exactly — the worker code
  looks for this name specifically).
- **Variables and Secrets** → add these **Secrets**:
  - `CR_VAPID_PUBLIC`  = `BPrdFlbyK--z9lHp5Vjv_ZajyGmoTdl1dYY194k0iE8ZYKNFc2mRrISqze1IJl3apcOvPWrsd5fPy1Wx-DB4QL8`
    (same value as `VAPID_PUBLIC_KEY` in `courtreach.html` — public, safe either place)
  - `CR_VAPID_PRIVATE` = the private key from the pair generated 2026-08-14 (see step 1)
  - `CR_VAPID_SUBJECT` = `mailto:you@yourdomain` (any contact mailto/URL — shown to
    push services, not to users)
  - `CR_FIRESTORE_SA_KEY` = the **full JSON contents** of a `courtreach-ee02b`
    service-account key file, pasted as one value. This is what lets the worker read
    tracked cases directly. If you still have the service-account key you generated
    for the day-sheet sync (`DAYSHEET-SYNC-SETUP.md`, step 3 — same `courtreach-ee02b`
    project), you can reuse that exact file rather than generating a new one.
    Otherwise: Firebase console → **courtreach-ee02b** → gear icon → **Project
    settings → Service accounts → Generate new private key**.

### 3. Point the app at the new worker

Copy the new worker's `*.workers.dev` URL and set it as `BOARD_PROXY` in
`courtreach.html` (then mirror to `index.html` and push — the Pages build deploys it).
Until this is done the app still talks to `sd-board`, and the new worker sits idle.

Check it first, before switching — the relay half needs nothing configured:

```bash
curl -s -o /dev/null -w '%{http_code}\n' 'https://courtreach.<your-subdomain>.workers.dev/?ctype=c'
```

`200` means the proxy works and the switch is safe. Redeploy after any later edit to
`worker.js`; the dashboard editor cannot import from this repo, so it is a manual paste.

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
- `worker.js` (this repo) — CourtReach's own worker: board relay, `/cr-push-*` with
  Firebase ID-token verification, the autonomous watcher, Firestore REST +
  service-account auth, and `board-engine.js` embedded **whole** between explicit BEGIN
  and END markers. The dashboard editor can't import across repos, so the engine is a
  manual paste — when `board-engine.js` changes, copy the entire file over the block
  between those markers rather than hand-editing it there. A hand-maintained partial
  copy is exactly how the worker previously drifted three fixes behind the app and
  started quoting distances the app itself had stopped quoting.
  It is NOT published by the Pages build: `.github/workflows/deploy-pages.yml` copies an
  explicit allow-list of browser files, so nothing here reaches courtreach.app.
