'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { col: 0, inten: 2, metal: 0, t: 0 };

var COLORS = [
  { name: 'Red', lam: 660, c: '#dc2626', draw: '#ef4444' },
  { name: 'Green', lam: 530, c: '#059669', draw: '#10b981' },
  { name: 'Blue', lam: 450, c: '#0369a1', draw: '#3b82f6' },
  { name: 'UV', lam: 300, c: '#7c3aed', draw: '#a78bfa' }
];
var METALS = [
  { name: 'Cesium', phi: 2.1 },
  { name: 'Sodium', phi: 2.3 },
  { name: 'Zinc', phi: 4.3 }
];

function photonEnergy(colIdx) {   // in eV: E = 1240/λ(nm)
  return 1240 / COLORS[colIdx].lam;
}
function ejects() { return photonEnergy(s.col) > METALS[s.metal].phi; }

var photons = [], electrons = [];
var spawnAcc = 0;

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  s.t += 0.016;
  var col = COLORS[s.col], met = METALS[s.metal];
  var E = photonEnergy(s.col);
  var KE = E - met.phi;

  // vacuum tube outline
  var bx = 60, by = h * 0.16, bw = w - 120, bh = h * 0.66;
  ctx.fillStyle = '#f9fafb';
  LK.roundRect(ctx, bx, by, bw, bh, 22); ctx.fill();
  ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 3; ctx.stroke();
  // cathode plate (left)
  var plateX = bx + 60;
  ctx.fillStyle = '#94a3b8';
  ctx.fillRect(plateX - 8, by + 40, 14, bh - 80);
  ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 2; ctx.strokeRect(plateX - 8, by + 40, 14, bh - 80);
  ctx.fillStyle = '#6b7891'; ctx.font = '600 12px Inter, sans-serif';
  ctx.fillText(met.name + ' plate', plateX - 34, by + bh - 96);
  // anode collector (right)
  var anodeX = bx + bw - 70;
  ctx.fillStyle = '#334155';
  ctx.fillRect(anodeX - 6, by + 60, 12, bh - 120);
  ctx.fillText('collector (+)', anodeX - 40, by + 52);

  // lamp
  var lampX = 30;
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.arc(lampX, by + bh * 0.5, 20, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = col.c; ctx.lineWidth = 3.5; ctx.stroke();

  // spawn photons (rate by intensity)
  spawnAcc += s.inten * 0.8 * 0.05;
  while (spawnAcc >= 1) {
    spawnAcc--;
    photons.push({ y: by + 40 + Math.random() * (bh - 80), x: lampX + 24 });
  }
  // photons travel as wave packets
  var speed = 300;
  ctx.strokeStyle = col.draw; ctx.lineWidth = 2.2;
  photons.forEach(function (p2) {
    p2.x += speed * 0.016;
    // wavy packet
    ctx.beginPath();
    for (var i = 0; i <= 26; i++) {
      var px0 = p2.x - 26 + i * 2;
      var py0 = p2.y + Math.sin((px0 + s.t * 400) * (6.28 / COLORS[s.col].lam) * 60) * 5;
      i === 0 ? ctx.moveTo(px0, py0) : ctx.lineTo(px0, py0);
    }
    ctx.stroke();
  });
  // absorb
  for (var i2 = photons.length - 1; i2 >= 0; i2--) {
    if (photons[i2].x >= plateX) {
      photons.splice(i2, 1);
      if (ejects()) {
        electrons.push({ x: plateX + 10, y: by + 40 + Math.random() * (bh - 80), v: 60 + KE * 30 });
      }
    }
  }
  // electrons fly to collector
  ctx.fillStyle = '#f97316';
  electrons.forEach(function (e2) {
    e2.x += e2.v * 0.016;
    ctx.beginPath(); ctx.arc(e2.x, e2.y, 5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#0f1b33';
    ctx.font = 'bold 9px Inter, sans-serif';
    ctx.fillText('−', e2.x - 2, e2.y + 3);
    ctx.fillStyle = '#f97316';
  });
  for (var i3 = electrons.length - 1; i3 >= 0; i3--) {
    if (electrons[i3].x > anodeX - 8) electrons.splice(i3, 1);
  }

  // ammeter reading
  var current = electrons.length > 0;
  ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(anodeX + 6, by + bh - 30);
  ctx.lineTo(bx + bw - 24, by + bh - 30);
  ctx.lineTo(bx + bw - 24, by + bh + 26);
  ctx.lineTo(plateX, by + bh + 26);
  ctx.lineTo(plateX, by + bh - 30);
  ctx.stroke();
  ctx.beginPath(); ctx.arc(bx + bw / 2, by + bh + 30, 18, 0, Math.PI * 2);
  ctx.fillStyle = '#fff'; ctx.fill(); ctx.stroke();
  ctx.fillStyle = current ? '#059669' : '#98a2b3';
  ctx.font = 'bold 14px Inter, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(current ? 'A' : '0', bx + bw / 2, by + bh + 35);
  ctx.textAlign = 'start';

  document.getElementById('energy').innerHTML =
    'Photon energy hν = 1240/λ = 1240/' + col.lam + ' = <b>' + E.toFixed(2) + ' eV</b>' +
    ' · work function φ = <b>' + met.phi + ' eV</b>';
  document.getElementById('result').innerHTML = !ejects()
    ? '❌ hν &lt; φ → <b>NO emission</b> — brighter light will NOT help! (energy per photon is fixed by colour)'
    : '✅ KE = hν − φ = <b>' + KE.toFixed(2) + ' eV</b> — electrons fly! Intensity sets the <i>count</i>, colour sets the <i>energy</i>.';
}

LK.segment('colSeg', function (i) { s.col = i; });
LK.segment('metSeg', function (i) { s.metal = i; });
LK.slider('int', function (v) { s.inten = v; document.getElementById('intv').textContent = v; });
st.draw = draw;
