"use strict";
(function () {
  const D = JSON.parse(document.getElementById("tqqq-data").textContent);
  const { dates, tqqq, qqq, months, monthIdx } = D;

  /* ---------- helpers ---------- */
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const $ = (id) => document.getElementById(id);

  function fmtKRW(v) {
    const a = Math.abs(v);
    if (a >= 1e12) return (v / 1e12).toFixed(2) + "조";
    if (a >= 1e8) return (v / 1e8).toFixed(a >= 1e9 ? 1 : 2) + "억";
    if (a >= 1e4) return Math.round(v / 1e4).toLocaleString() + "만";
    return Math.round(v).toLocaleString();
  }
  function fmtX(v) {
    if (v >= 100) return v.toFixed(0) + "배";
    if (v >= 10) return v.toFixed(1) + "배";
    return v.toFixed(2) + "배";
  }
  const parseNum = (s) => {
    const n = Number(String(s).replace(/[^0-9.]/g, ""));
    return isFinite(n) ? n : 0;
  };
  const commas = (n) => Math.round(n).toLocaleString();
  const ymLabel = (ym) => ym.slice(0, 4) + "." + ym.slice(5, 7);

  /* ---------- state ---------- */
  const state = {
    init: 1e8, monthly: 15e5, years: 10, goal: 5e8,
    sel: null, rows: [], hoverRoll: null, hoverPath: null,
  };

  /* ---------- core simulation ---------- */
  function runRolling() {
    const { init, monthly, years, goal } = state;
    const need = years * 12;
    const rows = [];
    for (let s = 0; s + need < months.length; s++) {
      const i0 = monthIdx[s], i1 = monthIdx[s + need];
      let uT = init / tqqq[i0], uQ = init / qqq[i0];
      let principal = init;
      let peakT = init, peakQ = init, mddT = 0, mddQ = 0;
      let gT = -1, gQ = -1;
      let mi = s + 1;
      for (let i = i0; i <= i1; i++) {
        if (mi <= s + need && i === monthIdx[mi]) {
          if (monthly > 0) {
            uT += monthly / tqqq[i];
            uQ += monthly / qqq[i];
            principal += monthly;
          }
          mi++;
        }
        const vT = uT * tqqq[i], vQ = uQ * qqq[i];
        if (vT > peakT) peakT = vT;
        else { const d = vT / peakT - 1; if (d < mddT) mddT = d; }
        if (vQ > peakQ) peakQ = vQ;
        else { const d = vQ / peakQ - 1; if (d < mddQ) mddQ = d; }
        if (gT < 0 && vT >= goal) gT = i;
        if (gQ < 0 && vQ >= goal) gQ = i;
      }
      rows.push({
        si: s, start: months[s], end: months[s + need], i0, i1,
        T: uT * tqqq[i1], Q: uQ * qqq[i1], principal,
        mddT, mddQ, goalT: gT, goalQ: gQ,
      });
    }
    return rows;
  }

  function pathFor(row) {
    const { init, monthly, years } = state;
    const need = years * 12;
    let uT = init / tqqq[row.i0], uQ = init / qqq[row.i0];
    let principal = init, mi = row.si + 1;
    const out = { t: [], q: [], p: [], idx: [] };
    for (let i = row.i0; i <= row.i1; i++) {
      if (mi <= row.si + need && i === monthIdx[mi]) {
        if (monthly > 0) {
          uT += monthly / tqqq[i];
          uQ += monthly / qqq[i];
          principal += monthly;
        }
        mi++;
      }
      out.idx.push(i);
      out.t.push(uT * tqqq[i]);
      out.q.push(uQ * qqq[i]);
      out.p.push(principal);
    }
    return out;
  }

  /* ---------- canvas base ---------- */
  function setupCanvas(cv) {
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth, h = cv.clientHeight;
    cv.width = Math.round(w * dpr);
    cv.height = Math.round(h * dpr);
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
  }

  function niceLogTicks(lo, hi) {
    const ticks = [];
    const a = Math.floor(Math.log10(lo)), b = Math.ceil(Math.log10(hi));
    for (let e = a; e <= b; e++) {
      for (const m of [1, 2, 5]) {
        const v = m * Math.pow(10, e);
        if (v >= lo * 0.98 && v <= hi * 1.02) ticks.push(v);
      }
    }
    return ticks;
  }

  /* ---------- chart 1: rolling ---------- */
  const rollGeo = { pad: null, rows: null };

  function drawRolling() {
    const cv = $("c-roll");
    const { ctx, w, h } = setupCanvas(cv);
    const rows = state.rows;
    if (!rows.length) return;

    const pad = { l: 56, r: 14, t: 10, b: 26 };
    const PW = w - pad.l - pad.r, PH = h - pad.t - pad.b;

    let lo = Infinity, hi = -Infinity;
    for (const r of rows) {
      const a = r.T / r.principal, b = r.Q / r.principal;
      if (a > 0) { lo = Math.min(lo, a); hi = Math.max(hi, a); }
      if (b > 0) { lo = Math.min(lo, b); hi = Math.max(hi, b); }
    }
    lo = Math.max(lo * 0.75, 1e-4); hi = hi * 1.3;
    const L = Math.log10(lo), H = Math.log10(hi);
    const Y = (v) => pad.t + PH - ((Math.log10(Math.max(v, lo)) - L) / (H - L)) * PH;
    const X = (i) => pad.l + (i / Math.max(1, rows.length - 1)) * PW;

    const cLine = css("--line"), cMuted = css("--muted"), cT = css("--tqqq"), cQ = css("--qqq");

    // grid + y labels
    ctx.font = '11px "IBM Plex Mono", monospace';
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (const t of niceLogTicks(lo, hi)) {
      const y = Y(t);
      ctx.strokeStyle = cLine; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.l, Math.round(y) + .5); ctx.lineTo(w - pad.r, Math.round(y) + .5); ctx.stroke();
      ctx.fillStyle = cMuted;
      ctx.fillText(fmtX(t), pad.l - 8, y);
    }
    // principal line (1.0x)
    if (1 >= lo && 1 <= hi) {
      const y = Math.round(Y(1)) + .5;
      ctx.save(); ctx.setLineDash([4, 4]); ctx.strokeStyle = cMuted; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke(); ctx.restore();
    }

    // x labels (years)
    ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillStyle = cMuted;
    let lastYr = null;
    const step = Math.max(1, Math.round(rows.length / 12));
    for (let i = 0; i < rows.length; i += step) {
      const yr = rows[i].start.slice(0, 4);
      if (yr !== lastYr) { ctx.fillText(yr, X(i), pad.t + PH + 7); lastYr = yr; }
    }

    // series
    const draw = (key, color) => {
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.beginPath();
      rows.forEach((r, i) => {
        const v = r[key] / r.principal;
        const x = X(i), y = Y(v);
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      });
      ctx.stroke();
    };
    draw("Q", cQ);
    draw("T", cT);

    // marker: selected (dashed) and hovered (solid crosshair)
    const marker = (i, dashed) => {
      if (i == null || i < 0 || i >= rows.length) return;
      const x = X(i);
      ctx.save();
      ctx.strokeStyle = cMuted; ctx.lineWidth = 1;
      if (dashed) ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, pad.t + PH); ctx.stroke();
      ctx.restore();
      for (const [k, c] of [["T", cT], ["Q", cQ]]) {
        ctx.fillStyle = c; ctx.strokeStyle = css("--panel"); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(x, Y(rows[i][k] / rows[i].principal), 4.5, 0, 7); ctx.fill(); ctx.stroke();
      }
    };
    if (state.sel != null) marker(rows.findIndex((r) => r.si === state.sel), true);
    if (state.hoverRoll != null) marker(state.hoverRoll, false);
    rollGeo.pad = pad; rollGeo.X = X; rollGeo.Y = Y; rollGeo.w = w; rollGeo.h = h;
  }

  /* ---------- chart 2: path ---------- */
  const pathGeo = {};

  function drawPath() {
    const cv = $("c-path");
    const { ctx, w, h } = setupCanvas(cv);
    const row = state.rows.find((r) => r.si === state.sel);
    if (!row) return;
    const p = pathFor(row);
    pathGeo.p = p;

    const pad = { l: 60, r: 14, t: 10, b: 26 };
    const PW = w - pad.l - pad.r, PH = h - pad.t - pad.b;

    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < p.t.length; i++) {
      for (const v of [p.t[i], p.q[i], p.p[i]]) {
        if (v > 0) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
      }
    }
    lo = Math.max(lo * .7, 1); hi *= 1.25;
    const L = Math.log10(lo), H = Math.log10(hi);
    const Y = (v) => pad.t + PH - ((Math.log10(Math.max(v, lo)) - L) / (H - L)) * PH;
    const X = (i) => pad.l + (i / Math.max(1, p.t.length - 1)) * PW;

    const cLine = css("--line"), cMuted = css("--muted"), cT = css("--tqqq"), cQ = css("--qqq");
    ctx.font = '11px "IBM Plex Mono", monospace';
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (const t of niceLogTicks(lo, hi)) {
      const y = Y(t);
      ctx.strokeStyle = cLine; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.l, Math.round(y) + .5); ctx.lineTo(w - pad.r, Math.round(y) + .5); ctx.stroke();
      ctx.fillStyle = cMuted; ctx.fillText(fmtKRW(t), pad.l - 8, y);
    }
    ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillStyle = cMuted;
    let lastYr = null;
    const step = Math.max(1, Math.round(p.idx.length / 10));
    for (let i = 0; i < p.idx.length; i += step) {
      const yr = dates[p.idx[i]].slice(0, 4);
      if (yr !== lastYr) { ctx.fillText(yr, X(i), pad.t + PH + 7); lastYr = yr; }
    }

    // principal (dashed)
    ctx.save(); ctx.setLineDash([4, 4]); ctx.strokeStyle = cMuted; ctx.lineWidth = 1.5;
    ctx.beginPath();
    p.p.forEach((v, i) => { const x = X(i), y = Y(v); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke(); ctx.restore();

    const draw = (arr, color) => {
      ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.beginPath();
      arr.forEach((v, i) => { const x = X(i), y = Y(v); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      ctx.stroke();
    };
    draw(p.q, cQ);
    draw(p.t, cT);

    if (state.hoverPath != null && state.hoverPath >= 0 && state.hoverPath < p.t.length) {
      const i = state.hoverPath, x = X(i);
      ctx.strokeStyle = cMuted; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, pad.t + PH); ctx.stroke();
      for (const [arr, c] of [[p.t, cT], [p.q, cQ]]) {
        ctx.fillStyle = c; ctx.strokeStyle = css("--panel"); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(x, Y(arr[i]), 4.5, 0, 7); ctx.fill(); ctx.stroke();
      }
    }

    pathGeo.pad = pad; pathGeo.X = X; pathGeo.Y = Y; pathGeo.w = w; pathGeo.h = h; pathGeo.row = row;
  }

  /* ---------- tooltips ---------- */
  function bindTip(cvId, tipId, handler, hoverKey, redrawFn) {
    const cv = $(cvId), tip = $(tipId);
    const move = (e) => {
      const r = cv.getBoundingClientRect();
      const x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
      const res = handler(x, r.width);
      if (!res) { tip.style.opacity = 0; return; }
      if (state[hoverKey] !== res.i) { state[hoverKey] = res.i; redrawFn(); }
      tip.innerHTML = res.html;
      tip.style.opacity = 1;
      const tw = tip.offsetWidth;
      let left = res.x + 14;
      if (left + tw > r.width) left = res.x - tw - 14;
      tip.style.left = Math.max(0, left) + "px";
      tip.style.top = "10px";
    };
    cv.addEventListener("mousemove", move);
    cv.addEventListener("touchmove", (e) => { move(e); }, { passive: true });
    cv.addEventListener("mouseleave", () => {
      tip.style.opacity = 0;
      if (state[hoverKey] != null) { state[hoverKey] = null; redrawFn(); }
    });
  }

  function tipRow(color, label, value) {
    return '<div class="t-row"><span class="lab"><i class="sw" style="background:' + color + '"></i>' +
      label + '</span><span class="val">' + value + "</span></div>";
  }

  /* ---------- render: stats / dist / goal / table ---------- */
  function renderStats() {
    const rows = state.rows;
    const n = rows.length;
    const win = rows.filter((r) => r.T > r.Q).length;
    const under = rows.filter((r) => r.T < r.principal).length;
    const mults = rows.map((r) => r.T / r.principal).sort((a, b) => a - b);
    const qmults = rows.map((r) => r.Q / r.principal).sort((a, b) => a - b);
    const med = mults[Math.floor(n / 2)], qmed = qmults[Math.floor(n / 2)];
    const worst = rows.reduce((a, b) => (a.T / a.principal < b.T / b.principal ? a : b));

    const el = (k, v, d, alert) =>
      '<div class="stat' + (alert ? " alert" : "") + '"><div class="k">' + k +
      '</div><div class="v">' + v + '</div><div class="d">' + d + "</div></div>";

    $("stats").innerHTML =
      el("TQQQ 승률", (win / n * 100).toFixed(1) + "%",
        n + "개 시작월 중 " + win + "회 QQQ 초과") +
      el("원금 손실 확률", (under / n * 100).toFixed(1) + "%",
        under + "회는 원금도 못 건짐", under / n > 0.15) +
      el("TQQQ 중앙값", fmtX(med), "QQQ 중앙값 " + fmtX(qmed)) +
      el("최악의 시작월", ymLabel(worst.start),
        fmtKRW(worst.principal) + " → " + fmtKRW(worst.T) + " (" + fmtX(worst.T / worst.principal) + ")", true);
  }

  function renderDist() {
    const rows = state.rows, n = rows.length;
    const mT = rows.map((r) => r.T / r.principal).sort((a, b) => a - b);
    const mQ = rows.map((r) => r.Q / r.principal).sort((a, b) => a - b);
    const at = (a, p) => a[Math.min(n - 1, Math.floor(n * p))];
    const marks = [[0, "최악"], [.1, "하위10%"], [.25, "하위25%"], [.5, "중앙"], [.75, "상위25%"], [.9, "상위10%"], [.999, "최고"]];
    const maxV = Math.max(at(mT, .999), at(mQ, .999));
    const scale = (v) => Math.max(2, (Math.log10(Math.max(v, .01)) - Math.log10(.01)) / (Math.log10(maxV) - Math.log10(.01)) * 100);

    let html = '<div class="dist-head"><span></span><span>TQQQ</span><span>QQQ</span></div>';
    for (const [p, lbl] of marks) {
      const a = at(mT, p), b = at(mQ, p);
      html += '<div class="dist-row"><div class="lbl">' + lbl + "</div>" +
        '<div class="dist-bar"><i style="width:' + scale(a) + "%;background:" +
        (a < 1 ? "var(--danger-soft)" : "var(--tqqq-soft)") + ";border-right:2px solid " +
        (a < 1 ? "var(--danger)" : "var(--tqqq)") + '"></i><span>' + fmtX(a) + "</span></div>" +
        '<div class="dist-bar"><i style="width:' + scale(b) + "%;background:var(--qqq-soft);border-right:2px solid var(--qqq)" +
        '"></i><span>' + fmtX(b) + "</span></div></div>";
    }
    html += '<p style="font-size:12.5px;color:var(--muted);margin:12px 0 0">' +
      "1.0배 미만은 원금 손실. TQQQ는 중앙값이 QQQ보다 높아도 하위 구간이 훨씬 깊다.</p>";
    $("dist").innerHTML = html;
  }

  function renderGoal() {
    const rows = state.rows, n = rows.length;
    const okT = rows.filter((r) => r.goalT >= 0), okQ = rows.filter((r) => r.goalQ >= 0);
    const yrs = (r, k) => (r[k] - r.i0) / 252;
    const medOf = (a, k) => {
      if (!a.length) return null;
      const s = a.map((r) => yrs(r, k)).sort((x, y) => x - y);
      return s[Math.floor(s.length / 2)];
    };
    const mT = medOf(okT, "goalT"), mQ = medOf(okQ, "goalQ");
    const both = rows.filter((r) => r.goalT >= 0 && r.goalQ >= 0);
    const faster = both.filter((r) => r.goalT < r.goalQ).length;

    const box = (who, color, cnt, med) =>
      '<div class="goal-box"><div class="who"><i class="sw" style="width:9px;height:9px;border-radius:2px;background:' +
      color + '"></i>' + who + "</div><div class=\"big\">" + (cnt / n * 100).toFixed(0) + "%</div>" +
      '<div class="sm">' + cnt + " / " + n + "개 시작월 도달<br>" +
      (med == null ? "—" : "중앙 " + med.toFixed(1) + "년 소요") + "</div></div>";

    $("goal").innerHTML =
      '<div class="goal-grid">' +
      box("TQQQ", "var(--tqqq)", okT.length, mT) +
      box("QQQ", "var(--qqq)", okQ.length, mQ) +
      "</div>" +
      '<p style="font-size:12.5px;color:var(--muted);margin:12px 0 0">' +
      "둘 다 도달한 " + both.length + "개 구간 중 TQQQ가 먼저 닿은 건 <b>" + faster +
      "회(" + (both.length ? (faster / both.length * 100).toFixed(0) : 0) + "%)</b>. " +
      "목표 " + fmtKRW(state.goal) + " · " + state.years + "년 내 · 세전 달러 기준.</p>";
  }

  function renderTable() {
    const rows = [...state.rows].sort((a, b) => a.T / a.Q - b.T / b.Q).slice(0, 10);
    let html = "<thead><tr><th>시작</th><th>종료</th><th>납입원금</th><th>TQQQ</th><th>QQQ</th>" +
      "<th>배수</th><th>TQQQ MDD</th><th></th></tr></thead><tbody>";
    for (const r of rows) {
      const lost = r.T < r.principal;
      html += '<tr class="clickable' + (r.si === state.sel ? " sel" : "") + '" data-si="' + r.si + '">' +
        "<td>" + ymLabel(r.start) + "</td><td>" + ymLabel(r.end) + "</td>" +
        '<td class="n">' + fmtKRW(r.principal) + "</td>" +
        '<td class="n" style="color:var(--tqqq)">' + fmtKRW(r.T) + "</td>" +
        '<td class="n" style="color:var(--qqq)">' + fmtKRW(r.Q) + "</td>" +
        '<td class="n">' + fmtX(r.T / r.principal) + "</td>" +
        '<td class="n">' + (r.mddT * 100).toFixed(1) + "%</td>" +
        "<td>" + (lost ? '<span class="pill bad">원금손실</span>' : '<span class="pill lose">QQQ 우세</span>') + "</td></tr>";
    }
    $("t-worst").innerHTML = html + "</tbody>";
    $("t-worst").querySelectorAll("tr.clickable").forEach((tr) => {
      tr.addEventListener("click", () => select(Number(tr.dataset.si)));
    });
  }

  function renderPathStats() {
    const row = state.rows.find((r) => r.si === state.sel);
    if (!row) return;
    const el = (k, v, d, cls) =>
      '<div class="stat"><div class="k">' + k + '</div><div class="v"' +
      (cls ? ' style="color:' + cls + '"' : "") + ">" + v + '</div><div class="d">' + d + "</div></div>";
    $("path-stats").innerHTML =
      el("납입 원금", fmtKRW(row.principal), state.years + "년간 총 투입") +
      el("TQQQ 최종", fmtKRW(row.T), fmtX(row.T / row.principal) + " · MDD " + (row.mddT * 100).toFixed(1) + "%", "var(--tqqq)") +
      el("QQQ 최종", fmtKRW(row.Q), fmtX(row.Q / row.principal) + " · MDD " + (row.mddQ * 100).toFixed(1) + "%", "var(--qqq)") +
      el("차이", (row.T >= row.Q ? "+" : "") + fmtKRW(row.T - row.Q),
        row.T >= row.Q ? "TQQQ가 앞섬" : "TQQQ가 뒤짐",
        row.T >= row.Q ? "var(--tqqq)" : "var(--danger)");
    $("detail-note").textContent =
      ymLabel(row.start) + " 시작 · " + ymLabel(row.end) + " 종료 · " + state.years + "년";
  }

  function select(si) {
    state.sel = si;
    drawRolling(); drawPath(); renderPathStats(); renderTable();
  }

  /* ---------- recompute ---------- */
  function recompute() {
    state.rows = runRolling();
    if (state.sel == null || !state.rows.some((r) => r.si === state.sel)) {
      const worst = state.rows.reduce((a, b) => (a.T / a.Q < b.T / b.Q ? a : b));
      state.sel = worst.si;
    }
    renderStats(); renderDist(); renderGoal(); renderTable();
    drawRolling(); drawPath(); renderPathStats();
  }

  /* ---------- inputs ---------- */
  function hookNum(id, hintId, key) {
    const inp = $(id), hint = $(hintId);
    const sync = () => {
      const v = parseNum(inp.value);
      state[key] = v;
      hint.textContent = v ? fmtKRW(v) + " 원" : "0";
    };
    inp.addEventListener("input", () => {
      const caretEnd = inp.selectionStart === inp.value.length;
      const v = parseNum(inp.value);
      inp.value = v ? commas(v) : "";
      if (caretEnd) inp.setSelectionRange(inp.value.length, inp.value.length);
      sync(); recompute();
    });
    sync();
  }

  hookNum("f-init", "h-init", "init");
  hookNum("f-monthly", "h-monthly", "monthly");
  hookNum("f-goal", "h-goal", "goal");

  $("seg-years").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-y]");
    if (!b) return;
    [...$("seg-years").children].forEach((x) => x.removeAttribute("aria-pressed"));
    b.setAttribute("aria-pressed", "true");
    state.years = Number(b.dataset.y);
    state.sel = null;
    recompute();
  });

  /* ---------- chart interaction ---------- */
  bindTip("c-roll", "tip-roll", (mx, cw) => {
    const rows = state.rows;
    if (!rows.length || !rollGeo.pad) return null;
    const { pad } = rollGeo;
    const PW = cw - pad.l - pad.r;
    let i = Math.round(((mx - pad.l) / PW) * (rows.length - 1));
    i = Math.max(0, Math.min(rows.length - 1, i));
    const r = rows[i];
    const html =
      '<div class="t-date">' + ymLabel(r.start) + " 시작 → " + ymLabel(r.end) + "</div>" +
      tipRow(css("--tqqq"), "TQQQ", fmtKRW(r.T) + "  " + fmtX(r.T / r.principal)) +
      tipRow(css("--qqq"), "QQQ", fmtKRW(r.Q) + "  " + fmtX(r.Q / r.principal)) +
      '<div class="t-sep"></div>' +
      tipRow(css("--muted"), "납입원금", fmtKRW(r.principal)) +
      '<div class="t-note">TQQQ 최대낙폭 ' + (r.mddT * 100).toFixed(1) + "% · 클릭하면 이 투자의 경로를 봅니다</div>";
    return { html, x: rollGeo.X(i), i };
  }, "hoverRoll", drawRolling);

  $("c-roll").addEventListener("click", (e) => {
    const rows = state.rows;
    if (!rows.length || !rollGeo.pad) return;
    const r = $("c-roll").getBoundingClientRect();
    const { pad } = rollGeo;
    const PW = r.width - pad.l - pad.r;
    let i = Math.round(((e.clientX - r.left - pad.l) / PW) * (rows.length - 1));
    i = Math.max(0, Math.min(rows.length - 1, i));
    select(rows[i].si);
    document.getElementById("detail-title").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  bindTip("c-path", "tip-path", (mx, cw) => {
    const p = pathGeo.p;
    if (!p || !pathGeo.pad) return null;
    const { pad } = pathGeo;
    const PW = cw - pad.l - pad.r;
    let i = Math.round(((mx - pad.l) / PW) * (p.t.length - 1));
    i = Math.max(0, Math.min(p.t.length - 1, i));
    const html =
      '<div class="t-date">' + dates[p.idx[i]] + "</div>" +
      tipRow(css("--tqqq"), "TQQQ", fmtKRW(p.t[i])) +
      tipRow(css("--qqq"), "QQQ", fmtKRW(p.q[i])) +
      '<div class="t-sep"></div>' +
      tipRow(css("--muted"), "누적 원금", fmtKRW(p.p[i])) +
      '<div class="t-note">원금 대비 TQQQ ' + fmtX(p.t[i] / p.p[i]) + " · QQQ " + fmtX(p.q[i] / p.p[i]) + "</div>";
    return { html, x: pathGeo.X(i), i };
  }, "hoverPath", drawPath);

  /* ---------- meta ---------- */
  $("m-range").textContent = D.start + " ~ " + D.end;
  $("m-days").textContent = D.n.toLocaleString() + "일";
  $("m-real").textContent = dates[D.realFrom.tqqq] + "부터";
  $("mm-b").textContent = D.coef ? D.coef.b.toFixed(4) : "1.0398";
  $("mm-c").textContent = D.coef ? D.coef.c.toFixed(5) : "0.00151";
  $("foot-built").textContent = "생성 " + (D.built || "");

  /* ---------- redraw on resize / theme ---------- */
  let raf = null;
  const redraw = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => { drawRolling(); drawPath(); });
  };
  new ResizeObserver(redraw).observe($("host-roll"));
  new ResizeObserver(redraw).observe($("host-path"));
  if (window.matchMedia) {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener ? mq.addEventListener("change", redraw) : mq.addListener(redraw);
  }
  new MutationObserver(redraw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  recompute();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(redraw);
})();
