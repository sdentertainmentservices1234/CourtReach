# CourtReach

A live tracker for the Supreme Court of India display board. Register, add your
matters by court + item, and CourtReach tells you the moment each one is reaching
— so you never miss your turn or chase the clerk.

- **`index.html` / `courtreach.html`** — the app (same file; `index.html` is the Pages entry point).
- **`board-engine.js`** — the shared, chamber-agnostic proximity engine (how "N away" is computed).
- **`sync_daysheet.py`** — optional bridge that mirrors ONE organisation's SD-Chamber
  day sheet into its CourtReach board, on a schedule. Off by default; see
  `DAYSHEET-SYNC-SETUP.md`.

## Account types
Signup is two steps: pick a type, then fill only that type's fields.
- **Individual** — your own board, your own 30-day trial.
- **Organisation** — chambers, law firm, law office or in-house team (the kind is
  a field, `orgType`; they all want the same thing so they share one door). One
  subscription covers everyone. The owner gets a rotatable invite code and can
  pre-approve colleagues by email. Members share **one board** (every member's
  matters pooled and attributed), the organisation's entitlement, and **chat**.
- **Join an organisation** — with an invite code, at signup or later.

An individual can join an organisation at any time from Settings (a dismissible
prompt points there). Two guarantees on that path: they keep whichever
entitlement is **better**, their own or the organisation's, so joining never
shortens access; and their pre-existing matters are stamped `personal` first, so
nothing they entered as an individual is retroactively published to the office.

Chat thread kinds: **Team** (colleagues + staff — the default landing thread),
**Everyone** (whole chamber, for announcements), **direct messages**, and one
thread per **outside collaborator** who has addressed the office. The owner/senior
lands on Everyone and is never badged for Team, so reaching them is a deliberate
act rather than a side effect of office chatter.

## Boards
The board home is a set of tabs, built from the boards a person actually holds:
their chamber's, their own (only if they keep matters outside the chamber), and
one per collaborating senior. **My cases** mirrors this with My / Chamber /
Collaborating lists, grouped by date and colour-coded per court.

Every matter carries the **date** it's listed for, and every board filters on it —
matters entered for a future hearing stay off today's board. Picking a date from
the calendar shows the courts you're listed in that day. Matters saved before
dates were enforced have none and are grandfathered onto today.

## Data model
| Path | What it holds |
| --- | --- |
| `users/{uid}` | profile + `orgId` / `orgRole` |
| `usermatters/{uid}` | that person's tracked matters (source of truth even in a chamber) |
| `orgs/{orgId}` | chamber; `orgId` **is** the owner's uid; carries the shared trial/override |
| `orgcodes/{CODE}` | invite-code → orgId. **get-only**, never listable |
| `orginvites/{email}` | pre-approved email → orgId. Readable only by that email's owner |
| `orgmsgs/{id}` | chat, keyed by `orgId` + `channel` (`team` / `all` / `dm:a_b`) |
| `chatreads/{uid}` | per-channel "read up to" marker — drives unread counts and seen ticks |
| `linkmsgs/{id}` | collaboration chat; `scope:'peer'` (1:1) or `'chamber'` (addressed to a whole office) |

A matter can carry `source:"daysheet"` + `byLabel` — written only by
`sync_daysheet.py`, never by the app itself. It marks a matter mirrored in from
outside CourtReach and names who's appearing as plain text rather than a real
account. The UI hides edit/remove on these (edit the source instead) and never
recomputes the label — `byLabel` always wins over the account-based name.

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
