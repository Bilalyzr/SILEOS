'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { c0: 1, k: 0.1, t: 0, playing: false, trail: [], particles: [] };

function initParticles() {
  s.particles = [];
  var n = 60;
  for (var i = 0; i < n; i++) {
    s.particles.push({
      x: Math.random(), y: Math.random(),
      vx: (Math.random() - 0.5) * 0.004, vy: (Math.random() - 0.5) * 0.004,
      reacted: false, reactAt: -Math.log(1 - Math.random() * 0.98)   // exponential waiting time
    });
  }
}

function draw() {
  var dt = 0.016;
  if (s.playing) s.t += dt;
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);

  var A = s.c0 * Math.exp(-s.k * s.t);
  var B = s.c0 - A;
  var rate = s.k * A;
  var half = 0.693 / s.k;

  /* ---------- particle chamber (left) ---------- */
  var bx = 50, by = h * 0.16, bw = w * 0.44, bh = h * 0.72;
  ctx.fillStyle = 'rgba(248,250,252,.9)';
  LK.roundRect(ctx, bx, by, bw, bh, 14); ctx.fill();
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 3; ctx.stroke();
  // particles: reacted fraction = B / c0
  var frac = s.c0 > 0 ? B / s.c0 : 0;
  var speedBoost = 1 + (s.k - 0.1) * 4;
  s.particles.forEach(function (p) {
    p.x += p.vx * speedBoost; p.y += p.vy * speedBoost;
    if (p.x < 0.03 || p.x > 0.97) p.vx *= -1;
    if (p.y < 0.03 || p.y > 0.97) p.vy *= -1;
    var reacted = p.reactAt <= s.k * s.t + 0.0001 && s.playing || (p.reactAt <= s.k * s.t);
    reacted = p.reactAt <= s.k * s.t;
    var px0 = bx + p.x * bw, py0 = by + p.y * bh;
    ctx.fillStyle = reacted ? '#22c55e' : '#8b5cf6';
    ctx.beginPath(); ctx.arc(px0, py0, 6.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,.7)';
    ctx.beginPath(); ctx.arc(px0 - 2, py0 - 2, 2, 0, Math.PI * 2); ctx.fill();
  });
  // legend
  ctx.font = '600 13px system-ui, sans-serif';
  ctx.fillStyle = '#8b5cf6'; ctx.fillText('● A (reactant): ' + A.toFixed(2) + ' M', bx + 14, by + bh + 28);
  ctx.fillStyle = '#22c55e'; ctx.fillText('● B (product): ' + B.toFixed(2) + ' M', bx + 190, by + bh + 28);

  /* ---------- concentration-time graph (right) ---------- */
  s.trail.push({ t: s.t, A: A, B: B });
  if (s.trail.length > 500) s.trail.shift();
  var gx0 = w * 0.54, gx1 = w - 40, gy0 = 60, gy1 = h - 70;
  var tMax = Math.max(30, s.t * 1.05);
  var TX = function (t) { return gx0 + (t / tMax) * (gx1 - gx0); };
  var PY = function (c) { return gy1 - (c / s.c0) * (gy1 - gy0); };
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(gx0, gy0); ctx.lineTo(gx0, gy1); ctx.lineTo(gx1, gy1); ctx.stroke();
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  for (var cc = 0; cc <= s.c0; cc += s.c0 / 4) {
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(gx0, PY(cc)); ctx.lineTo(gx1, PY(cc)); ctx.stroke();
    ctx.fillText(cc.toFixed(1) + ' M', gx0 - 36, PY(cc) + 4);
  }
  for (var tt = 0; tt <= tMax; tt += tMax / 6) {
    ctx.fillText(tt.toFixed(0) + 's', TX(tt) - 8, gy1 + 18);
  }
  // half-life line
  ctx.strokeStyle = LK.C.b; ctx.setLineDash([6, 6]); ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(TX(half), gy0); ctx.lineTo(TX(half), gy1); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = LK.C.b; ctx.fillText('t½ = ' + half.toFixed(1) + ' s', TX(half) + 6, gy0 + 14);
  // curves
  function curve(key, color) {
    ctx.strokeStyle = color; ctx.lineWidth = 3;
    ctx.beginPath();
    s.trail.forEach(function (p2, i) {
      i ? ctx.lineTo(TX(p2.t), PY(p2[key])) : ctx.moveTo(TX(p2.t), PY(p2[key]));
    });
    ctx.stroke();
  }
  curve('A', '#8b5cf6');
  curve('B', '#22c55e');
  // dots
  ctx.fillStyle = '#8b5cf6'; ctx.beginPath(); ctx.arc(TX(s.t), PY(A), 5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#22c55e'; ctx.beginPath(); ctx.arc(TX(s.t), PY(B), 5, 0, Math.PI * 2); ctx.fill();
  ctx.font = '600 12.5px system-ui, sans-serif';
  ctx.fillStyle = '#8b5cf6'; ctx.fillText('[A] = c₀e^(−kt)', gx0 + 10, gy0 + 16);
  ctx.fillStyle = '#22c55e'; ctx.fillText('[B] = c₀ − [A]', gx0 + 150, gy0 + 16);

  /* ---------- readouts ---------- */
  document.getElementById('rT').textContent = s.t.toFixed(1) + ' s';
  document.getElementById('rA').textContent = A.toFixed(2) + ' M';
  document.getElementById('rB').textContent = B.toFixed(2) + ' M';
  document.getElementById('rRate').textContent = rate.toFixed(3) + ' M/s';
  var hl = s.t >= half ? Math.floor(s.t / half) : 0;
  document.getElementById('rHalf').innerHTML =
    'Half-lives elapsed: <b>' + hl + '</b> — [A] halves every ' + half.toFixed(1) + ' s, always.';
}

LK.slider('c0', function (v) {
  s.c0 = v;
  document.getElementById('c0v').textContent = v.toFixed(1) + ' M';
  reset();
});
LK.slider('k', function (v) {
  s.k = v;
  document.getElementById('kv').textContent = v.toFixed(2) + ' /s';
  reset();
});
LK.slider('temp', function (v) {
  document.getElementById('tempv').textContent = v + ' K';
  // Arrhenius: k roughly doubles per 10 K — map temperature to k automatically
  var kNew = LK.clamp(0.1 * Math.pow(2, (v - 310) / 10), 0.02, 0.4);
  s.k = kNew;
  document.getElementById('k').value = kNew;
  document.getElementById('kv').textContent = kNew.toFixed(2) + ' /s';
  reset();
});
LK.button('playBtn', function () {
  s.playing = !s.playing;
  this.textContent = s.playing ? '⏸ Pause' : '▶ Run reaction';
});
LK.button('resetBtn', reset);
function reset() {
  s.t = 0; s.trail = []; s.playing = false;
  document.getElementById('playBtn').textContent = '▶ Run reaction';
  initParticles();
}

initParticles();
st.draw = draw;
