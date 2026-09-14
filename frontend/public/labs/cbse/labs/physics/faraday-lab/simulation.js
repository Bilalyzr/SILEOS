'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { loops: 8, flip: 1, magY: 0, magV: 0, drag: false, emf: 0, t: 0 };

var track = [];   // emf history for the scope
var SCOPE = 260;

function coilCenter() { return { x: st.w * 0.62, y: st.h * 0.5 }; }
var COIL_R = 62;

function fluxFromMag(dist) {
  // crude dipole flux falloff
  var B = 2200 / (30 + Math.abs(dist) * Math.abs(dist) * 0.55);
  return B;
}

function physics() {
  if (s.drag) return;
  // free the magnet gently back to start height
  s.magY += (0 - s.magY) * 0.06;
  s.magV = 0;
}

function computeEMF() {
  var c = coilCenter();
  var dist = s.magY;                            // relative to coil center line (screen y diff)
  var flux = fluxFromMag(dist) * s.loops * s.flip;
  var dFlux = -(fluxFromMag(dist - s.magV) * s.loops * s.flip) + flux;  // change per frame
  s.emf = dFlux * 0.045;
  track.push(s.emf);
  if (track.length > SCOPE) track.shift();
}

function draw() {
  s.t += 0.016;
  physics();
  computeEMF();
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var c = coilCenter();

  /* ---------- coil ---------- */
  var wireColor = '#334155';
  for (var l = 0; l < s.loops; l++) {
    var lx = c.x - (s.loops - 1) * 7 + l * 14;
    ctx.strokeStyle = wireColor; ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.ellipse(lx, c.y, 13, COIL_R, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
  // induced current glow in wires when emf nonzero
  if (Math.abs(s.emf) > 0.02) {
    ctx.strokeStyle = 'rgba(37,99,235,' + Math.min(0.9, Math.abs(s.emf) * 1.6) + ')';
    ctx.lineWidth = 2.5;
    for (var l2 = 0; l2 < s.loops; l2++) {
      var lx2 = c.x - (s.loops - 1) * 7 + l2 * 14;
      var ph = (s.t * 6 * Math.sign(s.emf) + l2 * 0.6) % 1;
      var ang = ph * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(lx2 + Math.cos(ang) * 13, c.y + Math.sin(ang) * COIL_R, 3.4, 0, Math.PI * 2);
      ctx.fillStyle = '#2563eb'; ctx.fill();
    }
  }
  // wires to galvanometer
  ctx.strokeStyle = wireColor; ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(c.x - (s.loops - 1) * 7 - 13, c.y - COIL_R);
  ctx.quadraticCurveTo(150, 90, 120, h * 0.78);
  ctx.moveTo(c.x + (s.loops - 1) * 7 + 13, c.y - COIL_R);
  ctx.quadraticCurveTo(w - 260, 70, w - 120, h * 0.78);
  ctx.stroke();

  /* ---------- bar magnet ---------- */
  var mw = 46, mh = 150;
  var magX = c.x;
  var magY = c.y + s.magY;    // s.magY: offset (0 = centered in coil)
  ctx.save();
  ctx.translate(magX, magY);
  ctx.fillStyle = s.flip > 0 ? '#ef4444' : '#3b82f6';
  ctx.fillRect(-mw / 2, -mh / 2, mw / 2, mh);
  ctx.fillStyle = s.flip > 0 ? '#3b82f6' : '#ef4444';
  ctx.fillRect(0, -mh / 2, mw / 2, mh);
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5;
  ctx.strokeRect(-mw / 2, -mh / 2, mw, mh);
  ctx.fillStyle = '#fff'; ctx.font = 'bold 20px system-ui, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(s.flip > 0 ? 'N' : 'S', -mw / 4, 8);
  ctx.fillText(s.flip > 0 ? 'S' : 'N', mw / 4, 8);
  ctx.textAlign = 'start';
  ctx.restore();
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText('⇕ drag the magnet through the coil', c.x - 110, c.y - COIL_R - 46);

  /* ---------- field lines around magnet ---------- */
  ctx.lineWidth = 1.4;
  for (var fl = 0; fl < 5; fl++) {
    var off = 30 + fl * 16;
    ctx.strokeStyle = 'rgba(79,70,229,0.30)';
    ctx.beginPath();
    ctx.ellipse(magX, magY, off, off * 1.5, 0, 0, Math.PI * 2);
    ctx.stroke();
  }

  /* ---------- galvanometer ---------- */
  var gx = w - 110, gy = h * 0.78, gR = 54;
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.arc(gx, gy, gR, Math.PI, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 4; ctx.stroke();
  ctx.beginPath(); ctx.moveTo(gx - gR, gy); ctx.lineTo(gx + gR, gy); ctx.stroke();
  ctx.fillStyle = LK.C.sub; ctx.font = '600 11px system-ui, sans-serif';
  ctx.fillText('−', gx - gR - 4, gy - 6);
  ctx.fillText('+', gx + gR - 2, gy - 6);
  // needle
  var swing = LK.clamp(s.emf * 1.4, -1.2, 1.2);
  var nAng = -Math.PI / 2 + swing;
  ctx.strokeStyle = LK.C.target; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(gx, gy);
  ctx.lineTo(gx + Math.cos(nAng) * (gR - 8), gy + Math.sin(nAng) * (gR - 8));
  ctx.stroke();
  ctx.fillStyle = LK.C.ink; ctx.beginPath(); ctx.arc(gx, gy, 5, 0, Math.PI * 2); ctx.fill();

  /* ---------- emf scope (bottom-left) ---------- */
  var sx0 = 60, sx1 = w * 0.42, sy0 = h - 130, sy1 = h - 60;
  ctx.strokeStyle = LK.C.grid2; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(sx0, (sy0 + sy1) / 2); ctx.lineTo(sx1, (sy0 + sy1) / 2); ctx.stroke();
  ctx.strokeStyle = '#2563eb'; ctx.lineWidth = 2.2;
  ctx.beginPath();
  track.forEach(function (e2, i) {
    var x = sx0 + (i / SCOPE) * (sx1 - sx0);
    var y = (sy0 + sy1) / 2 - LK.clamp(e2 * 22, -34, 34);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.stroke();
  ctx.fillStyle = LK.C.sub; ctx.font = '600 12px system-ui, sans-serif';
  ctx.fillText('induced EMF vs time (move the magnet!)', sx0, sy0 - 8);

  /* ---------- readouts ---------- */
  document.getElementById('emfRead').textContent = Math.abs(s.emf).toFixed(2) + ' V';
  document.getElementById('lenz').innerHTML =
    Math.abs(s.emf) < 0.02 ? 'No motion → <b>no EMF</b>. A still magnet induces nothing!' :
    (s.emf > 0 ? 'Needle swings right — ' : 'Needle swings left — ') +
    'induced current <b>opposes</b> the change (Lenz\u2019s law). ' + s.loops + ' loops multiply the EMF.';
}

/* ---------- drag the magnet ---------- */
LK.pointer(st.canvas, {
  down: function (p) {
    var c = coilCenter();
    if (Math.abs(p.x - c.x) < 60 && Math.abs(p.y - (c.y + s.magY)) < 100) {
      s.drag = true;
    }
  },
  move: function (p, d) {
    if (d && s.drag) {
      var c = coilCenter();
      var newY = LK.clamp(p.y - c.y, -st.h * 0.36, st.h * 0.36);
      s.magV = newY - s.magY;
      s.magY = newY;
    }
  },
  up: function () { s.drag = false; }
});

LK.slider('loops', function (v) {
  s.loops = v;
  document.getElementById('loopsv').textContent = v;
});
LK.button('flipBtn', function () { s.flip *= -1; });

st.draw = draw;
