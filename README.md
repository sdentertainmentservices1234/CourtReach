# CourtReach

A personal live tracker for the Supreme Court of India display board. Every user
is their own office: register, add your matters by court + item, and CourtReach
tells you the moment each one is reaching — so you never miss your turn or chase
the clerk. Collaboration (track & message the advocate you're briefing) is next.

- **`index.html` / `courtreach.html`** — the app (same file; `index.html` is the Pages entry point).
- **`board-engine.js`** — the shared, chamber-agnostic proximity engine (how "N away" is computed).

## Setup
1. Create a Firebase project → enable Email/Password auth + Firestore (`asia-south1`).
2. Paste its `firebaseConfig` into `courtreach.html`/`index.html` (and keep `const DEMO = false;`).
3. Publish the Firestore rules (own `users/{uid}` + `usermatters/{uid}`).
4. The SC board data comes from a shared Cloudflare relay (`BOARD_PROXY`) — no change needed.

Local dev: `sed 's/const DEMO = false;/const DEMO = true;/' index.html > courtreach-demo.html` then serve.
