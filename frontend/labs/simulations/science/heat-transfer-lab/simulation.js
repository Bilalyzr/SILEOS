'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, mat: 0, flame: 2, dist: 120, vac: true };
var MATS = [
  { name: 'Copper', k: 1.00, color: '#d97706' },
  { name: 'Steel',  k: 0.45, color: '#94a3b8' },
  { name: 'Glass',  k: 0.18, color: '#93c5fd' },
  { name: 'Wood',   k: 0.06, color: '#a16207' }
];
var rodTemp = [];  // per-cell temperature 0..1
for (var i = 0; i < 40; i++) rodTemp.push(0);
var conv = [];     // convection particles
var simT = 0;

function heatColor(t) {
  // t 0..1 → blue → red → white-hot
  var r = Math.round(40 + 215 * Math.min(1, t * 1.6));
  var g = Math.round(90 + 90 * Math.max(0, 1 - Math.abs(t - 0.55) * 2.4));
  var b = Math.round(160 - 140 * t);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  simT += 0.016;

  if (s.mode === 0) drawConduction(ctx, w, h);
  if (s.mode === 1) drawConvection(ctx, w, h);
  if (s.mode === 2) drawRadiation(ctx, w, h);
}

/* ---------------- conduction ---------------- */
function drawConduction(ctx, w, h) {
  var m = MATS[s.mat];
  // diffuse heat along rod
  var k = 0.012 + m.k * 0.10;
  var N = rodTemp.length;
  for (var it = 0; it < 3; it++) {
    rodTemp[0] = Math.min(1, rodTemp[0] + 0.012 + m.k * 0.02);
    for (var i = N - 1; i > 0; i--) rodTemp[i] += (rodTemp[i - 1] - rodTemp[i]) * k;
  }
  // rod
  var rx = 90, rw = w - 180, ry = h / 2 - 26, rh = 52, cw = rw / N;
  for (var c = 0; c < N; c++) {
    ctx.fillStyle = heatColor(rodTemp[c]);
    ctx.fillRect(rx + c * cw, ry, cw + 1, rh);
  }
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5;
  ctx.strokeRect(rx, ry, rw, rh);
  // particles vibrating — speed by local temp
  ctx.fillStyle = 'rgba(15,23,42,.75)';
  for (var p = 0; p < N; p += 1) {
    var px0 = rx + p * cw + cw / 2, py0 = ry + rh / 2;
    var amp = 1 + rodTemp[p] * 5;
    for (var q = 0; q < 3; q++) {
      var jitter = Math.sin(simT * (6 + rodTemp[p] * 30) + p * 2 + q * 2.1) * amp;
      var jitter2 = Math.cos(simT * (5 + rodTemp[p] * 26) + p * 1.7 + q) * amp;
      ctx.beginPath(); ctx.arc(px0 + jitter, py0 + jitter2, 2.2, 0, Math.PI * 2); ctx.fill();
    }
  }
  // candle flame at left end
  flame(ctx, rx - 22, ry + rh);
  // wax at far end melts when heat arrives
  var endT = rodTemp[N - 1];
  ctx.fillStyle = endT > 0.35 ? '#fca5a5' : '#e2e8f0';
  LK.roundRect(ctx, rx + rw + 14, ry + 6, 26, rh - 12, 6); ctx.fill();
  ctx.strokeStyle = LK.C.sub; ctx.stroke();
  document.getElementById('condRead').innerHTML =
    m.name + ': ' + (m.k > 0.4 ? 'excellent conductor — the far end is ' + (endT > 0.3 ? 'HOT!' : 'warming fast')
    : m.k > 0.12 ? 'poor conductor — heat crawls along'
    : 'insulator — the far end stays cool') +
    '<br>Far-end temperature: <b>' + Math.round(endT * 100) + '%</b> of flame heat';
}

/* ---------------- convection ---------------- */
function drawConvection(ctx, w, h) {
  var bx = w * 0.5 - 160, by = h * 0.5 - 150, bw = 320, bh = 300;
  // water
  ctx.fillStyle = '#dbeafe';
  LK.roundRect(ctx, bx, by, bw, bh, 12); ctx.fill();
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 3; ctx.stroke();
  // heater at bottom center
  var hx = bx + bw / 2, hy = by + bh - 8;
  flame(ctx, hx, hy + 18);
  // convection particle loop
  if (conv.length < 90) {
    conv.push({ leg: 'up', t: Math.random(), x: hx + LK.rand(-24, 24) });
  }
  var speed = 0.10 + s.flame * 0.09;
  ctx.fillStyle = '#ef4444';
  conv.forEach(function (p) {
    // path: up the middle, across the top, down the sides, along the bottom
    var m = 26;
    if (p.leg === 'up') { p.y = hy - 10 - p.t * (bh - 40); p.x += Math.sin(simT * 4 + p.t * 9) * 0.6; p.t += speed; if (p.t >= 1) { p.leg = 'top'; p.t = 0; p.side = Math.random() < 0.5 ? -1 : 1; } }
    else if (p.leg === 'top') { p.x = hx + p.side * p.t * (bw / 2 - m); p.y = by + m; p.t += speed; if (p.t >= 1) { p.leg = 'down'; p.t = 0; } }
    else if (p.leg === 'down') { p.y = by + m + p.t * (bh - 2 * m); p.x = bx + (p.side < 0 ? m : bw - m); p.t += speed; if (p.t >= 1) { p.leg = 'bot'; p.t = 0; } }
    else { p.x = (p.side < 0 ? bx + m : bx + bw - m) - p.side * p.t * (bw / 2 - m); p.y = hy - 10; p.t += speed; if (p.t >= 1) { p.leg = 'up'; p.t = 0; p.x = hx + LK.rand(-24, 24); } }
    ctx.globalAlpha = p.leg === 'up' ? 0.95 : 0.4;
    ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI * 2); ctx.fill();
  });
  ctx.globalAlpha = 1;
  // arrows showing loop
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 2; ctx.setLineDash([5, 5]);
  ctx.beginPath();
  ctx.moveTo(hx, hy - 16); ctx.lineTo(hx, by + 40);
  ctx.lineTo(bx + 46, by + 40); ctx.lineTo(bx + 46, hy - 26); ctx.lineTo(hx, hy - 26);
  ctx.stroke(); ctx.setLineDash([]);
  LK.arrow(ctx, bx + 46, by + 60, -Math.PI / 2, LK.C.sub, 9);
  document.getElementById('convRead').innerHTML =
    'Red = heated water <b>rising</b> (expands, gets lighter). Blue-grey = cooled water <b>sinking</b>. ' +
    'Flame ' + ['off', 'low', 'medium', 'high'][s.flame] + ' → loop runs ' + (s.flame > 1 ? 'faster' : 'slowly') +
    '.<br>This same loop drives sea breezes and monsoon winds!';
}

