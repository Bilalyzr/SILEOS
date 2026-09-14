'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var N0 = 400;
var s = { iso: 0, t: 0 };
var ISOS = [
  { name: 'Iodine-131', T: 8, unit: 'days', use: 'Treats thyroid cancer; decays β' },
  { name: 'Carbon-14', T: 5730, unit: 'years', use: 'Dates organic remains up to ~50,000 y' },
  { name: 'Radium-226', T: 1600, unit: 'years', use: 'Marie Curie\u2019s α-emitter' },
  { name: 'Fluorine-18', T: 1.83, unit: 'hours', use: 'PET scans — must be made on-site!' }
];
// map slider 0..400 to 0..3 half-lives worth of time in display units
function tOfSlider(v) { return v / 400 * 3; }    // in half-lives
function fracLeft(hl) { return Math.pow(0.5, hl); }

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var iso = ISOS[s.iso];
  var hl = tOfSlider(s.t);                       // elapsed half-lives
  var frac = fracLeft(hl);
  var nLeft = Math.round(N0 * frac);

  /* left: sample grid of atoms */
  var gx0 = 46, gy0 = 60, cell = Math.min(26, (w * 0.46 - 60) / 20);
  var cols = 20, rows = Math.ceil(N0 / cols);
  var decayed = N0 - nLeft;
  for (var i = 0; i < N0; i++) {
    var cx = gx0 + (i % cols) * cell, cy = gy0 + Math.floor(i / cols) * cell;
    var isDecayed = i < decayed;                 // deterministic for teaching clarity
    ctx.beginPath(); ctx.arc(cx, cy, cell * 0.32, 0, Math.PI * 2);
    if (isDecayed) {
      ctx.fillStyle = '#e4e7ec'; ctx.fill();
      ctx.strokeStyle = '#f1f3f6'; ctx.lineWidth = 1; ctx.stroke();
    } else {
      ctx.fillStyle = '#f97316'; ctx.fill();
      ctx.strokeStyle = '#ea580c'; ctx.lineWidth = 1.5; ctx.stroke();
    }
  }
  // legend
  ctx.font = '600 12px Inter, sans-serif';
  ctx.fillStyle = '#f97316'; ctx.fillText('● parent (' + nLeft + ')', gx0, gy0 + rows * cell + 26);
  ctx.fillStyle = '#98a2b3'; ctx.fillText('● decayed (' + decayed + ')', gx0 + 130, gy0 + rows * cell + 26);

  /* right: decay curve */
  var px0 = w * 0.55, px1 = w - 46, py0 = 56, py1 = h - 70;
  var hMax = 3;
  var TX = function (hl2) { return px0 + (hl2 / hMax) * (px1 - px0); };
  var PY = function (f) { return py1 - f * (py1 - py0); };
  ctx.strokeStyle = '#e4e7ec'; ctx.lineWidth = 1;
  [1, 0.75, 0.5, 0.25].forEach(function (f) {
    ctx.beginPath(); ctx.moveTo(px0, PY(f)); ctx.lineTo(px1, PY(f)); ctx.stroke();
    ctx.fillStyle = '#6b7891'; ctx.font = '11px Inter, sans-serif';
    ctx.fillText((f * 100) + '%', px0 - 32, PY(f) + 4);
  });
  [0, 1, 2, 3].forEach(function (k) {
    ctx.beginPath(); ctx.moveTo(TX(k), py0); ctx.lineTo(TX(k), py1); ctx.stroke();
    ctx.fillText(k + ' T½', TX(k) - 10, py1 + 18);
  });
  // half-life steps
  ctx.fillStyle = 'rgba(3,105,161,.12)';
  for (var k2 = 1; k2 <= 3; k2++) {
    ctx.fillRect(px0, PY(fracLeft(k2)), TX(k2) - px0, py1 - PY(fracLeft(k2)));
  }
  // curve
  ctx.strokeStyle = '#f97316'; ctx.lineWidth = 3;
  ctx.beginPath();
  for (var x2 = 0; x2 <= hMax; x2 += 0.02) {
    var y2 = PY(fracLeft(x2));
    x2 === 0 ? ctx.moveTo(TX(x2), y2) : ctx.lineTo(TX(x2), y2);
  }
  ctx.stroke();
  // marker
  ctx.fillStyle = '#dc2626';
  ctx.beginPath(); ctx.arc(TX(hl), PY(frac), 6, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#dc2626'; ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(TX(hl), PY(frac)); ctx.lineTo(TX(hl), py1); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(px0, PY(frac)); ctx.lineTo(TX(hl), PY(frac)); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = '#6b7891'; ctx.font = '600 12px Inter, sans-serif';
  ctx.fillText('N = N₀ (½)^(t/T½)', px0 + 8, py0 + 14);

  var elapsed = hl * iso.T;
  document.getElementById('remain').innerHTML =
    'Remaining: <b>' + nLeft + ' of ' + N0 + '</b> (' + (frac * 100).toFixed(1) + '%)';
  document.getElementById('half').innerHTML =
    'Elapsed: <b>' + elapsed.toFixed(elapsed < 10 ? 1 : 0) + ' ' + iso.unit + '</b> = ' + hl.toFixed(2) + ' half-lives';
  document.getElementById('use').innerHTML = '💡 ' + iso.use;
}

LK.segment('isoSeg', function (i) { s.iso = i; s.t = 0; document.getElementById('time').value = 0; document.getElementById('timev').textContent = '0'; draw(); });
LK.slider('time', function (v) { s.t = v; document.getElementById('timev').textContent = (v / 400 * 3).toFixed(2) + ' T½'; draw(); });
st.draw = draw; draw();
