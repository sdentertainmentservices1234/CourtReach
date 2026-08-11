#!/usr/bin/env python3
"""
Mirrors SD-Chamber's day sheet into ONE CourtReach organisation's shared board.

SD-Chamber and CourtReach are separate Firebase projects with separate Auth —
a browser signed into one has no valid session in the other, so there's no
client-side way to share data between them. This script is the bridge: it runs
server-side (via .github/workflows/daysheet-sync.yml, on a schedule, the same
pattern as fetch_causelist.py), using an admin service-account key for EACH
project to read SD-Chamber's day sheet and write into CourtReach's board for a
single named organisation.

Source (SD-Chamber, project sd-chamber-1aa78):
    daysheets/{date} = {entries: [{courtNo, itemNo, caseTitle, bench, listType,
                                    appearingFor, juniorUids | juniorUid, ...}]}
Destination (CourtReach, project courtreach-ee02b):
    usermatters/{ORG_OWNER_UID} = {matters: [{court, item, date, listType,
                                               title, bench, appearingFor,
                                               scope:"chamber", source:"daysheet",
                                               byLabel}]}

Idempotent and non-destructive: every matter this script writes is tagged
source:"daysheet". Each run REPLACES only that tagged subset for the dates in
the sync window — anything entered by hand in CourtReach (including a chamber
member's own personal matters, scope:"personal") is left completely alone.
Removing an entry from the day sheet removes it here on the next run; nothing
written by this script ever lingers once it's gone from the source.

Attribution: a day-sheet entry's juniorUids are SD-Chamber's own internal ids,
which don't correspond to CourtReach logins. Rather than require every junior
and clerk to also have a CourtReach account, we resolve their real name from
SD-Chamber's own users collection and carry it as a plain-text label (byLabel)
— CourtReach shows it as who's appearing without it being tied to an account.

Env vars — see DAYSHEET-SYNC-SETUP.md for how to obtain each one:
    SD_CHAMBER_SA_KEY    service-account JSON (as a string) for the SD-Chamber project
    COURTREACH_SA_KEY    service-account JSON (as a string) for the CourtReach project
    COURTREACH_ORG_UID   the target organisation's owner uid (CourtReach → Settings →
                          Organisation → "Organisation ID", owner only)
    SYNC_WINDOW_DAYS      how many days ahead to mirror (default 7)
"""
import os
import sys
import json
import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    sys.exit("Missing dependency — run: pip install firebase-admin")

WINDOW_DAYS = int(os.environ.get("SYNC_WINDOW_DAYS", "7"))


def _client(app_name, key_env):
    raw = os.environ.get(key_env)
    if not raw:
        sys.exit(f"Missing {key_env} — see DAYSHEET-SYNC-SETUP.md")
    try:
        key = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"{key_env} isn't valid JSON ({e}) — paste the whole service-account file.")
    app = firebase_admin.initialize_app(credentials.Certificate(key), name=app_name)
    return firestore.client(app)


def upcoming_dates(n):
    today = datetime.date.today()
    return [(today + datetime.timedelta(days=i)).isoformat() for i in range(n)]


def junior_names(sd_db):
    """uid -> real name, from SD-Chamber's own users collection."""
    names = {}
    for doc in sd_db.collection("users").stream():
        u = doc.to_dict() or {}
        if u.get("name"):
            names[doc.id] = u["name"]
    return names


def build_synced_matters(sd_db, names, dates):
    """One CourtReach-shaped matter per usable day-sheet entry across the window."""
    out = []
    for date in dates:
        snap = sd_db.collection("daysheets").document(date).get()
        if not snap.exists:
            continue
        entries = (snap.to_dict() or {}).get("entries") or []
        for e in entries:
            court = str(e.get("courtNo") or "").strip()
            item = str(e.get("itemNo") or "").strip()
            if not court or not item:
                continue  # oral mentionings / not-yet-numbered entries have nothing to list yet
            jr_uids = e.get("juniorUids") or ([e["juniorUid"]] if e.get("juniorUid") else [])
            jr_names = [n for n in (names.get(u, "") for u in jr_uids) if n]
            out.append({
                "id": "ds_" + date + "_" + court + "_" + item.replace(".", "-"),
                "court": court,
                "item": item,
                "date": date,
                "listType": e.get("listType") or "",
                "title": e.get("caseTitle") or "",
                "bench": e.get("bench") or "",
                "appearingFor": e.get("appearingFor") or "",
                "scope": "chamber",
                "source": "daysheet",
                "byLabel": " & ".join(jr_names),
            })
    return out


def main():
    org_uid = os.environ.get("COURTREACH_ORG_UID")
    if not org_uid:
        sys.exit("Missing COURTREACH_ORG_UID — see DAYSHEET-SYNC-SETUP.md")

    sd_db = _client("sdchamber", "SD_CHAMBER_SA_KEY")
    cr_db = _client("courtreach", "COURTREACH_SA_KEY")

    dates = upcoming_dates(WINDOW_DAYS)
    date_set = set(dates)
    fresh = build_synced_matters(sd_db, junior_names(sd_db), dates)

    ref = cr_db.collection("usermatters").document(org_uid)
    existing = ((ref.get().to_dict() or {}).get("matters")) or []
    # keep everything that ISN'T our own previous sync for a date in this window — a
    # member's own hand-entered matter, a personal-scope matter, or a date further out
    # than we mirror, all pass through untouched.
    kept = [m for m in existing if not (m.get("source") == "daysheet" and m.get("date") in date_set)]
    merged = kept + fresh

    # order-insensitive compare so an unchanged day sheet doesn't cause a needless write
    if sorted(json.dumps(m, sort_keys=True) for m in merged) == \
       sorted(json.dumps(m, sort_keys=True) for m in existing):
        print("No change.")
        return

    ref.set({"matters": merged, "updatedAt": firestore.SERVER_TIMESTAMP}, merge=True)
    print(f"Synced {len(fresh)} day-sheet matter(s) across {len(dates)} date(s) into {org_uid}.")


if __name__ == "__main__":
    main()
