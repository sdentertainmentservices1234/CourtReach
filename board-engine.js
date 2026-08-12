/* ============================================================================
   SD Chamber Display Board — PURE proximity engine (shared, server-ready)
   ----------------------------------------------------------------------------
   This is board.html's classify()/seq/order/passover logic with EVERY global it
   used to reach for lifted into an explicit `ctx`. Same maths, no DOM, no
   Firestore, no globals — so the identical file can run in the browser (thin
   client) AND inside the Cloudflare worker (/compute), and be unit-tested in
   isolation. It is deliberately byte-faithful to the live engine; a cross-check
   harness (board-engine-check) diffs it against the running board.html to prove
   they never disagree before anything ships.

   ctx (all optional; missing → treated as empty):
     nowMins          int    minutes-into-day IST (was nowMinsIST())
     seqByCourt       {court: "raw sequence text"}      (marquee, ?seq)
     remarksByCourt   {court: {items:{item: "OVER"|"PASS OVER"|…}}}
     poMarks          {"court_item": {mode,after,…}|null}   already date-filtered
     doneMarks        {"court_item": {v:"att"|"abs",…}|null} already date-filtered
     boardPO          {"court_item": true}                   currently outstanding, live-observed
     recalledPO       {"court_item": true}                   confirmed recalled earlier today —
                                                               tells classify() a court's passover
                                                               queue is already moving, not merely
                                                               declared
     itemHi           {court: highestRawItemSeenToday}
     miscTotalByCourt {court: int|null}   Misc list size (caller precomputes)
     boardByCourt     {court: bcRow}      the parsed board keyed by court
   ============================================================================ */
