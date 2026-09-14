'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { a: 36, b: 48 };

function factorTree(n) {
  // returns tree {v, left, right}
  if (n <= 2) return { v: n };
  for (var d = 2; d * d <= n; d++) {
    if (n % d === 0) return { v: n, l: factorTree(d), r: factorTree(n / d) };
  }
  return { v: n };
}
function primesOf(n) {
  var out = [], d = 2;
  while (n > 1) { while (n % d === 0) { out.push(d); n /= d; } d++; }
  return out;
}
function gcd(a, b) { return b ? gcd(b, a % b) : a; }

function drawTree(node, x, y, dx, ctx) {
  var isPrime = !node.l;
  ctx.strokeStyle = '#e4e7ec'; ctx.lineWidth = 2;
  [node.l, node.r].forEach(function (c2, i) {
    if (!c2) return;
    var cx = x + (i === 0 ? -dx : dx), cy = y + 74;
    ctx.beginPath(); ctx.moveTo(x, y + 18); ctx.lineTo(cx, cy - 18); ctx.stroke();
    drawTree(c2, cx, cy, dx * 0.55, ctx);
  });
  // node circle
  ctx.fillStyle = isPrime ? '#f97316' : '#ffffff';
  ctx.beginPath(); ctx.arc(x, y, 19, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = isPrime ? '#ea580c' : '#98a2b3'; ctx.lineWidth = 2.5; ctx.stroke();
  ctx.fillStyle = isPrime ? '#fff' : '#0f1b33';
  ctx.font = '600 14px Inter, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(node.v, x, y + 5); ctx.textAlign = 'start';
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, w, h);
  var tA = factorTree(s.a), tB = factorTree(s.b);
  drawTree(tA, w * 0.27, 80, Math.min(95, w * 0.11), ctx);
  drawTree(tB, w * 0.73, 80, Math.min(95, w * 0.11), ctx);
  ctx.font = '600 13px Inter, sans-serif'; ctx.fillStyle = '#6b7891';
  ctx.fillText('factor tree of ' + s.a, w * 0.27 - 52, 40);
  ctx.fillText('factor tree of ' + s.b, w * 0.73 - 52, 40);
}

function upd() {
  var pa = primesOf(s.a), pb = primesOf(s.b);
  var g = gcd(s.a, s.b), l = s.a * s.b / g;
  document.getElementById('fA').innerHTML = s.a + ' = <b>' + pa.join(' × ') + '</b>';
  document.getElementById('fB').innerHTML = s.b + ' = <b>' + pb.join(' × ') + '</b>';
  document.getElementById('hcfRead').innerHTML = 'HCF (shared primes) = <b>' + g + '</b>';
  document.getElementById('lcmRead').innerHTML = 'LCM (all primes) = <b>' + l + '</b> · check: ' + g + ' × ' + l + ' = ' + (g * l) + ' = ' + s.a + ' × ' + s.b + ' ✓';
  draw();
}

LK.slider('na', function (v) { s.a = v; document.getElementById('nav').textContent = v; upd(); });
LK.slider('nb', function (v) { s.b = v; document.getElementById('nbv').textContent = v; upd(); });
st.draw = draw; upd();
