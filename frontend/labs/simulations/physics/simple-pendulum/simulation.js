'use strict';
var s = { L: 1, amp: 15, g: 9.8, theta: 0, omega: 0, playing: true, slow: false };
var st = LK.setupCanvas(document.getElementById('cv'));
var lastT = 0;
var crossings = [];   // timestamps of same-direction zero crossings

function reset() {
  s.theta = s.amp * Math.PI / 180;
  s.omega = 0;
  crossings = [];
  document.getElementById('rMeasured').innerHTML = 'Measured T: — (watch one full swing)';
}

function draw(now) {
  var dtReal = Math.min(0.05, (now - lastT) / 1000 || 0.016);
  lastT = now;
  var dt = dtReal * (s.slow ? 0.25 : 1);
  var prevTheta = s.theta;
  if (s.playing) {
    // Euler–Cromer, sub-stepped for stability
    for (var i = 0; i < 4; i++) {
      var h = dt / 4;
      s.omega += -(s.g / s.L) * Math.sin(s.theta) * h;
      s.theta += s.omega * h;
    }
    // detect period (same-direction zero crossings)
    if (prevTheta < 0 && s.theta >= 0) {
      var tNow = (window.__pendT = (window.__pendT || 0) + dtReal);
      crossings.push(tNow);
      if (crossings.length >= 3) {
        var Tmeas = crossings[crossings.length - 1] - crossings[crossings.length - 3];
        document.getElementById('rMeasured').innerHTML = 'Measured T: <b>' + Tmeas.toFixed(2) + ' s</b>';
      }
    }
    document.getElementById('rTheta').innerHTML = 'θ: ' + (s.theta * 180 / Math.PI).toFixed(1) + '\u00B0';
  }

  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var ppm = (h - 150) / 2.7;
  var pivX = w / 2, pivY = 70;
  var bx = pivX + Math.sin(s.theta) * s.L * ppm;
  var by = pivY + Math.cos(s.theta) * s.L * ppm;

  // ceiling
  ctx.fillStyle = LK.C.grid2;
  ctx.fillRect(pivX - 90, pivY - 26, 180, 14);
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 1.5;
  for (var hx = -80; hx <= 80; hx += 20) {
    ctx.beginPath(); ctx.moveTo(pivX + hx, pivY - 12); ctx.lineTo(pivX + hx - 8, pivY - 24); ctx.stroke();
  }
  // vertical reference
  ctx.strokeStyle = LK.C.sub; ctx.setLineDash([6, 6]); ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(pivX, pivY); ctx.lineTo(pivX, pivY + s.L * ppm + 40); ctx.stroke();
  ctx.setLineDash([]);
  // angle arc
  ctx.strokeStyle = LK.C.b;
  ctx.beginPath();
  ctx.arc(pivX, pivY, 52, Math.PI / 2, Math.PI / 2 - s.theta, s.theta > 0);
  ctx.stroke();

  // rod + bob
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(pivX, pivY); ctx.lineTo(bx, by); ctx.stroke();
  var bobR = 15 + s.L * 5;
  var grad = ctx.createRadialGradient(bx - 5, by - 5, 2, bx, by, bobR);
  grad.addColorStop(0, '#a5b4fc'); grad.addColorStop(1, LK.C.brand);
  ctx.fillStyle = grad;
  ctx.beginPath(); ctx.arc(bx, by, bobR, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2; ctx.stroke();

  // scale ruler
  ctx.fillStyle = LK.C.sub; ctx.font = '12px system-ui, sans-serif';
  ctx.fillText('L = ' + s.L.toFixed(1) + ' m', pivX + 10, pivY + s.L * ppm * 0.5);
  ctx.fillText('0.5 m', pivX + 46, pivY + 0.5 * ppm + 3);
  ctx.fillText('1.0 m', pivX + 46, pivY + 1.0 * ppm + 3);
  ctx.fillText('1.5 m', pivX + 46, pivY + 1.5 * ppm + 3);
  ctx.strokeStyle = LK.C.grid2;
  [0.5, 1.0, 1.5, 2.0, 2.5].forEach(function (m) {
    ctx.beginPath(); ctx.moveTo(pivX - 10, pivY + m * ppm); ctx.lineTo(pivX + 40, pivY + m * ppm); ctx.stroke();
  });
}

function updStatic() {
  var Th = 2 * Math.PI * Math.sqrt(s.L / s.g);
  document.getElementById('rTheory').innerHTML = 'Theory (small angles): T = 2\u03C0\u221A(L/g) = <b>' + Th.toFixed(2) + ' s</b>';
}

LK.slider('len', function (v) {
  s.L = v;
  document.getElementById('lenv').textContent = v.toFixed(1) + ' m';
  reset(); updStatic();
});
LK.slider('amp', function (v) {
  s.amp = v;
  document.getElementById('ampv').textContent = v + '\u00B0';
  reset(); updStatic();
});
LK.segment('gSeg', function (i) { s.g = [9.8, 1.62, 3.71][i]; reset(); updStatic(); });
LK.check('slowChk', function (on) { s.slow = on; });
LK.button('playBtn', function () {
  s.playing = !s.playing;
  this.textContent = s.playing ? '\u23F8 Pause' : '\u25B6 Play';
});
LK.button('resetBtn', reset);

reset();
st.draw = draw;
