/* ============================================================
   LabKit — shared helpers for the CBSE Virtual Labs
   Zero dependencies. Everything is original code.
   ============================================================ */
(function () {
  'use strict';

  // Collect page errors so the library index can show a health badge
  window.__lkErrors = [];
  window.addEventListener('error', function (e) {
    window.__lkErrors.push(String(e.message));
  });

  var C = {
    brand: '#4f46e5', m: '#0d9488', b: '#d97706', target: '#f43f5e',
    ok: '#16a34a', ink: '#0f172a', sub: '#64748b',
    grid: '#f1f5f9', grid2: '#e2e8f0', axis: '#94a3b8', white: '#ffffff'
  };

  var clamp = function (v, lo, hi) { return Math.min(hi, Math.max(lo, v)); };

  // -- canvas: HiDPI + auto-resize + rAF loop. Returns state {canvas, ctx, w, h, draw}
  function setupCanvas(canvas) {
    var st = { canvas: canvas, ctx: canvas.getContext('2d'), w: 0, h: 0, dpr: 1, draw: null };
    function resize() {
      var r = canvas.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      st.dpr = Math.min(window.devicePixelRatio || 1, 2);
      st.w = r.width; st.h = r.height;
      canvas.width = Math.round(r.width * st.dpr);
      canvas.height = Math.round(r.height * st.dpr);
      st.ctx.setTransform(st.dpr, 0, 0, st.dpr, 0, 0);
      if (st.draw) { st.draw(st); }
    }
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(resize).observe(canvas);
    window.addEventListener('resize', resize);
    resize();
    // first frame via timer so sims draw even in background tabs (rAF is paused there)
    setTimeout(function () { loop(); }, 60);
    function loop() {
      if (st.draw) st.draw(st);
      requestAnimationFrame(loop);
    }
    (window.__sashaCanvases = window.__sashaCanvases || []).push(st);
    return st;
  }

  // -- pretty number (real minus sign, trimmed decimals)
  function fmt(v, d) {
    if (d === undefined) d = 1;
    var r = Math.round(v * Math.pow(10, d)) / Math.pow(10, d);
    if (Object.is(r, -0)) r = 0;
    return String(r).replace('-', '\u2212');
  }
  // -- coefficient formatting (integers plain, halves with 1 decimal)
  function coef(v) {
    var neg = v < 0, a = Math.abs(v);
    var s = Number.isInteger(a) ? String(a) : a.toFixed(1);
    return (neg ? '\u2212' : '') + s;
  }

  // -- math grid with axes + tick labels. view:{scale,cx,cy}, o:{labelStep,unit}
  function grid(st, view, o) {
    o = o || {};
    var ctx = st.ctx, s = view.scale, cx = view.cx, cy = view.cy, w = st.w, h = st.h;
    var X = function (x) { return cx + x * s; }, Y = function (y) { return cy - y * s; };
    var xMin = (0 - cx) / s, xMax = (w - cx) / s, yMin = (cy - h) / s, yMax = cy / s;
    ctx.lineWidth = 1;
    var unit = o.unit || 1;
    var x, y;
    for (x = Math.ceil(xMin / unit) * unit; x <= xMax; x += unit) {
      ctx.strokeStyle = Math.round(x) % 5 === 0 ? C.grid2 : C.grid;
      ctx.beginPath(); ctx.moveTo(X(x), 0); ctx.lineTo(X(x), h); ctx.stroke();
    }
    for (y = Math.ceil(yMin / unit) * unit; y <= yMax; y += unit) {
      ctx.strokeStyle = Math.round(y) % 5 === 0 ? C.grid2 : C.grid;
      ctx.beginPath(); ctx.moveTo(0, Y(y)); ctx.lineTo(w, Y(y)); ctx.stroke();
    }
    ctx.strokeStyle = C.axis; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(X(0), 0); ctx.lineTo(X(0), h); ctx.stroke();
    if (o.noLabels) return { X: X, Y: Y };
    var step = o.labelStep || (s >= 26 ? 2 : s >= 13 ? 4 : 5);
    ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = C.axis;
    for (x = Math.ceil(xMin / step) * step; x <= xMax; x += step) {
      if (x === 0) continue;
      var tx = String(Math.round(x * 10) / 10);
      ctx.fillText(tx.replace('-', '\u2212'), X(x) - tx.length * 3.6, Y(0) + 15);
    }
    for (y = Math.ceil(yMin / step) * step; y <= yMax; y += step) {
      if (y === 0) continue;
      ctx.fillText(fmt(y, 1).replace('.0', ''), X(0) + 6, Y(y) + 4);
    }
    ctx.fillText('0', X(0) - 12, Y(0) + 15);
    return { X: X, Y: Y };
  }

  // -- wire a range slider; calls fn(value) immediately and on input
  function slider(id, fn) {
    var el = document.getElementById(id);
    var f = function () { fn(parseFloat(el.value)); };
    el.addEventListener('input', f);
    f();
    return el;
  }
  // -- wire segmented buttons; container holds buttons, fn(index, button)
  function segment(containerId, fn) {
    var box = document.getElementById(containerId);
    var btns = [].slice.call(box.querySelectorAll('button'));
    btns.forEach(function (btn, i) {
      btn.addEventListener('click', function () {
        btns.forEach(function (b2) { b2.classList.remove('active'); });
        btn.classList.add('active');
        fn(i, btn);
      });
    });
    return btns;
  }
  function check(id, fn) {
    var el = document.getElementById(id);
    var f = function () { fn(el.checked); };
    el.addEventListener('change', f);
    f();
    return el;
  }
  function button(id, fn) {
    var el = document.getElementById(id);
    el.addEventListener('click', fn);
    return el;
  }

  // -- pointer events on a canvas -> handlers {down,move,up,hover} get {x,y} css px + isDragging
  function pointer(canvas, h) {
    function pos(e) {
      var r = canvas.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    }
    var dragging = false;
    canvas.addEventListener('pointerdown', function (e) {
      dragging = true;
      try { canvas.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events */ }
      if (h.down) h.down(pos(e));
      e.preventDefault();
    });
    canvas.addEventListener('pointermove', function (e) {
      var p = pos(e);
      if (h.move) h.move(p, dragging);
      if (h.hover && !dragging) h.hover(p);
    });
    var end = function (e) { dragging = false; if (h.up) h.up(pos(e)); };
    canvas.addEventListener('pointerup', end);
    canvas.addEventListener('pointercancel', end);
    canvas.addEventListener('pointerleave', function () { if (h.out) h.out(); });
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }
  function chip(ctx, x, y, text, bg) {
    ctx.font = 'bold 12px system-ui, sans-serif';
    var w = ctx.measureText(text).width + 16;
    x = clamp(x - w / 2, 6, ctx.canvas.clientWidth - w - 6);
    y = clamp(y, 6, ctx.canvas.clientHeight - 26);
    ctx.fillStyle = bg; roundRect(ctx, x, y, w, 21, 7); ctx.fill();
    ctx.fillStyle = C.white; ctx.textAlign = 'center';
    ctx.fillText(text, x + w / 2, y + 15); ctx.textAlign = 'start';
  }
  function arrow(ctx, tipX, tipY, angle, color, size) {
    size = size || 9;
    ctx.save(); ctx.translate(tipX, tipY); ctx.rotate(angle);
    ctx.fillStyle = color || C.axis;
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(-size, -size / 2); ctx.lineTo(-size, size / 2);
    ctx.closePath(); ctx.fill(); ctx.restore();
  }
  // simple seeded-free RNG helper
  function rand(a, b) { return a + Math.random() * (b - a); }

  // hide "back to library" when embedded in an LMS iframe
  if (window.self !== window.top) {
    document.addEventListener('DOMContentLoaded', function () {
      var back = document.querySelector('.lk-back');
      if (back) back.classList.add('hidden');
    });
  }

  window.LK = {
    C: C, clamp: clamp, setupCanvas: setupCanvas, fmt: fmt, coef: coef,
    grid: grid, slider: slider, segment: segment, check: check, button: button,
    pointer: pointer, roundRect: roundRect, chip: chip, arrow: arrow, rand: rand
  };
})();
