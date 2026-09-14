'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { op: 'A∪B' };
var U = [];
for (var i = 1; i <= 20; i++) U.push(i);
function inA(v) { return v % 3 === 0; }        // multiples of 3
function inB(v) { return v % 4 === 0; }        // multiples of 4
var A = U.filter(inA), B = U.filter(inB);

function regionOf(v) {
  var a = inA(v), b = inB(v);
  return a && b ? 'AB' : a ? 'A' : b ? 'B' : 'U';
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var rx = 60, ry = 40, rw = w - 120, rh = h - 100;
  ctx.strokeStyle = '#98a2b3'; ctx.lineWidth = 2;
  ctx.strokeRect(rx, ry, rw, rh);
  ctx.font = '600 13px Inter, sans-serif'; ctx.fillStyle = '#6b7891';
  ctx.fillText('U = {1…20}', rx + 10, ry + 20);

  var r = Math.min(rh * 0.62, 170);
  var cxA = rx + rw * 0.38, cxB = rx + rw * 0.62, cy = ry + rh * 0.55;
  function lit(v) {
    var reg = regionOf(v);
    switch (s.op) {
      case 'A': return reg === 'A' || reg === 'AB';
      case 'B': return reg === 'B' || reg === 'AB';
      case 'A∪B': return reg !== 'U';
      case 'A∩B': return reg === 'AB';
      case 'A−B': return reg === 'A';
      case 'A′': return reg !== 'A' && reg !== 'AB';
    }
    return false;
  }
  // circles with tint fill
  function circle(cx, tint) {
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = tint; ctx.fill();
    ctx.strokeStyle = '#f97316'; ctx.lineWidth = 3; ctx.stroke();
  }
  circle(cxA, 'rgba(249,115,22,.06)');
  circle(cxB, 'rgba(3,105,161,.06)');
  // numbers placed in regions
  var slots = { A: [], B: [], AB: [], U: [] };
  U.forEach(v => slots[regionOf(v)].push(v));
  function place(list, x0, dx, y) {
    list.forEach((v, i) => {
      var hl = lit(v);
      ctx.beginPath();
      ctx.arc(x0 + i * dx, y, 12, 0, Math.PI * 2);
      ctx.fillStyle = hl ? (s.op.includes('′') || s.op === 'A−B' ? '#dc2626' : '#f97316') : '#f1f3f6';
      ctx.fill();
      ctx.strokeStyle = hl ? '#ea580c' : '#e4e7ec'; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.fillStyle = hl ? '#fff' : '#6b7891';
      ctx.font = '600 11px Inter, sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(v, x0 + i * dx, y + 4);
      ctx.textAlign = 'start';
    });
  }
  var rowY = cy - 40;
  place(slots.AB, cxA + 24, 26, rowY - 30);
  place(slots.A, cxA - 70, 26, rowY);
  place(slots.B, cxB + 20, 26, rowY);
  // outside numbers in corners
  var ox = rx + 18, oy = ry + rh - 22;
  slots.U.forEach((v, i) => {
    var xx = ox + (i % 10) * 26, yy = oy - Math.floor(i / 10) * 26;
    var hl = lit(v);
    ctx.beginPath(); ctx.arc(xx, yy, 11, 0, Math.PI * 2);
    ctx.fillStyle = hl ? '#dc2626' : '#f1f3f6';
    ctx.fill();
    ctx.strokeStyle = hl ? '#b91c1c' : '#e4e7ec'; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.fillStyle = hl ? '#fff' : '#6b7891';
    ctx.font = '600 10.5px Inter, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(v, xx, yy + 4); ctx.textAlign = 'start';
  });
  ctx.fillStyle = '#b45309'; ctx.font = '600 13px Inter, sans-serif';
  ctx.fillText('A = multiples of 3', cxA - 60, ry + 14);
  ctx.fillStyle = '#0369a1';
  ctx.fillText('B = multiples of 4', cxB - 30, ry + 14);

  var union = A.length + B.length - slots.AB.length;
  document.getElementById('counts').innerHTML =
    'n(A) = <b>' + A.length + '</b> · n(B) = <b>' + B.length + '</b> · n(A∩B) = <b>' + slots.AB.length + '</b> · n(U) = <b>20</b>';
  document.getElementById('formula').innerHTML =
    'n(A∪B) = ' + A.length + ' + ' + B.length + ' − ' + slots.AB.length + ' = <b>' + union + '</b> ✓ (highlighted now: ' + U.filter(lit).length + ')';
}

document.querySelectorAll('#opSeg button').forEach(function (b) {
  b.addEventListener('click', function () {
    document.querySelectorAll('#opSeg button').forEach(function (b2) { b2.classList.remove('active'); });
    b.classList.add('active');
    s.op = b.getAttribute('data-op');
    draw();
  });
});
st.draw = draw; draw();
