/* Nazorat markazi: jonli yangilanish, soat, xarita boshqaruvi, toast */
(function () {
  document.body.addEventListener("htmx:configRequest", (event) => {
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) event.detail.headers["X-CSRF-Token"] = token.content;
  });
  // ---- soat ----
  const base = new Date(document.body.dataset.now || Date.now());
  const drift = Date.now() - base.getTime();
  function tick() {
    const d = new Date(Date.now() - drift);
    const pad = (n) => String(n).padStart(2, "0");
    const t = document.getElementById("clock-time"), dt = document.getElementById("clock-date");
    if (t) t.textContent = pad(d.getHours()) + ":" + pad(d.getMinutes());
    if (dt) dt.textContent = pad(d.getDate()) + "." + pad(d.getMonth() + 1) + "." + d.getFullYear();
  }
  setInterval(tick, 1000); tick();

  // ---- WebSocket jonli oqim ----
  let ws, retry = 1000, lastLive = 0;
  function liveTrigger() {
    const now = Date.now();
    if (now - lastLive < 1500) { clearTimeout(liveTrigger._t); liveTrigger._t = setTimeout(liveTrigger, 1500); return; }
    lastLive = now;
    if (window.htmx) htmx.trigger(document.body, "live");
  }
  function toast(msg) {
    if (!msg || msg.level === "INFO") return;
    let root = document.getElementById("toast-root");
    if (!root) return;
    root.className = "toast";
    const el = document.createElement("div");
    el.className = "toast-item lv-" + msg.level;
    const level = document.createElement("b"), title = document.createElement("span");
    level.textContent = msg.level || "";
    title.textContent = msg.title || msg.event_type || "";
    el.append(level, title);
    if (msg.cabinet_id) { el.style.cursor = "pointer"; el.onclick = () => location.href = "/yacheyka/" + msg.cabinet_id; }
    root.appendChild(el);
    setTimeout(() => el.remove(), 6000);
    if (msg.level === "CRITICAL" || msg.level === "SECURITY") beep();
  }
  let audio;
  function beep() {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      const o = audio.createOscillator(), g = audio.createGain();
      o.type = "square"; o.frequency.value = 880; g.gain.value = 0.04;
      o.connect(g); g.connect(audio.destination); o.start(); o.stop(audio.currentTime + 0.18);
    } catch (e) { /* ovoz ruxsati yo'q */ }
  }
  function connect() {
    const proto = location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(proto + location.host + "/ws/live");
    ws.onopen = () => { retry = 1000; setStatus(true); };
    ws.onmessage = (e) => { try { const m = JSON.parse(e.data); liveTrigger(); toast(m); } catch (_) { liveTrigger(); } };
    ws.onclose = () => { setStatus(false); setTimeout(connect, retry); retry = Math.min(retry * 2, 15000); };
    ws.onerror = () => ws.close();
  }
  function setStatus(ok) {
    const el = document.querySelector(".sys-ok");
    if (!el) return;
    el.querySelector(".dot").className = "dot " + (ok ? "dot-green" : "dot-red");
    el.lastChild.textContent = ok ? (document.body.dataset.lang === "cyr" ? "Тизим фаол" : "Tizim faol") : (document.body.dataset.lang === "cyr" ? "Алоқа йўқ" : "Aloqa yo'q");
  }
  connect();
  setInterval(() => { if (ws && ws.readyState === 1) ws.send("ping"); }, 25000);

  // ---- xarita: zoom, pan, tooltip ----
  const mapStates = new Map();
  document.body.addEventListener("htmx:beforeSwap", (e) => {
    const target = e.detail.target || e.target;
    const active = document.activeElement;
    const wrap = active && active.closest(".map-wrap");
    if (!wrap || !wrap.id || !target.contains(active)) return;
    const state = mapStates.get(wrap.id);
    if (state && active.matches("a.uzmap-region")) state.restoreFocus = active.dataset.code;
  });
  function initMap(wrap) {
    const svg = wrap.querySelector("svg.uzmap");
    if (!svg || svg.dataset.init) return;
    svg.dataset.init = "1";
    const vb0 = svg.getAttribute("viewBox").trim().split(/[\s,]+/).map(Number);
    if (vb0.length !== 4 || !vb0.every(Number.isFinite) || vb0[2] <= 0 || vb0[3] <= 0) return;
    const saved = wrap.id && mapStates.get(wrap.id);
    let vb = saved && saved.base.every((n, i) => n === vb0[i]) ? saved.viewBox.slice() : vb0.slice();
    const clamp = (n, min, max) => Math.max(min, Math.min(n, max));
    const apply = () => {
      vb[0] = clamp(vb[0], vb0[0], vb0[0] + vb0[2] - vb[2]);
      vb[1] = clamp(vb[1], vb0[1], vb0[1] + vb0[3] - vb[3]);
      svg.setAttribute("viewBox", vb.join(" "));
      if (wrap.id) mapStates.set(wrap.id, { base: vb0.slice(), viewBox: vb.slice() });
    };
    const point = (x, y, matrix) => {
      const screen = matrix || svg.getScreenCTM();
      if (!screen) return null;
      const p = svg.createSVGPoint(); p.x = x; p.y = y;
      return p.matrixTransform(matrix ? matrix : screen.inverse());
    };
    const zoom = (f, cx, cy) => {
      const scale = clamp(vb0[2] / vb[2] * f, 1, 8);
      const w = vb0[2] / scale, h = vb0[3] / scale;
      const px = cx === undefined ? vb[0] + vb[2] / 2 : cx;
      const py = cy === undefined ? vb[1] + vb[3] / 2 : cy;
      vb = [px - (px - vb[0]) * w / vb[2], py - (py - vb[1]) * h / vb[3], w, h];
      apply();
    };
    apply();
    let drag = null, suppressClickUntil = 0;
    const tip = wrap.querySelector(".map-tip");
    const hideTip = () => { if (tip) tip.hidden = true; };
    const finishDrag = (e) => {
      if (!drag || (e && e.pointerId !== drag.id)) return;
      const previous = drag; drag = null;
      if (previous.moved) suppressClickUntil = performance.now() + 500;
      svg.classList.remove("is-panning");
      if (svg.hasPointerCapture(previous.id)) svg.releasePointerCapture(previous.id);
    };
    wrap.querySelectorAll(".map-zoom button").forEach((b) => b.addEventListener("click", () => {
      finishDrag(); hideTip();
      const z = b.dataset.zoom;
      if (z === "in") zoom(1.3); else if (z === "out") zoom(1 / 1.3); else { vb = vb0.slice(); apply(); }
    }));
    svg.addEventListener("pointerdown", (e) => {
      if (drag || !e.isPrimary || e.button !== 0) return;
      const matrix = svg.getScreenCTM();
      if (!matrix) return;
      // Keep the native anchor target until the gesture is clearly a drag.
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, inverse: matrix.inverse(), vb: vb.slice(), moved: false };
      suppressClickUntil = 0;
    });
    svg.addEventListener("pointermove", (e) => {
      if (!drag || e.pointerId !== drag.id) return;
      if (!drag.moved) {
        if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) <= 4) return;
        drag.moved = true;
        svg.setPointerCapture(e.pointerId);
        svg.classList.add("is-panning");
      }
      e.preventDefault(); hideTip();
      const start = point(drag.x, drag.y, drag.inverse), current = point(e.clientX, e.clientY, drag.inverse);
      vb = [drag.vb[0] - (current.x - start.x), drag.vb[1] - (current.y - start.y), drag.vb[2], drag.vb[3]];
      apply();
    });
    svg.addEventListener("pointerup", finishDrag);
    svg.addEventListener("pointercancel", finishDrag);
    svg.addEventListener("lostpointercapture", finishDrag);
    svg.addEventListener("pointerleave", (e) => { if (drag && !drag.moved) finishDrag(e); });
    svg.addEventListener("click", (e) => {
      // Keyboard activation has detail=0 and must never be swallowed by a previous drag.
      if (e.detail > 0 && performance.now() < suppressClickUntil) { e.preventDefault(); e.stopPropagation(); }
    }, true);
    svg.addEventListener("wheel", (e) => {
      if (!e.deltaY) return;
      e.preventDefault(); finishDrag(); hideTip();
      const p = point(e.clientX, e.clientY);
      if (p) zoom(e.deltaY < 0 ? 1.2 : 1 / 1.2, p.x, p.y);
    }, { passive: false });

    const positionTip = (clientX, clientY) => {
      if (!tip || tip.hidden) return;
      const r = wrap.getBoundingClientRect(), margin = 8, gap = 14;
      tip.style.maxWidth = Math.max(0, wrap.clientWidth - margin * 2) + "px";
      tip.style.minWidth = Math.min(200, Math.max(0, wrap.clientWidth - margin * 2)) + "px";
      const x = clientX - r.left - wrap.clientLeft, y = clientY - r.top - wrap.clientTop;
      let left = x + gap, top = y + gap;
      if (left + tip.offsetWidth > wrap.clientWidth - margin) left = x - tip.offsetWidth - gap;
      if (top + tip.offsetHeight > wrap.clientHeight - margin) top = y - tip.offsetHeight - gap;
      tip.style.left = clamp(left, margin, Math.max(margin, wrap.clientWidth - tip.offsetWidth - margin)) + "px";
      tip.style.top = clamp(top, margin, Math.max(margin, wrap.clientHeight - tip.offsetHeight - margin)) + "px";
    };
    const showTip = (a, txt, e) => {
      if (!tip || (drag && drag.moved)) return;
      const divider = txt.indexOf(":"), heading = document.createElement("b"), table = document.createElement("table");
      heading.textContent = divider < 0 ? txt : txt.slice(0, divider);
      const stats = divider < 0 ? [] : txt.slice(divider + 1).split(",").map((s) => s.trim()).filter(Boolean);
      stats.forEach((stat) => {
        const row = document.createElement("tr"), label = document.createElement("td"), value = document.createElement("td");
        const divider = stat.lastIndexOf(" ");
        label.textContent = divider < 0 ? stat : stat.slice(0, divider);
        value.textContent = divider < 0 ? "" : stat.slice(divider + 1);
        row.append(label, value); table.append(row);
      });
      tip.replaceChildren(heading, table);
      tip.setAttribute("role", "tooltip"); tip.hidden = false;
      const r = a.getBoundingClientRect();
      positionTip(e ? e.clientX : r.left + r.width / 2, e ? e.clientY : r.top + r.height / 2);
    };
    svg.querySelectorAll("a.uzmap-region").forEach((a) => {
      const title = a.querySelector("title");
      const txt = title ? title.textContent : a.dataset.name || "";
      a.addEventListener("pointerenter", (e) => showTip(a, txt, e));
      a.addEventListener("pointermove", (e) => { if (!drag || !drag.moved) positionTip(e.clientX, e.clientY); });
      a.addEventListener("pointerleave", hideTip);
      a.addEventListener("focus", () => showTip(a, txt));
      a.addEventListener("blur", hideTip);
      a.addEventListener("keydown", (e) => { if (e.key === "Escape") hideTip(); });
    });
    if (saved && saved.restoreFocus) {
      const focus = Array.from(svg.querySelectorAll("a.uzmap-region")).find((a) => a.dataset.code === saved.restoreFocus);
      if (focus) requestAnimationFrame(() => {
        if (svg.isConnected && (document.activeElement === document.body || !document.activeElement)) focus.focus({ preventScroll: true });
      });
    }
  }
  function initAll(root) {
    const mapRoot = root || document;
    if (mapRoot.matches && mapRoot.matches(".map-wrap")) initMap(mapRoot);
    mapRoot.querySelectorAll(".map-wrap").forEach(initMap);
    (root || document).querySelectorAll("tr.row-link").forEach((tr) => {
      if (tr.dataset.init) return; tr.dataset.init = "1";
      tr.addEventListener("click", (e) => { if (e.target.closest("a, button")) return; location.href = tr.dataset.href; });
    });
  }
  document.addEventListener("DOMContentLoaded", () => initAll());
  document.body.addEventListener("htmx:afterSwap", (e) => initAll(e.target));
})();
