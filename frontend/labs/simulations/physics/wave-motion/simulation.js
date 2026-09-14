'use strict';
var s = { A: 1, lam: 2, f: 0.5, t: 0, playing: true };
var st = LK.setupCanvas(document.getElementById('cv'));
var lastT = 0;

function yAt(x) { return s.A * Math.sin(2 * Math.PI * (x / s.lam - s.f * s.t)); }

function draw(now) {
  var dt = Math.min(0.05, (now - lastT) / 1000 || 0.016);
  lastT = now;
  if (s.playing) s.t += dt;

  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var shown = 12;                              // metres of string on screen
  var ppm = (w - 100) / shown;
  var midY = h / 2;
  var X = function (x) { return 50 + x * ppm; };
  var Y = function (y) { return midY - y * 55; };

  // centre line
  ctx.strokeStyle = LK.C.grid2; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(40, midY); ctx.lineTo(w - 30, midY); ctx.stroke();

  // the wave
  ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 3.5;
  ctx.beginPath();
  for (var px = 0; px <= w - 70; px += 2) {
    var wx = px / ppm, wy = yAt(wx);
    px ? ctx.lineTo(X(wx), Y(wy)) : ctx.moveTo(X(wx), Y(wy));
  }
  ctx.stroke();

  // particles at fixed positions (transverse motion only)
  for (var xm = 0; xm <= shown; xm += 0.5) {
    ctx.fillStyle = '#60a5fa';
    ctx.beginPath(); ctx.arc(X(xm), Y(yAt(xm)), 4.5, 0, Math.PI * 2); ctx.fill();
  }

  // crest marker riding at v = f*lam
  var crestX = s.lam * ((s.f * s.t + 0.25) % 1);
  ctx.fillStyle = LK.C.b;
  ctx.beginPath(); ctx.moveTo(X(crestX), Y(s.A) - 12);
  ctx.lineTo(X(crestX) - 8, Y(s.A) - 30); ctx.lineTo(X(crestX) + 8, Y(s.A) - 30);
  ctx.closePath(); ctx.fill();
  LK.chip(ctx, X(crestX), Y(s.A) - 66, 'this crest moves at v = f\u03BB', LK.C.b);

  // wavelength bracket between two crests
  var c2 = crestX + s.lam;
  if (c2 < shown) {
    ctx.strokeStyle = LK.C.ok; ctx.lineWidth = 2;
    var yTop = Math.min(Y(s.A) - 78, 60);
    ctx.beginPath(); ctx.moveTo(X(crestX), yTop); ctx.lineTo(X(c2), yTop); ctx.stroke();
    [crestX, c2].forEach(function (cx) {
      ctx.beginPath(); ctx.moveTo(X(cx), yTop); ctx.lineTo(X(cx), yTop + 10); ctx.stroke();
    });
    ctx.fillStyle = LK.C.ok; ctx.font = '600 13px system-ui, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('\u03BB = ' + s.lam.toFixed(1) + ' m', (X(crestX) + X(c2)) / 2, yTop - 6);
    ctx.textAlign = 'start';
  }

  // amplitude arrow
  ctx.strokeStyle = LK.C.target; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(X(9.6), midY); ctx.lineTo(X(9.6), Y(s.A)); ctx.stroke();
  LK.arrow(ctx, X(9.6), Y(s.A), -Math.PI / 2, LK.C.target, 10);
  LK.arrow(ctx, X(9.6), midY, Math.PI / 2, LK.C.target, 10);
  ctx.fillStyle = LK.C.target; ctx.font = '600 13px system-ui, sans-serif';
  ctx.fillText('A', X(9.6) + 10, midY - Y(s.A) > 0 ? (midY + Y(s.A)) / 2 : (midY + Y(s.A)) / 2);
}

function upd() {
  var v = s.f * s.lam;
  document.getElementById('rSpeed').innerHTML = 'Wave speed v = f\u03BB = <b>' + v.toFixed(2) + ' m/s</b>';
  document.getElementById('rPeriod').innerHTML = 'Time period T = 1/f = <b>' + (1 / s.f).toFixed(2) + ' s</b>';
}

LK.slider('amp', function (v) { s.A = v; document.getElementById('ampv').textContent = v.toFixed(1) + ' m'; });
LK.slider('lam', function (v) { s.lam = v; document.getElementById('lamv').textContent = v.toFixed(1) + ' m'; upd(); });
LK.slider('freq', function (v) { s.f = v; document.getElementById('freqv').textContent = v.toFixed(2) + ' Hz'; upd(); });
LK.button('playBtn', function () {
  s.playing = !s.playing;
  this.textContent = s.playing ? '\u23F8 Pause' : '\u25B6 Play';
});

upd();
st.draw = draw;
