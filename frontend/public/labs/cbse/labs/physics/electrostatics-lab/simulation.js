'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { q1: 2, q2: -2, c1: null, c2: null, drag: null };

function pos() {
  return {
    c1: s.c1 || { x: st.w * 0.34, y: st.h * 0.5 },
    c2: s.c2 || { x: st.w * 0.66, y: st.h * 0.5 }
  };
}

function fieldAt(x, y) {
  var p = pos();
  var fx = 0, fy = 0;
  [[p.c1, s.q1], [p.c2, s.q2]].forEach(function (c) {
    var dx = x - c[0].x, dy = y - c[0].y;
    var d2 = dx * dx + dy * dy + 120;
    var mag = c[1] * 9.2e5 / (d2 * Math.sqrt(d2));
    fx += dx * mag; fy += dy * mag;
  });
  return { x: fx, y: fy, len: Math.hypot(fx, fy) };
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var p = pos();

  /* field lines from positive charges */
  [[p.c1, s.q1], [p.c2, s.q2]].forEach(function (src) {
    if (src[1] <= 0) return;
    var nLines = src[1] * 6;
    for (var l = 0; l < nLines; l++) {
      var a0 = l / nLines * Math.PI * 2;
      var x = src[0].x + Math.cos(a0) * 22, y = src[0].y + Math.sin(a0) * 22;
      ctx.strokeStyle = 'rgba(249,115,22,.42)';
      ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(x, y);
      for (var step = 0; step < 320; step++) {
        var f = fieldAt(x, y);
        if (f.len < 1) break;
        x += f.x / f.len * 5; y += f.y / f.len * 5;
        ctx.lineTo(x, y);
        if (x < -20 || x > w + 20 || y < -20 || y > h + 20) break;
        var hit = [[p.c1, s.q1], [p.c2, s.q2]].some(function (t) {
          return t[1] < 0 && Math.hypot(x - t[0].x, y - t[0].y) < 22;
        });
        if (hit) break;
      }
      ctx.stroke();
    }
  });
  if (s.q1 <= 0 && s.q2 <= 0) {
    ctx.fillStyle = '#6b7891'; ctx.font = '600 13px Inter, sans-serif';
    ctx.fillText('Both charges negative — field lines all point IN (switch one to + to trace lines)', 40, 40);
  }

  /* neutral point marker */
  for (var nx = 40; nx < w - 40; nx += 18) {
    for (var ny = 40; ny < h - 40; ny += 18) {
      var f2 = fieldAt(nx, ny);
      if (f2.len < 0.06 && s.q1 * s.q2 > 0) {
        ctx.strokeStyle = '#0369a1'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(nx, ny, 10, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = '#0369a1'; ctx.font = '600 11px Inter, sans-serif';
        ctx.fillText('neutral', nx + 14, ny + 4);
      }
    }
  }

  /* charges */
  function charge(c, q) {
    var r = 16 + Math.abs(q) * 2.5;
    ctx.fillStyle = q > 0 ? '#dc2626' : '#2563eb';
    ctx.beginPath(); ctx.arc(c.x, c.y, r, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 2.5; ctx.stroke();
    ctx.fillStyle = '#fff'; ctx.font = 'bold 17px Inter, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText((q > 0 ? '+' : '−') + Math.abs(q), c.x, c.y + 6);
    ctx.textAlign = 'start';
  }
  charge(p.c1, s.q1);
  charge(p.c2, s.q2);

  /* force arrows (Coulomb) */
  var dx = p.c2.x - p.c1.x, dy = p.c2.y - p.c1.y;
  var r2 = (dx * dx + dy * dy) / 10000;         // in "cm²"
  var F = Math.abs(s.q1 * s.q2) / Math.max(r2, 0.01);
  var attract = s.q1 * s.q2 < 0;
  var ux = dx / Math.hypot(dx, dy), uy = dy / Math.hypot(dx, dy);
  var flen = LK.clamp(F * 4, 20, 110);
  ctx.strokeStyle = attract ? '#059669' : '#b45309'; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(p.c1.x, p.c1.y); ctx.lineTo(p.c1.x + (attract ? ux : -ux) * flen, p.c1.y + (attract ? uy : -uy) * flen); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(p.c2.x, p.c2.y); ctx.lineTo(p.c2.x + (attract ? -ux : ux) * flen, p.c2.y + (attract ? -uy : uy) * flen); ctx.stroke();

  document.getElementById('coulomb').innerHTML =
    'F = k·|q₁q₂|/r² = 9×10⁹ × ' + Math.abs(s.q1 * s.q2) + ' / ' + (r2 / 100).toFixed(2) + '² ≈ <b>' + (F / 1000).toFixed(1) + '×10³ N</b>';
  document.getElementById('mode').innerHTML = s.q1 * s.q2 < 0
    ? 'Unlike charges: <b style="color:#059669;">ATTRACT</b> — dipole pattern (lines flow + → −)'
    : s.q1 * s.q2 > 0 ? 'Like charges: <b style="color:#b45309;">REPEL</b> — lines bend away; neutral point between'
    : 'One charge neutral — single-charge radial field';
}

LK.slider('q1', function (v) { s.q1 = v; document.getElementById('q1v').textContent = (v > 0 ? '+' : '') + v; draw(); });
LK.slider('q2', function (v) { s.q2 = v; document.getElementById('q2v').textContent = (v > 0 ? '+' : '') + v; draw(); });
LK.button('flipBtn', function () { s.c1 = null; s.c2 = null; });
LK.pointer(st.canvas, {
  down: function (pt) {
    var p = pos();
    if (Math.hypot(pt.x - p.c1.x, pt.y - p.c1.y) < 30) s.drag = 1;
    else if (Math.hypot(pt.x - p.c2.x, pt.y - p.c2.y) < 30) s.drag = 2;
  },
  move: function (pt, d) {
    if (!d || !s.drag) return;
    var p = pos();
    var c = s.drag === 1 ? p.c1 : p.c2;
    c.x = LK.clamp(pt.x, 40, st.w - 40);
    c.y = LK.clamp(pt.y, 40, st.h - 40);
    if (s.drag === 1) s.c1 = c; else s.c2 = c;
    draw();
  },
  up: function () { s.drag = null; }
});
st.draw = draw; draw();
