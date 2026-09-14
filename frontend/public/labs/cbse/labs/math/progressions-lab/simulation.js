'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { a: 2, d: 3, n: 8 };

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var padL = 56, padB = 50, padT = 60;
  var gy = h - padB;
  var terms = [];
  for (var i = 0; i < s.n; i++) terms.push(s.a + i * s.d);
  var maxAbs = Math.max(4, Math.abs(s.a), Math.abs(terms[terms.length - 1])) * 1.15;
  var Y = function (v) { return gy - (v / maxAbs) * (gy - padT) * 0.9 * (v >= 0 ? 1 : -1) * (v >= 0 ? 1 : 1); };
  // baseline
  ctx.strokeStyle = '#98a2b3'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(padL - 20, gy); ctx.lineTo(w - 20, gy); ctx.stroke();
  var bw = Math.min(58, (w - padL - 40) / s.n * 0.6);
  terms.forEach(function (t, i) {
    var x = padL + (i + 0.5) * (w - padL - 40) / s.n;
    var bh = (t / maxAbs) * (gy - padT) * 0.9;
    var grad = ctx.createLinearGradient(0, gy - Math.abs(bh), 0, gy);
    if (t >= 0) { grad.addColorStop(0, '#f97316'); grad.addColorStop(1, '#fed7aa'); }
    else { grad.addColorStop(0, '#fecaca'); grad.addColorStop(1, '#dc2626'); }
    ctx.fillStyle = grad;
    ctx.fillRect(x - bw / 2, gy - Math.max(0, bh), bw, Math.abs(bh));
    ctx.strokeStyle = '#e4e7ec'; ctx.strokeRect(x - bw / 2, gy - Math.max(0, bh), bw, Math.abs(bh));
    ctx.fillStyle = '#0f1b33'; ctx.font = '600 12px Inter, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(String(t), x, (bh >= 0 ? gy - Math.max(0, bh) - 8 : gy + 16));
    ctx.fillStyle = '#6b7891'; ctx.font = '11px Inter, sans-serif';
    ctx.fillText('a' + (i + 1), x, gy + 30);
    ctx.textAlign = 'start';
  });
  // sum staircase
  ctx.strokeStyle = '#0369a1'; ctx.lineWidth = 2; ctx.setLineDash([5, 4]);
  ctx.beginPath();
  terms.forEach(function (t, i) {
    var x = padL + (i + 0.5) * (w - padL - 40) / s.n;
    var yv = gy - (t / maxAbs) * (gy - padT) * 0.9;
    i === 0 ? ctx.moveTo(x, gy) : 0;
    ctx.lineTo(x, yv);
    if (i === terms.length - 1) ctx.lineTo(x, gy);
  });
  ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = '#0369a1'; ctx.font = '600 12px Inter, sans-serif';
  ctx.fillText('— term bars · - - sum staircase', padL, 34);
}

function upd() {
  var nth = s.a + (s.n - 1) * s.d;
  var sum = s.n * (2 * s.a + (s.n - 1) * s.d) / 2;
  var seq = [];
  for (var i = 0; i < s.n; i++) seq.push(s.a + i * s.d);
  document.getElementById('nth').innerHTML = 'aₙ = a + (n−1)d = ' + s.a + ' + ' + (s.n - 1) + '×' + s.d + ' = <b>' + nth + '</b>';
  document.getElementById('sum').innerHTML = 'Sₙ = n/2 [2a + (n−1)d] = <b>' + sum + '</b>';
  document.getElementById('seqRead').innerHTML = 'Sequence: <b>' + seq.join(', ') + '</b>' +
    (s.d > 0 ? ' (growing)' : s.d < 0 ? ' (shrinking — watch the bars dip below zero!)' : ' (constant)');
  draw();
}

LK.slider('a0', function (v) { s.a = v; document.getElementById('a0v').textContent = v; upd(); });
LK.slider('d0', function (v) { s.d = v; document.getElementById('d0v').textContent = v; upd(); });
LK.slider('n0', function (v) { s.n = v; document.getElementById('n0v').textContent = v; upd(); });
st.draw = draw; upd();
