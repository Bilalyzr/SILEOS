'use strict';
var TRACK = 20;      // metres
var s = { x: 2, rec: [], recording: false, t: 0, dist: 0, demo: false };
var st = LK.setupCanvas(document.getElementById('cv'));
var lastT = 0;

function layout() {
  return { trackY: Math.min(110, st.h * 0.2), graphTop: st.h * 0.28, padL: 56, padR: 24, padB: 40, padT: 46 };
}

function draw(now) {
  var dt = Math.min(0.05, (now - lastT) / 1000 || 0.016);
  lastT = now;
  if (s.recording || s.demo) {
    s.t += dt;
    if (s.demo) {
      s.x = Math.min(TRACK, s.x + 2 * dt);
      if (s.x >= TRACK) s.demo = false;
    }
    var prev = s.rec[s.rec.length - 1];
    if (prev) s.dist += Math.abs(s.x - prev.x);
    s.rec.push({ t: s.t, x: s.x });
    upd();
  }

  var ctx = st.ctx, w = st.w, h = st.h, L = layout();
  ctx.clearRect(0, 0, w, h);

  /* ---------- track ---------- */
  var tx0 = L.padL + 10, tx1 = w - L.padR - 10, ty = L.trackY;
  var X = function (m) { return tx0 + (m / TRACK) * (tx1 - tx0); };
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.moveTo(tx0, ty); ctx.lineTo(tx1, ty); ctx.stroke();
  for (var m = 0; m <= TRACK; m++) {
    var big = m % 5 === 0;
    ctx.strokeStyle = LK.C.sub; ctx.lineWidth = big ? 2 : 1;
    ctx.beginPath(); ctx.moveTo(X(m), ty - (big ? 12 : 7)); ctx.lineTo(X(m), ty + (big ? 12 : 7)); ctx.stroke();
    if (big) {
      ctx.fillStyle = LK.C.sub; ctx.font = '12px system-ui, sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(m + ' m', X(m), ty + 30);
    }
  }
  ctx.textAlign = 'start';
  // runner
  ctx.font = '34px serif'; ctx.textAlign = 'center';
  ctx.fillText('\u{1F3C3}', X(s.x), ty - 18);
  ctx.textAlign = 'start';
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText(s.recording ? '\u25CF recording — drag along the track!' : 'press on the track to record', L.padL, 24);

  /* ---------- graph ---------- */
  var gx0 = L.padL, gx1 = w - L.padR, gy0 = L.graphTop + L.padT, gy1 = h - L.padB;
  var tMax = Math.max(10, s.t * 1.05);
  var TX = function (t) { return gx0 + (t / tMax) * (gx1 - gx0); };
  var PY = function (m) { return gy1 - (m / TRACK) * (gy1 - gy0); };
  // frame
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(gx0, gy0); ctx.lineTo(gx0, gy1); ctx.lineTo(gx1, gy1); ctx.stroke();
  // grid + labels
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  for (var g = 0; g <= TRACK; g += 5) {
    ctx.strokeStyle = LK.C.grid2; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(gx0, PY(g)); ctx.lineTo(gx1, PY(g)); ctx.stroke();
    ctx.fillText(g + ' m', gx0 - 34, PY(g) + 4);
  }
  var tStep = tMax > 60 ? 20 : tMax > 25 ? 10 : 5;
  for (var tt = 0; tt <= tMax; tt += tStep) {
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(TX(tt), gy0); ctx.lineTo(TX(tt), gy1); ctx.stroke();
    ctx.fillText(tt + ' s', TX(tt) - 8, gy1 + 18);
  }
  ctx.fillStyle = LK.C.sub; ctx.font = '13px system-ui, sans-serif';
  ctx.fillText('position (m) vs time (s)', gx0, gy0 - 14);

  // recorded path
  if (s.rec.length > 1) {
    ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 3;
    ctx.beginPath();
    s.rec.forEach(function (p, i) {
      i ? ctx.lineTo(TX(p.t), PY(p.x)) : ctx.moveTo(TX(p.t), PY(p.x));
    });
    ctx.stroke();
    var last = s.rec[s.rec.length - 1];
    ctx.fillStyle = LK.C.brand;
    ctx.beginPath(); ctx.arc(TX(last.t), PY(last.x), 5.5, 0, Math.PI * 2); ctx.fill();
  }
}

function upd() {
  var x0 = s.rec.length ? s.rec[0].x : 0;
  var disp = s.x - x0;
  document.getElementById('rTime').innerHTML = 'Time: <b>' + s.t.toFixed(1) + ' s</b>';
  document.getElementById('rPos').innerHTML = 'Position: <b>' + s.x.toFixed(1) + ' m</b>';
  document.getElementById('rDist').innerHTML = 'Distance travelled: <b>' + s.dist.toFixed(1) + ' m</b>';
  document.getElementById('rDisp').innerHTML = 'Displacement: <b>' + disp.toFixed(1) + ' m</b>';
  document.getElementById('rSpeed').innerHTML = 'Average speed: <b>' + (s.t ? s.dist / s.t : 0).toFixed(2) + ' m/s</b>';
  document.getElementById('rVel').innerHTML = 'Average velocity: <b>' + (s.t ? disp / s.t : 0).toFixed(2) + ' m/s</b>';
}

LK.pointer(st.canvas, {
  down: function (p) {
    var L = layout();
    if (p.y < L.graphTop) {
      s.recording = true; s.demo = false;
      s.x = LK.clamp((p.x - L.padL - 10) / (st.w - L.padR - 10 - L.padL - 10) * TRACK, 0, TRACK);
    }
  },
  move: function (p, d) {
    if (d && s.recording) {
      var L = layout();
      s.x = LK.clamp((p.x - L.padL - 10) / (st.w - L.padR - 10 - L.padL - 10) * TRACK, 0, TRACK);
    }
  },
  up: function () { s.recording = false; },
  out: function () { s.recording = false; }
});
LK.button('demoBtn', function () { s.demo = true; s.recording = true; });
LK.button('clearBtn', function () {
  s.rec = []; s.t = 0; s.dist = 0; s.x = 2; s.demo = false; s.recording = false; upd();
});

st.draw = draw; upd();
