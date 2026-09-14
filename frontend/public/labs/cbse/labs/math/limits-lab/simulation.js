'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { fn: 0, x0: 1, h: 0.9 };
var FNS = [
  { f: x => x * x, d: x => 2 * x, label: 'f(x) = x²', dLabel: "f'(x) = 2x" },
  { f: x => x * x * x - x, d: x => 3 * x * x - 1, label: 'f(x) = x³ − x', dLabel: "f'(x) = 3x² − 1" },
  { f: x => Math.sin(x), d: x => Math.cos(x), label: 'f(x) = sin x', dLabel: "f'(x) = cos x" }
];

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var FN = FNS[s.fn];
  var scale = Math.min(w / 7, h / 6);
  var cx = w / 2, cy = h / 2;
  var X = x => cx + x * scale, Y = y => cy - y * scale;

  // axes
  ctx.strokeStyle = '#98a2b3'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(X(0), 0); ctx.lineTo(X(0), h); ctx.stroke();

  // curve
  ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 3;
  ctx.beginPath();
  var first = true;
  for (var px = 0; px <= w; px += 2) {
    var x = (px - cx) / scale;
    var y = FN.f(x);
    var py = Y(y);
    if (py < -300 || py > h + 300) { first = true; continue; }
    first ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    first = false;
  }
  ctx.stroke();

  var x0 = s.x0, x1 = s.x0 + s.h;
  var y0 = FN.f(x0), y1 = FN.f(x1);
  var secSlope = (y1 - y0) / s.h;
  var tanSlope = FN.d(x0);

  // secant line (blue, long)
  function line(slope, through, color, width, dash) {
    ctx.strokeStyle = color; ctx.lineWidth = width;
    if (dash) ctx.setLineDash(dash);
    ctx.beginPath();
    ctx.moveTo(0, Y(through.y - slope * (through.x + cx / scale)));
    ctx.lineTo(w, Y(through.y + slope * ((w - cx) / scale - through.x)));
    ctx.stroke(); ctx.setLineDash([]);
  }
  // simpler: draw via two far points
  function line2(slope, pt, color, width, dash) {
    ctx.strokeStyle = color; ctx.lineWidth = width;
    if (dash) ctx.setLineDash(dash);
    ctx.beginPath();
    var xa = -cx / scale, xb = (w - cx) / scale;
    ctx.moveTo(X(xa), Y(pt.y + slope * (xa - pt.x)));
    ctx.lineTo(X(xb), Y(pt.y + slope * (xb - pt.x)));
    ctx.stroke(); ctx.setLineDash([]);
  }
  if (s.h > 0.0005) line2(secSlope, { x: x0, y: y0 }, '#0369a1', 2.5, [7, 5]);
  line2(tanSlope, { x: x0, y: y0 }, '#dc2626', 3);

  // points
  function dot(x, y, color, r) {
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.arc(X(x), Y(y), r + 2.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(X(x), Y(y), r, 0, Math.PI * 2); ctx.fill();
  }
  dot(x0, y0, '#dc2626', 6);
  if (s.h > 0.0005) dot(x1, y1, '#0369a1', 6);
  // h bracket
  if (s.h > 0.08) {
    ctx.strokeStyle = '#b45309'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(X(x0), Y(0) + 26); ctx.lineTo(X(x1), Y(0) + 26); ctx.stroke();
    ctx.fillStyle = '#b45309'; ctx.font = '600 12px Inter, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('h', (X(x0) + X(x1)) / 2, Y(0) + 44);
    ctx.textAlign = 'start';
  }
  ctx.fillStyle = '#0f1b33'; ctx.font = '600 13px Inter, sans-serif';
  ctx.fillText(FN.label + '   ·   ' + FN.dLabel, 16, 26);

  document.getElementById('secant').innerHTML =
    'Secant slope = [f(x₀+h) − f(x₀)]/h = <b>' + secSlope.toFixed(4) + '</b>';
  document.getElementById('tangent').innerHTML =
    "True derivative f'(x₀) = <b>" + tanSlope.toFixed(4) + '</b>';
  var agree = Math.abs(secSlope - tanSlope) < 0.05;
  document.getElementById('limit').innerHTML = s.h <= 0.0005
    ? 'h → 0: the secant <b>becomes</b> the tangent 🎯'
    : (agree ? 'Already close — shrink h further! (Δ = ' + Math.abs(secSlope - tanSlope).toFixed(3) + ')'
             : 'Δ = ' + Math.abs(secSlope - tanSlope).toFixed(3) + ' — keep shrinking h');
}

LK.segment('fnSeg', function (i) { s.fn = i; draw(); });
LK.slider('x0', function (v) { s.x0 = v; document.getElementById('x0v').textContent = v.toFixed(1); draw(); });
LK.slider('hh', function (v) { s.h = v; document.getElementById('hhv').textContent = v.toFixed(2); draw(); });
st.draw = draw; draw();
