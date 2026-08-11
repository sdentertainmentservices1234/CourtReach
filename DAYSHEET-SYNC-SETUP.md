# SD-Chamber day sheet → CourtReach board — setup

SD-Chamber and CourtReach are two separate Firebase projects with separate
sign-ins, so there's no way for one to read the other's data from the browser.
A scheduled **GitHub Action** (`.github/workflows/daysheet-sync.yml`) bridges
them server-side: it reads SD-Chamber's day sheet with one admin key and
writes into one CourtReach organisation's shared board with another.

This is wired up for **one organisation only** — the one whose owner uid you
put in `COURTREACH_ORG_UID` below. It is not a general multi-tenant feature.

## What it does

Every ~10 minutes, for each of the next 7 days: read `daysheets/{date}` from
SD-Chamber, and write a matching matter into that organisation's CourtReach
board — court, item, cause title, bench, and who's appearing (by name, pulled
from SD-Chamber's own user list — no CourtReach login needed for juniors or
staff to show up correctly).

**Non-destructive.** Every matter it writes is tagged so it only ever touches
its own previous output for the same date — anything a chamber member enters
by hand in CourtReach, or marks personal, is never touched. Deleting an entry
from the day sheet removes it from CourtReach on the next run.

**Read-only mirror.** Editing a synced matter's card in CourtReach won't stick
— the next sync overwrites it from the day sheet. Edit it in SD-Chamber.

## One-time setup (~5 min, admin only)

### 1. Find the target organisation's ID

In CourtReach, sign in as the organisation's **owner** → **Settings →
Organisation** → scroll to **Organisation ID** → Copy. This is a CourtReach
account uid, not a code you'd give anyone to join — nobody else needs it.

### 2. Generate a service-account key for SD-Chamber

Firebase console → **sd-chamber-1aa78** project → gear icon → **Project
settings → Service accounts** → **Generate new private key**. This downloads a
JSON file — keep it private, it's an admin credential for that project.

### 3. Generate a service-account key for CourtReach

Same steps, in the **courtreach-ee02b** project.

### 4. Add the three GitHub secrets

This repo → **Settings → Secrets and variables → Actions → Secrets** → **New
repository secret**, three times:

| Secret | Value |
|---|---|
| `SD_CHAMBER_SA_KEY` | The full contents of the SD-Chamber JSON key file |
| `COURTREACH_SA_KEY` | The full contents of the CourtReach JSON key file |
| `COURTREACH_ORG_UID` | The Organisation ID from step 1 |

### 5. Turn it on

Same **Settings → Secrets and variables → Actions**, but the **Variables**
tab this time → **New repository variable** → name `DAYSHEET_SYNC_ENABLED`,
value `true`. (It's a variable rather than a secret because it's not
sensitive, and it's how the workflow skips itself cleanly — no red X on every
run — until you're ready.)

### 6. Run it once

Repo **Actions** tab → *Sync SD-Chamber day sheet into CourtReach* → **Run
workflow**. Open CourtReach's board for that organisation — today's day-sheet
entries should appear within a minute or two.

## Turning it off

Set `DAYSHEET_SYNC_ENABLED` back to `false` (or delete the variable). Matters
already synced stay on the board until the next run would have removed them —
delete them by hand in CourtReach if you want them gone immediately.

## Notes & limits

- One organisation per setup. Wiring up a second chamber means a second set of
  secrets and, if it's not a fork of this repo, its own workflow file.
- Attribution is a **plain-text name**, not a real CourtReach account — no
  click-through, no permissions, just a label so the board answers "whose is
  this?" without every junior and clerk needing their own login.
- An entry with no court/item yet (an oral mentioning, a matter still awaiting
  numbers) has nothing to list and is skipped until the day sheet has both.