/* ---------------- radiation ---------------- */
function drawRadiation(ctx, w, h) {
  var scale = 0.55;
  var sx = 130, sy = h / 2;
  var ex = sx + s.dist * scale * 1.6, ey = sy;
  // sun
  var g = ctx.createRadialGradient(sx, sy, 10, sx, sy, 70);
  g.addColorStop(0, '#fde047'); g.addColorStop(1, 'rgba(253,224,71,0)');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(sx, sy, 70, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#f59e0b'; ctx.beginPath(); ctx.arc(sx, sy, 30, 0, Math.PI * 2); ctx.fill();
  // vacuum label
  if (s.vac) {
    ctx.fillStyle = LK.C.sub; ctx.font = '13px system-ui, sans-serif';
    ctx.fillText('— empty space / vacuum —', sx + 60, sy - 90);
  } else {
    ctx.fillStyle = 'rgba(147,197,253,.25)'; ctx.fillRect(sx + 40, sy - 80, ex - sx - 60, 160);
    ctx.fillStyle = LK.C.sub; ctx.fillText('— air medium —', sx + 60, sy - 90);
  }
  // infrared rays
  var intensity = 3200 / (s.dist * s.dist) * 100;
  for (var r = 0; r < 7; r++) {
    var ry = sy + (r - 3) * 22;
    ctx.strokeStyle = 'rgba(249,115,22,' + Math.min(0.85, 0.18 + intensity / 90) + ')';
    ctx.lineWidth = 2;
    var phase = (simT * 240) % 26;
    ctx.beginPath();
    for (var xx = sx + 44; xx < ex - 30; xx += 26) {
      var yy = ry + Math.sin((xx + phase) * 0.16) * 5;
      xx === sx + 44 ? ctx.moveTo(xx, yy) : ctx.lineTo(xx, yy);
    }
    ctx.stroke();
  }
  // earth
  ctx.fillStyle = '#2e6fd8';
  ctx.beginPath(); ctx.arc(ex, ey, 34, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#22c55e';
  ctx.beginPath(); ctx.arc(ex - 10, ey - 8, 12, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(ex + 12, ey + 10, 8, 0, Math.PI * 2); ctx.fill();
  // thermometer on earth
  var t = Math.round(18 + 12000 / (s.dist * s.dist) * 60);
  ctx.fillStyle = LK.C.target;
  ctx.fillRect(ex + 44, ey + 30 - LK.clamp(t / 8, 0, 40), 8, LK.clamp(t / 8, 0, 40));
  document.getElementById('radRead').innerHTML =
    'Distance from Sun: <b>' + (s.dist / 240 * 150).toFixed(0) + ' million km</b> (Earth ≈ 150!)<br>' +
    'Received heat follows the <b>inverse-square law</b>: double the distance → quarter the warmth. ' +
    'Notice the waves cross the vacuum without any medium!';
}

function flame(ctx, x, y) {
  var f = 1 + Math.sin(simT * 9) * 0.12;
  ctx.fillStyle = '#f97316';
  ctx.beginPath();
  ctx.moveTo(x, y - 26 * f);
  ctx.quadraticCurveTo(x + 12, y - 8, x, y);
  ctx.quadraticCurveTo(x - 12, y - 8, x, y - 26 * f);
  ctx.fill();
  ctx.fillStyle = '#fde047';
  ctx.beginPath();
  ctx.moveTo(x, y - 15 * f);
  ctx.quadraticCurveTo(x + 6, y - 4, x, y);
  ctx.quadraticCurveTo(x - 6, y - 4, x, y - 15 * f);
  ctx.fill();
}

/* ---------------- wiring ---------------- */
LK.segment('modeSeg', function (i) {
  s.mode = i;
  document.getElementById('condCard').classList.toggle('hidden', i !== 0);
  document.getElementById('convCard').classList.toggle('hidden', i !== 1);
  document.getElementById('radCard').classList.toggle('hidden', i !== 2);
});
LK.segment('matSeg', function (i) { s.mat = i; for (var j = 0; j < rodTemp.length; j++) rodTemp[j] = 0; });
LK.slider('flame', function (v) {
  s.flame = v;
  document.getElementById('flamev').textContent = ['off', 'low', 'medium', 'high'][v];
});
LK.slider('dist', function (v) {
  s.dist = v;
  document.getElementById('distv').textContent = (v / 240 * 150).toFixed(0) + ' M km';
});
LK.check('vacChk', function (on) { s.vac = on; });

st.draw = draw;
