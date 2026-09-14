'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { theta: 0, speed: 1, playing: true, trailSin: [], trailCos: [], t: 0, drag: false };

function draw() {
  var dt = 0.016;
  s.t += dt;
  if (s.playing && !s.drag) s.theta += s.speed * dt;

  // record trails relative to theta (drawn against current theta as right edge)
  s.trailSin.push(Math.sin(s.theta));
  s.trailCos.push(Math.cos(s.theta));
  var TRAIL = 320;
  if (s.trailSin.length > TRAIL) { s.trailSin.shift(); s.trailCos.shift(); }

  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);

  /* ---------- unit circle (left) ---------- */
  var uR = Math.min(h * 0.30, w * 0.20);
  var ucx = 60 + uR + 30, ucy = h / 2;
  ctx.strokeStyle = LK.C.grid2; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(ucx - uR - 20, ucy); ctx.lineTo(ucx + uR + 20, ucy); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(ucx, ucy - uR - 20); ctx.lineTo(ucx, ucy + uR + 20); ctx.stroke();
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(ucx, ucy, uR, 0, Math.PI * 2); ctx.stroke();

  var px0 = ucx + Math.cos(s.theta) * uR;
  var py0 = ucy - Math.sin(s.theta) * uR;
  // radius
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(ucx, ucy); ctx.lineTo(px0, py0); ctx.stroke();
  // sin (vertical drop, brand)
  ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 3.5;
  ctx.beginPath(); ctx.moveTo(px0, ucy); ctx.lineTo(px0, py0); ctx.stroke();
  // cos (horizontal, teal)
  ctx.strokeStyle = LK.C.m; ctx.lineWidth = 3.5;
  ctx.beginPath(); ctx.moveTo(ucx, ucy); ctx.lineTo(px0, ucy); ctx.stroke();
  // dashed guides to graphs
  ctx.setLineDash([4, 5]); ctx.lineWidth = 1.2;
  ctx.strokeStyle = LK.C.brand;
  ctx.beginPath(); ctx.moveTo(px0, py0); ctx.lineTo(w - 30, py0); ctx.stroke();
  ctx.strokeStyle = LK.C.m;
  ctx.beginPath(); ctx.moveTo(px0, ucy); ctx.lineTo(w - 30, ucy - Math.cos(s.theta) * waveAmp(h)); ctx.stroke();
  ctx.setLineDash([]);
  // point
  ctx.fillStyle = LK.C.ink;
  ctx.beginPath(); ctx.arc(px0, py0, 8, 0, Math.PI * 2); ctx.fill();
  // angle arc
  ctx.strokeStyle = LK.C.b; ctx.lineWidth = 2;
  ctx.beginPath();
  var a0 = -s.theta;
  ctx.arc(ucx, ucy, 30, 0, -s.theta, s.theta > 0);
  ctx.stroke();

  /* ---------- waves (right) ---------- */
  var gx0 = ucx + uR + 60, gx1 = w - 30;
  var waveAmp_ = waveAmp(h);
  var gy = h / 2;
  // axes
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(gx0, gy); ctx.lineTo(gx1, gy); ctx.stroke();
  // gridlines at π/2 multiples
  var pxPerRad = (gx1 - gx0) / (Math.PI * 2);
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  var kStart = Math.floor((s.theta - (TRAIL * s.speed * 0.016)) / (Math.PI / 2));
  for (var k = -8; k <= 40; k++) {
    var rad0 = k * Math.PI / 2;
    var xx = gx1 - (s.theta - rad0) * pxPerRad;
    if (xx < gx0 || xx > gx1) continue;
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(xx, gy - waveAmp_ - 10); ctx.lineTo(xx, gy + waveAmp_ + 10); ctx.stroke();
    var lbls = ['0', 'π/2', 'π', '3π/2', '2π'];
    ctx.fillText(lbls[((k % 4) + 4) % 4 === 0 && k !== 0 ? 4 : ((k % 4) + 4) % 4], xx - 8, gy + waveAmp_ + 26);
  }
  // trails (older = left)
  function wave(trail, color) {
    ctx.strokeStyle = color; ctx.lineWidth = 3;
    ctx.beginPath();
    for (var i = 0; i < trail.length; i++) {
      var x = gx1 - (trail.length - 1 - i) * (gx1 - gx0) / TRAIL;
      var y = gy - trail[i] * waveAmp_;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
  }
  wave(s.trailSin, LK.C.brand);
  wave(s.trailCos, LK.C.m);
  // legend
  ctx.font = '600 13px system-ui, sans-serif';
  ctx.fillStyle = LK.C.brand; ctx.fillText('— sin θ', gx0 + 8, gy - waveAmp_ - 14);
  ctx.fillStyle = LK.C.m; ctx.fillText('— cos θ', gx0 + 78, gy - waveAmp_ - 14);

  /* readouts */
  document.getElementById('rSin').textContent = Math.sin(s.theta).toFixed(3);
  document.getElementById('rCos').textContent = Math.cos(s.theta).toFixed(3);
  var degs = ((s.theta * 180 / Math.PI) % 360 + 360) % 360;
  document.getElementById('rTheta').textContent = degs.toFixed(0) + '°';
  document.getElementById('rRad').textContent = (s.theta % (Math.PI * 2)).toFixed(2);
  document.getElementById('angleRead').innerHTML =
    'θ grows with time: one full lap = <b>2π rad = 360°</b>. Currently ' + (degs / 360 * 100).toFixed(0) + '% around.';
}

function waveAmp(h) { return Math.min(h * 0.26, 150); }

/* drag the point */
LK.pointer(st.canvas, {
  down: function (p) {
    var uR = Math.min(st.h * 0.30, st.w * 0.20);
    var ucx = 60 + uR + 30, ucy = st.h / 2;
    var px0 = ucx + Math.cos(s.theta) * uR, py0 = ucy - Math.sin(s.theta) * uR;
    if (Math.hypot(p.x - px0, p.y - py0) < 26) s.drag = true;
  },
  move: function (p, d) {
    if (d && s.drag) {
      var uR = Math.min(st.h * 0.30, st.w * 0.20);
      var ucx = 60 + uR + 30, ucy = st.h / 2;
      var ang = Math.atan2(ucy - p.y, p.x - ucx);
      var old = Math.floor(s.theta / (Math.PI * 2));
      s.theta = old * Math.PI * 2 + ang + (ang < 0 ? Math.PI * 2 : 0);
      s.trailSin = []; s.trailCos = [];
    }
  },
  up: function () { s.drag = false; }
});

LK.slider('spd', function (v) {
  s.speed = v;
  document.getElementById('spdv').textContent = v.toFixed(2) + '\u00D7';
});
LK.button('playBtn', function () {
  s.playing = !s.playing;
  this.textContent = s.playing ? '\u23F8 Pause' : '\u25B6 Play';
});

st.draw = draw;