(function (root) {
  "use strict";
  const MENT_END = 640;          // 10:40 IST — mentioning done
  const REG_BASE = 101;          // Regular list numbered 101+
  const poKey = (court, item) => String(court) + "_" + String(item);

  // ---- pure sequence maths (identical to board.html) ----
  function isMentioning(item) { const s = String(item || "").trim(); return s !== "" && !/^\d/.test(s); }

  function seqInfo(text) {
    if (!text) return { seq: [], passIdx: null };
    const norm = String(text).replace(/(\d)\s*[-–—]\s*(\d)/g, "$1 TO $2");
    const toks = norm.toUpperCase().replace(/[^0-9A-Z. ]/g, " ").split(/\s+/).filter(Boolean);
    const out = [], seen = new Set(); let passIdx = null;
    const push = n => { if (!seen.has(n)) { seen.add(n); out.push(n); } };
    for (let i = 0; i < toks.length; i++) {
      const t = toks[i];
      if (passIdx == null && (t === "PASSOVER" || t === "PASSOVERS" || t === "PO" || (t === "PASS" && (toks[i + 1] === "OVER" || toks[i + 1] === "OVERS")))) passIdx = out.length;
      const num = t.match(/^(\d+)(?:\.\d+)?$/); if (!num) continue;
      const a = parseInt(num[1], 10);
      if (toks[i + 1] === "TO" && /^\d+$/.test(toks[i + 2] || "")) {
        const b = parseInt(toks[i + 2], 10);
        if (b >= a && b - a < 600) { for (let k = a; k <= b; k++) push(k); } else push(a); i += 2;
      } else push(a);
    }
    return { seq: out, passIdx };
  }

  function parseSequenceLine(text) {
    const out = {};
    if (!text) return out;
    const T = " " + String(text).toUpperCase().replace(/\s+/g, " ") + " ";
    const re = /COURT\s*(?:NO\.?|NUMBER|ROOM)?\s*(\d{1,2})\b/g;
    const anchors = []; let m;
    while ((m = re.exec(T))) anchors.push({ court: String(parseInt(m[1], 10)), afterNum: re.lastIndex });
    for (let i = 0; i < anchors.length; i++) {
      const a = anchors[i];
      const nextStart = (i + 1 < anchors.length) ? T.lastIndexOf("COURT", anchors[i + 1].afterNum) : T.length;
      let seg = T.slice(a.afterNum, nextStart).trim();
      seg = seg.replace(/^[:\-–.\s]+/, "");
      if (seg && seqInfo(seg).seq.length) out[a.court] = seg;
    }
    return out;
  }

  function orderPos(seq, item) {
    item = Math.floor(parseFloat(item)); if (isNaN(item)) return null;
    const i = seq.indexOf(item); if (i >= 0) return i;
    const seqSet = new Set(seq); let before = 0;
    for (let n = 1; n < item; n++) { if (!seqSet.has(n)) before++; }
    return seq.length + before;
  }

  function preStartGap(seqTxt, ours) {
    const { seq } = seqInfo(seqTxt); if (!seq.length) return null;
    const op = orderPos(seq, ours); return op == null ? null : op;
  }
  function preStartResult(g) {
    const short = g === 0 ? "up next" : g + " ahead";
    const lab = g === 0 ? "opens · you're up first" : "opens · ~" + g + " ahead in the sequence";
    return { tier: g <= 4 ? "soon" : "later", label: lab, short, gap: g, preStart: true };
  }

  // ---- ctx-backed overlays (were globals) ----
  function detailRemark(ctx, court, item) {
    const r = (ctx.remarksByCourt || {})[String(court)]; if (!r || !r.items) return "";
    const s = String(item); if (r.items[s]) return r.items[s];
    const n = String(Math.floor(parseFloat(item)));
    return (n !== "NaN" && r.items[n]) || "";
  }
  const isOver = (ctx, court, item) => /^over$/i.test(detailRemark(ctx, court, item));
  const isPassOver = (ctx, court, item) => /pass\s*over/i.test(detailRemark(ctx, court, item));

  function overAhead(ctx, court, curItem, ours) {
    const r = (ctx.remarksByCourt || {})[String(court)]; if (!r || !r.items) return 0;
    const c = parseFloat(curItem), o = parseFloat(ours); if (isNaN(c) || isNaN(o)) return 0;
    let n = 0;
    for (const k in r.items) {
      if (!/^over$/i.test(r.items[k])) continue;
      const v = parseFloat(k); if (!isNaN(v) && v > c && v < o) n++;
    }
    return n;
  }

  function passoverItemsFor(ctx, court) {
    const out = {};
    const add = (item, after) => {
      const n = Math.floor(parseFloat(item)); if (isNaN(n)) return;
      const a = (after != null && after !== "") ? Math.floor(parseFloat(after)) : null;
      if (!(n in out)) out[n] = { after: a }; else if (a != null && out[n].after == null) out[n].after = a;
    };
    const r = (ctx.remarksByCourt || {})[String(court)];
    if (r && r.items) for (const k in r.items) { if (/pass\s*over/i.test(r.items[k])) add(k, null); }
    const pm = ctx.poMarks || {};
    for (const key in pm) { if (!pm[key]) continue; const i = key.indexOf("_"); if (i > 0 && key.slice(0, i) === String(court)) add(key.slice(i + 1), pm[key] && pm[key].after); }
    const bpo = ctx.boardPO || {};
    for (const key in bpo) { if (!bpo[key]) continue; const i = key.indexOf("_"); if (i > 0 && key.slice(0, i) === String(court)) add(key.slice(i + 1), null); }
    return out;
  }

  function poAdjust(ctx, court, curItem, ours, seq, passIdx) {
    const po = passoverItemsFor(ctx, court); const keys = Object.keys(po); if (!keys.length) return 0;
    const useSeq = !!(seq && seq.length);
    const pos = n => { n = Math.floor(parseFloat(n)); if (isNaN(n)) return null; return useSeq ? seq.indexOf(n) : n; };
    const curP = pos(curItem), ourP = pos(ours);
    if (curP == null || ourP == null) return 0;
    if (useSeq && (curP < 0 || ourP < 0)) return 0;
    if (ourP <= curP) return 0;
    const endP = useSeq ? seq.length : Infinity;
    const ourN = Math.floor(parseFloat(ours));
    let delta = 0;
    for (const k of keys) {
      if (parseInt(k, 10) === ourN) continue;
      const xp = pos(k); if (xp == null || (useSeq && xp < 0)) continue;
      let rp;
      if (po[k].after != null) { const ap = pos(po[k].after); rp = (ap != null && !(useSeq && ap < 0)) ? ap + 1 : endP; }
      else rp = (useSeq && passIdx != null && passIdx > curP) ? passIdx : endP;
      const aheadOrig = xp > curP && xp < ourP;
      const recallAhead = rp > curP && rp < ourP;
      if (aheadOrig && !recallAhead) delta--;
      else if (!aheadOrig && recallAhead) delta++;
    }
    return delta;
  }
  // When passovers are taken at the END of the board (no sequence), ours is recalled
  // after every other passed-over matter with a lower item number (reached earlier).
  function passoversBeforeOurs(ctx, court, ours) {
    const po = passoverItemsFor(ctx, court); const ourN = Math.floor(parseFloat(ours));
    if (isNaN(ourN)) return 0;
    let n = 0; for (const k in po) { const kn = parseInt(k, 10); if (!isNaN(kn) && kn < ourN) n++; }
    return n;
  }
  // Has this court recalled ANY previously passed-over item today? Direct evidence the court
  // is actively working its passover queue rather than saving recalls for the very end —
  // classify() uses this to choose which of two estimates for OUR OWN passed-over matter to
  // trust (see the "mark" branch below).
  function hasRecalledPO(ctx, court) {
    const rp = ctx.recalledPO || {}; const prefix = String(court) + "_";
    for (const k in rp) { if (rp[k] && k.indexOf(prefix) === 0) return true; }
    return false;
  }

  const doneOf = (ctx, court, item) => (ctx.doneMarks || {})[poKey(court, item)] || null;
  const poFor = (ctx, court, item) => (ctx.poMarks || {})[poKey(court, item)] || null;
  const boardPOhas = (ctx, court, item) => !!(ctx.boardPO || {})[poKey(court, item)];

  const miscTotalFor = (ctx, court) => { const v = (ctx.miscTotalByCourt || {})[String(court)]; return (v == null ? null : v); };

  function onRegularList(ctx, court, miscTotal) {
    const bc = (ctx.boardByCourt || {})[court]; const cur = bc ? parseInt(bc.item, 10) : NaN;
    if (isNaN(cur)) return false;
    if (miscTotal == null) return false;
    if (cur > miscTotal + 2) return true;
    const hi = (ctx.itemHi || {})[court] || 0;
    if (hi >= miscTotal - 3 && cur >= REG_BASE && cur < hi - 5) return true;
    return false;
  }

  // ---- the classifier — faithful port of board.html classify(e,bc) ----
  function classify(e, bc, ctx) {
    ctx = ctx || {};
    const ours = e.itemNo;
    const dn = doneOf(ctx, e.courtNo, ours);
    if (dn) return { tier: "passed", label: dn.v === "att" ? "over — attended" : "over — not attended", short: dn.v === "att" ? "over ✓" : "over ✗", over: true, done: true };
    if (!bc) return { tier: "unknown", label: "court not on the board", short: "—" };
    const seqTxt = (bc.sequence && bc.sequence.trim()) ? bc.sequence : ((ctx.seqByCourt || {})[String(e.courtNo)] || "");
    if (/not in session/i.test(bc.status || "")) {
      const pg = preStartGap(seqTxt, ours);
      if (pg != null) return preStartResult(pg);
      return { tier: "idle", label: "court not sitting", short: "not sitting" };
    }
    if (isMentioning(ours)) {
      if ((ctx.nowMins || 0) > MENT_END) return { tier: "passed", label: "mentioning — over", short: "over", ment: true };
      return { tier: "soon", label: "mentioning — watch", short: "watch", gap: 0, ment: true };
    }
    const curBoardNum = parseInt(bc.item, 10);
    const oursNum = parseFloat(ours);
    const oursSingle = oursNum >= 1600 && oursNum < 1700, oursChamber = oursNum >= 1700 && oursNum < 1800;
    if (oursSingle || oursChamber) {
      const inPhase = (oursSingle && curBoardNum >= 1600 && curBoardNum < 1700) || (oursChamber && curBoardNum >= 1700 && curBoardNum < 1800);
      if (inPhase) {
        const g = Math.floor(oursNum) - Math.floor(curBoardNum);
        if (g < 0) return { tier: "passed", label: "matter is over", short: "over", gap: g };
        if (g <= 1) return { tier: "now", label: g === 0 ? "ITEM ON NOW" : "NEXT — get in", short: g === 0 ? "NOW" : "NEXT", gap: g };
        if (g <= 4) return { tier: "soon", label: "~" + g + " items away", short: g + " away", gap: g };
        return { tier: "later", label: g + " items away", short: g + " away", gap: g };
      }
      return { tier: "later", label: (oursSingle ? "Single Judge" : "Chamber Judge") + " list — after the board", short: "after board", reg: true };
    }
    if (curBoardNum >= 800 && curBoardNum < 900) return { tier: "soon", label: "mentioning is on", short: "mentioning", ment: true };
    if (curBoardNum >= 1500 && curBoardNum < 1600) return { tier: "soon", label: "pronouncement is on", short: "pronouncement" };
    if (curBoardNum >= 1600 && curBoardNum < 1700) return { tier: "soon", label: "Single Judge matters on", short: "single judge" };
    if (curBoardNum >= 1700 && curBoardNum < 1800) return { tier: "soon", label: "Chamber Judge matters on", short: "chamber" };
    if (isOver(ctx, e.courtNo, ours)) return { tier: "passed", label: "matter is over", short: "over", over: true };
    const { seq, passIdx } = seqInfo(seqTxt);
    const curPos = seq.length ? seq.indexOf(parseInt(bc.item, 10)) : -1;
    const mark = poFor(ctx, e.courtNo, ours)
      || (isPassOver(ctx, e.courtNo, ours) ? { mode: "detail" } : null)
      || (boardPOhas(ctx, e.courtNo, ours) ? { mode: "slot" } : null);
    if (mark) {
      let gap = null, tail = "";
      if (mark.mode === "after" && mark.after) {
        if (seq.length) { const tp = seq.indexOf(parseInt(mark.after, 10)); if (tp >= 0 && curPos >= 0) gap = Math.max(0, tp - curPos + 1); }
        else { const cur = parseInt(bc.item, 10), tp = parseInt(mark.after, 10); if (!isNaN(cur) && !isNaN(tp)) gap = Math.max(0, tp - cur + 1); }
        if (gap != null) tail = " · taken after item " + String(mark.after);
      } else if (seq.length && curPos >= 0) {
        const tp = (passIdx != null && passIdx > curPos) ? passIdx : seq.length - 1;
        gap = Math.max(0, tp - curPos);
      }
      // No sequence, no explicit recall point: two different estimates, chosen by whether we
      // have actual evidence of how this court is handling recalls today.
      //
      // Once the court has recalled at least one OTHER passed-over item today (hasRecalledPO),
      // that's direct proof it's already working its passover queue interleaved with fresh
      // business, not saving them for later — so rank purely by how many other still-
      // outstanding passovers are ahead of ours (owner: "once passovers cases are taken up the
      // app is failing to see sequence of passovers and failing to calculate how far our case
      // which was 4th passover in line is"). passoversBeforeOurs() only counts items STILL in
      // recalledPO/boardPO's live-observed set, so as each one gets recalled in turn it drops
      // out and this count — and therefore our own gap — shrinks in step, the same way any
      // other "N away" queue does elsewhere in this file.
      //
      // Before any recall has been observed for this court today, there's no evidence either
      // way, so fall back to the original assumption: recalls wait for the rest of the list.
      // Getting this wrong in THAT direction is the safer failure — it under-promises rather
      // than telling someone their matter is closer than it is.
      if (gap == null) {
        if (hasRecalledPO(ctx, e.courtNo)) {
          gap = passoversBeforeOurs(ctx, e.courtNo, ours); tail = " · in the passover queue";
        } else {
          const total = miscTotalFor(ctx, e.courtNo), cur = parseInt(bc.item, 10);
          if (total != null && !isNaN(cur)) { gap = Math.max(0, total - cur) + passoversBeforeOurs(ctx, e.courtNo, ours); tail = " · taken at end"; }
        }
      }
      if (gap == null) return { tier: "later", label: "passed over — awaiting its turn", short: "passed over", po: true };
      if (gap <= 0) return { tier: "now", label: "passed over — item on now", short: "NOW", gap, po: true };
      if (gap === 1) return { tier: "now", label: "passed over — next", short: "NEXT", gap, po: true };
      if (gap <= 4) return { tier: "soon", label: "~" + gap + " items away · passed over" + tail, short: gap + " away", gap, po: true };
      return { tier: "later", label: gap + " items away · passed over" + tail, short: gap + " away", gap, po: true };
    }
    if (/^reg/i.test((e.listType || "").trim())) {
      const miscTotal = miscTotalFor(ctx, e.courtNo);
      if (!onRegularList(ctx, e.courtNo, miscTotal)) {
        const regRank = (Math.floor(oursNum) >= REG_BASE) ? (Math.floor(oursNum) - (REG_BASE - 1)) : Math.max(1, Math.floor(oursNum) || 1);
        if (miscTotal == null && !seq.length)
          return { tier: "later", label: "Regular list — after the Miscellaneous list", short: "after Misc", reg: true };
        const cur = parseInt(bc.item, 10);
        // miscDone approximates "how far into Misc has the court actually gotten" — but once
        // recalls are happening, the board's CURRENT item can be a low-numbered passover being
        // recalled right now, which is a temporary DIP, not real regression. Using cur alone
        // there would read that dip as "only just started Misc" and wildly overstate what's
        // left (owner's report: Court 8 showing 21 away with only three passovers and three
        // Regular matters actually outstanding — 21 is explained exactly by this: cur reading
        // a recalled low item while the court had genuinely already reached item ~97+ of a
        // ~100 Misc list). itemHi (the highest raw item any poll has seen at this court today)
        // never regresses on a recall the way cur does — same signal onRegularList() already
        // trusts for its own "has this court moved past Misc" call — so take whichever is
        // higher.
        const hi = (ctx.itemHi || {})[e.courtNo] || 0;
        const miscDone = (seq.length && curPos >= 0) ? curPos + 1 : Math.max(isNaN(cur) ? 0 : cur, hi);
        const miscLeft = Math.max(0, (miscTotal != null ? miscTotal : seq.length) - miscDone);
        // Misc's own outstanding passovers are still Misc business, not yet disposed, and
        // Misc must finish before Regular starts — so they count toward the gap too (owner:
        // "miscellaneous list comes first before the regular list and so also any passover
        // from the miscellaneous list comes first before regular list ... unless there is a
        // specific sequence provides for otherwise"). Concrete worked example that shaped
        // this: Court 8, item 31 current, Misc total 35, six outstanding Misc passovers, our
        // matter is Regular #104 (regRank 4) — expected gap = 6 (passovers) + 4 (Misc left:
        // 32-35) + 3 (Regular ahead: 101-103) = 13.
        //
        // Only passovers AT OR BEHIND the court's REACH so far count here — one still ahead of
        // that (item > miscDone) is already inside miscLeft above (it hasn't been reached OR
        // skipped yet from our vantage point), so adding it again would double it. Boundary is
        // miscDone (== max(cur,hi)), not cur alone, for the same reason miscDone itself uses
        // it: a passover with item number between a temporary recall dip and the court's real
        // peak was genuinely already reached and skipped, and using cur here would silently
        // drop it from the gap entirely — not double-counted, just gone.
        //
        // The exception: if the announced sequence explicitly places Regular items BEFORE its
        // mention of passovers (i.e. the court is saying "101-120 first, passovers after"),
        // that overrides the default — those passovers are no longer Misc-first business.
        const poException = seq.length && passIdx != null && seq.slice(0, passIdx).some(n => n >= REG_BASE);
        let miscPOLeft = 0;
        if (!poException) {
          const po = passoverItemsFor(ctx, e.courtNo);
          const miscCeil = miscTotal != null ? miscTotal : (REG_BASE - 1);
          for (const k in po) { const n = parseInt(k, 10); if (!isNaN(n) && n <= miscCeil && n <= miscDone) miscPOLeft++; }
        }
        const gap = miscLeft + miscPOLeft + (regRank - 1);
        const detail = (miscLeft > 0 || miscPOLeft > 0)
          ? "Misc: " + miscLeft + " to go" + (miscPOLeft ? " · " + miscPOLeft + " passover" + (miscPOLeft === 1 ? "" : "s") : "")
          : "Misc done";
        if (gap <= 1) return { tier: "now", label: "Regular — get in now", short: "NOW", gap, reg: true };
        if (gap <= 4) return { tier: "soon", label: "Regular — ~" + gap + " away · " + detail, short: gap + " away", gap, reg: true };
        return { tier: "later", label: "Regular — ~" + gap + " away · " + detail, short: gap + " away", gap, reg: true };
      }
    }
    let gap = null, approx = false;
    if (seq.length) { const op = orderPos(seq, ours), cp = orderPos(seq, bc.item); if (op != null && cp != null) gap = op - cp; }
    if (gap == null) { const c = parseFloat(bc.item); if (!isNaN(c)) { gap = Math.floor(oursNum) - Math.floor(c); approx = true; } }
    if (gap != null && gap > 0) { const done = overAhead(ctx, e.courtNo, bc.item, ours); if (done > 0) gap = Math.max(0, gap - done); }
    let poNote = "";
    if (gap != null) { const pa = poAdjust(ctx, e.courtNo, bc.item, ours, seq, passIdx); if (pa) { gap = Math.max(0, gap + pa); poNote = pa < 0 ? " · " + (-pa) + " passed over ahead" : " · " + pa + " recalled first"; } }
    if (gap == null) { const pg = preStartGap(seqTxt, ours); if (pg != null) return preStartResult(pg); }
    if (gap == null) return { tier: "unknown", label: "position unclear", short: "—" };
    if (gap < 0) return { tier: "passed", label: "matter is over", short: "over", gap, approx };
    if (gap <= 1) return { tier: "now", label: gap === 0 ? "ITEM ON NOW" : "NEXT — get in", short: gap === 0 ? "NOW" : "NEXT", gap, approx, poNote };
    if (gap <= 4) return { tier: "soon", label: "~" + gap + " items away" + poNote, short: gap + " away", gap, approx, poNote };
    return { tier: "later", label: gap + " items away" + poNote, short: gap + " away", gap, approx, poNote };
  }

  const API = { classify, seqInfo, orderPos, parseSequenceLine, preStartGap, preStartResult, isMentioning, MENT_END, REG_BASE, passoverItemsFor };
  root.BoardEngine = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof self !== "undefined" ? self : (typeof globalThis !== "undefined" ? globalThis : this));
