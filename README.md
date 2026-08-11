# CourtReach

A live tracker for the Supreme Court of India display board. Register, add your
matters by court + item, and CourtReach tells you the moment each one is reaching
— so you never miss your turn or chase the clerk.

- **`index.html` / `courtreach.html`** — the app (same file; `index.html` is the Pages entry point).
- **`board-engine.js`** — the shared, chamber-agnostic proximity engine (how "N away" is computed).

## Account types
- **Individual** — your own board, your own 30-day trial.
- **Chamber / office** — one subscription covering everyone. The owner gets an
  invite code (rotatable) and can pre-approve colleagues by email. Members share
  **one board** (every member's matters pooled and attributed), the chamber's
  entitlement, and in-app **chat**.

Chat has three thread kinds: **Team** (colleagues + staff — the default landing
thread), **Everyone** (whole chamber, for announcements), and **direct messages**.
The owner/senior lands on Everyone and is never badged for Team, so reaching them
is a deliberate act rather than a side effect of office chatter.

## Data model
| Path | What it holds |
| --- | --- |
| `users/{uid}` | profile + `orgId` / `orgRole` |
| `usermatters/{uid}` | that person's tracked matters (source of truth even in a chamber) |
| `orgs/{orgId}` | chamber; `orgId` **is** the owner's uid; carries the shared trial/override |
| `orgcodes/{CODE}` | invite-code → orgId. **get-only**, never listable |
| `orginvites/{email}` | pre-approved email → orgId. Readable only by that email's owner |
| `orgmsgs/{id}` | chat, keyed by `orgId` + `channel` (`team` / `all` / `dm:a_b`) |

Joining a chamber hands over someone else's subscription, so it is verified
server-side: the write must carry `joinedVia:<CODE>` matching a live `orgcodes`
doc, or the user's own email must be on that chamber's invite list. See
`firestore.rules`.

## PIN unlock
A **device-local** convenience lock over a session Firebase already holds — not a
second credential. Only a salted SHA-256 of the PIN is stored, in `localStorage`,
per uid. A new device or a sign-out still needs the real password; five wrong
tries signs out.

## Setup
1. Create a Firebase project → enable Email/Password auth + Firestore (`asia-south1`).
2. Paste its `firebaseConfig` into `courtreach.html`/`index.html` (and keep `const DEMO = false;`).
3. Publish the Firestore rules (own `users/{uid}` + `usermatters/{uid}`).
4. The SC board data comes from a shared Cloudflare relay (`BOARD_PROXY`) — no change needed.

Local dev: `sed 's/const DEMO = false;/const DEMO = true;/' index.html > courtreach-demo.html` then serve.
