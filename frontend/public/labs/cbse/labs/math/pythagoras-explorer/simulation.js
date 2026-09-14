'use strict';
var s = { a: 4, b: 3 };
var st = LK.setupCanvas(document.getElementById('cv'));
var view = { scale: 30, ox: 0, oy: 0 };

function X(x) { return view.ox + x * view.scale; }
function Y(y) { return view.oy - y * view.scale; }

function layout() {
  var p = 46;
  var target = Math.min((st.w - 2 * p) / (s.a + 2 * s.b), (st.h - 2 * p) / (2 * s.a + s.b));
  view.scale = view.scale ? view.scale + (target - view.scale) * 0.18 : target;
  view.ox = p + s.b * view.scale;
  view.oy = st.h - p - s.a * view.scale;
}

function unitSquare(ctx, p1, p2, dir, color, title) {
  // square on segment p1->p2 extending along vector dir (already unit-scaled)
  var P = [p1, p2, { x: p2.x + dir.x, y: p2.y + dir.y }, { x: p1.x + dir.x, y: p1.y + dir.y }];
  ctx.beginPath();
  P.forEach(function (pt, i) { i ? ctx.lineTo(X(pt.x), Y(pt.y)) : ctx.moveTo(X(pt.x), Y(pt.y)); });
  ctx.closePath();
  ctx.fillStyle = color; ctx.globalAlpha = 0.14; ctx.fill(); ctx.globalAlpha = 1;
  ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
  // tile grid: n divisions along each side
  var len = Math.hypot(p2.x - p1.x, p2.y - p1.y);
  var n = Math.max(1, Math.round(len));
  var ux = { x: (p2.x - p1.x) / n, y: (p2.y - p1.y) / n }, vx = { x: dir.x / n, y: dir.y / n };
  ctx.lineWidth = 1; ctx.strokeStyle = color; ctx.globalAlpha = 0.45;
  for (var i = 1; i < n; i++) {
    ctx.beginPath();
    ctx.moveTo(X(p1.x + ux.x * i), Y(p1.y + ux.y * i));
    ctx.lineTo(X(p1.x + ux.x * i + dir.x), Y(p1.y + ux.y * i + dir.y));
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(X(p1.x + vx.x * i), Y(p1.y + vx.y * i));
    ctx.lineTo(X(p1.x + vx.x * i + (p2.x - p1.x)), Y(p1.y + vx.y * i + (p2.y - p1.y)));
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
  // label
  var cxm = (P[0].x + P[1].x + P[2].x + P[3].x) / 4;
  var cym = (P[0].y + P[1].y + P[2].y + P[3].y) / 4;
  ctx.fillStyle = color; ctx.font = 'bold 15px system-ui, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(title, X(cxm), Y(cym) + 5);
  ctx.textAlign = 'start';
}

function draw() {
  layout();
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var a = s.a, b = s.b, c = Math.hypot(a, b);
  var Cc = { x: 0, y: 0 }, A = { x: a, y: 0 }, B = { x: 0, y: b };

  unitSquare(ctx, Cc, A, { x: 0, y: -a }, LK.C.brand, 'a\u00B2 = ' + (a * a));
  unitSquare(ctx, Cc, B, { x: -b, y: 0 }, LK.C.m, 'b\u00B2 = ' + (b * b));
  unitSquare(ctx, A, B, { x: b, y: a }, LK.C.b, 'c\u00B2 = ' + (a * a + b * b));

  // triangle
  ctx.beginPath();
  ctx.moveTo(X(Cc.x), Y(Cc.y)); ctx.lineTo(X(A.x), Y(A.y)); ctx.lineTo(X(B.x), Y(B.y));
  ctx.closePath();
  ctx.fillStyle = '#fff'; ctx.fill();
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 3; ctx.stroke();
  // right-angle marker
  var m = 0.35 * view.scale;
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 1.5;
  ctx.strokeRect(X(0), Y(0) - m, m, m);

  // vertex labels + drag handles
  handle(X(a), Y(0), 'a', LK.C.m);
  handle(X(0), Y(b), 'b', LK.C.b);
}

function handle(px, py, letter, color) {
  var ctx = st.ctx;
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(px, py, 11, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#fff'; ctx.font = 'italic bold 13px Georgia, serif'; ctx.textAlign = 'center';
  ctx.fillText(letter, px, py + 4.5); ctx.textAlign = 'start';
}

function upd() {
  var a2 = s.a * s.a, b2 = s.b * s.b, c2 = a2 + b2;
  document.getElementById('sums').innerHTML =
    'a = ' + LK.fmt(s.a, 1) + ', &nbsp; b = ' + LK.fmt(s.b, 1) + ', &nbsp; c = ' + LK.fmt(Math.sqrt(c2), 3) + '<br>' +
    '<b>' + LK.fmt(a2, 1) + ' + ' + LK.fmt(b2, 1) + ' = ' + LK.fmt(c2, 1) + '</b> \u2713';
}

LK.slider('sa', function (v) { s.a = v; document.getElementById('sav').textContent = LK.fmt(v, 1); upd(); });
LK.slider('sb', function (v) { s.b = v; document.getElementById('sbv').textContent = LK.fmt(v, 1); upd(); });

LK.pointer(st.canvas, {
  down: function (p) {
    if (Math.hypot(p.x - X(s.a), p.y - Y(0)) < 22) drag = 'a';
    else if (Math.hypot(p.x - X(0), p.y - Y(s.b)) < 22) drag = 'b';
    else drag = null;
  },
  move: function (p, d) {
    if (!d || !drag) return;
    if (drag === 'a') s.a = LK.clamp(Math.round(my2(p) * 2) / 2, 1, 9);
    else s.b = LK.clamp(Math.round(mx2(p) * 2) / 2, 1, 9);
    syncSliders(); upd();
  }
});
var drag = null;
function my2(p) { return (p.x - view.ox) / view.scale; }
function mx2(p) { return (view.oy - p.y) / view.scale; }
function syncSliders() {
  document.getElementById('sa').value = s.a;
  document.getElementById('sb').value = s.b;
  document.getElementById('sav').textContent = LK.fmt(s.a, 1);
  document.getElementById('sbv').textContent = LK.fmt(s.b, 1);
}

st.draw = draw; upd();
