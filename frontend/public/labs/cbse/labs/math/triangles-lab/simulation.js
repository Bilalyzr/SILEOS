'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { k: 1, rot: 20, shape: 0, drag: null };
var A = { x: -5, y: -2, y2: 3 };   // triangle A vertices in world units

function view() {
  return { scale: Math.min(st.w, st.h) / 16, cx: st.w / 2, cy: st.h / 2 };
}
function P(px, py) { var v = view(); return { x: v.cx + px * v.scale, y: v.cy - py * v.scale }; }

function triA() {
  var v = view();
  if (s.shape === 1) return [{ x: -4, y: -3 }, { x: 0, y: 4 }, { x: 4, y: -3 }];
  if (s.shape === 2) return [{ x: -4, y: -3 }, { x: 4, y: -3 }, { x: 4, y: 3 }];
  return [P2W(A.x, A.y), P2W(6, A.y), P2W(A.x + (6 - A.x) * 0.4, A.y2)];
}
function P2W(x, y) { return { x: x, y: y }; }
function W2P(p) { var v = view(); return { x: (p.x - v.cx) / v.scale, y: (v.cy - p.y) / v.scale }; }

function triB() {
  var a = triA(), out = [];
  var rad = s.rot * Math.PI / 180;
  a.forEach(function (pt) {
    out.push({
      x: (pt.x * Math.cos(rad) - pt.y * Math.sin(rad)) * s.k,
      y: (pt.x * Math.sin(rad) + pt.y * Math.cos(rad)) * s.k
    });
  });
  return out;
}

function dist(p, q) { return Math.hypot(p.x - q.x, p.y - q.y); }
function angle(p, q, r) {
  var v1 = { x: p.x - q.x, y: p.y - q.y }, v2 = { x: r.x - q.x, y: r.y - q.y };
  var dot = v1.x * v2.x + v1.y * v2.y;
  var m = Math.hypot(v1.x, v1.y) * Math.hypot(v2.x, v2.y);
  return Math.acos(LK.clamp(dot / m, -1, 1)) * 180 / Math.PI;
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var a = triA(), b = triB();
  function drawTri(pts, fill, stroke, label) {
    ctx.beginPath();
    var scr = pts.map(P);
    scr.forEach(function (p2, i) { i ? ctx.lineTo(p2.x, p2.y) : ctx.moveTo(p2.x, p2.y); });
    ctx.closePath();
    ctx.fillStyle = fill; ctx.fill();
    ctx.strokeStyle = stroke; ctx.lineWidth = 3.5; ctx.stroke();
    ctx.fillStyle = '#6b7891'; ctx.font = '600 13px Inter, sans-serif';
    var c2 = scr.reduce(function (acc, p2) { return { x: acc.x + p2.x / 3, y: acc.y + p2.y / 3 }; }, { x: 0, y: 0 });
    ctx.fillText(label, c2.x - 14, c2.y);
  }
  drawTri(b, 'rgba(3,105,161,.10)', '#0369a1', 'B');
  drawTri(a, 'rgba(249,115,22,.12)', '#f97316', 'A');

  if (s.shape === 0) {
    a.forEach(function (pt, i) {
      var p2 = P(pt);
      ctx.fillStyle = '#f97316';
      ctx.beginPath(); ctx.arc(p2.x, p2.y, 9, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.5; ctx.stroke();
    });
  }
}

function upd() {
  var a = triA(), b = triB();
  var sa = [dist(a[0], a[1]), dist(a[1], a[2]), dist(a[2], a[0])];
  var sb = [dist(b[0], b[1]), dist(b[1], b[2]), dist(b[2], b[0])];
  var aa = [angle(a[1], a[0], a[2]), angle(a[0], a[1], a[2]), angle(a[1], a[2], a[0])];
  var ab = [angle(b[1], b[0], b[2]), angle(b[0], b[1], b[2]), angle(b[1], b[2], b[0])];
  var f = i => (sa[i] / sb[i]).toFixed(2);
  document.getElementById('sides').innerHTML =
    'A: ' + sa.map(v => v.toFixed(1)).join(', ') + ' · B: ' + sb.map(v => v.toFixed(1)).join(', ') +
    '<br>Side ratio A/B: <b>' + f(0) + ' : ' + f(1) + ' : ' + f(2) + '</b>';
  var angEq = aa.every((v, i) => Math.abs(v - ab[i]) < 1.5);
  document.getElementById('angles').innerHTML =
    'Angles A: ' + aa.map(v => v.toFixed(0) + '°').join(', ') + ' · B: ' + ab.map(v => v.toFixed(0) + '°').join(', ') +
    (angEq ? ' — equal ✓' : '');
  var congruent = Math.abs(s.k - 1) < 0.001;
  document.getElementById('verdict').innerHTML = angEqual(angEq)
    ? (congruent ? '🟠 <b>CONGRUENT</b> — identical shape AND size (k=1): SSS holds.'
                 : '🔵 <b>SIMILAR</b> — same shape, scaled ' + s.k.toFixed(1) + '× (angles equal, sides proportional).')
    : 'Angles differ? Try smaller rotations — B always copies A exactly.';
  function angEqual(eq) { return eq; }
  draw();
}

LK.slider('k', function (v) { s.k = v; document.getElementById('kv').textContent = v.toFixed(1) + '×'; upd(); });
LK.slider('rot', function (v) { s.rot = v; document.getElementById('rotv').textContent = v + '°'; upd(); });
LK.segment('modeSeg', function (i) { s.shape = i; upd(); });
LK.pointer(st.canvas, {
  down: function (p) {
    if (s.shape !== 0) return;
    triA().forEach((pt, i) => {
      var sp = P(pt);
      if (Math.hypot(p.x - sp.x, p.y - sp.y) < 20) s.drag = i;
    });
  },
  move: function (p, d) {
    if (!d || s.drag === null || s.shape !== 0) return;
    var wpt = W2P(p);
    if (s.drag === 0) { A.x = wpt.x; A.y = wpt.y; }
    else if (s.drag === 1) { A.y = wpt.y; }
    else { A.y2 = wpt.y; }
    A.x = LK.clamp(A.x, -7, 2); A.y = LK.clamp(A.y, -5, 2); A.y2 = LK.clamp(A.y2, 0, 5.5);
    upd();
  },
  up: function () { s.drag = null; }
});
st.draw = draw; upd();
