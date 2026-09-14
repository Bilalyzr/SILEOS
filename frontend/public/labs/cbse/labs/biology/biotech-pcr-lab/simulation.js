'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { cycle: 0, phase: 0, running: false, speed: 1.5, t: 0, copies: 1 };
var PHASES = [
  { name: 'Denaturation 95°C', dur: 1.0, color: '#dc2626', desc: 'Heat breaks the hydrogen bonds — the double helix UNZIPS into two single strands.' },
  { name: 'Annealing 55°C', dur: 1.0, color: '#0369a1', desc: 'Cooling lets short PRIMERS bind to each strand at the start of the target gene.' },
  { name: 'Extension 72°C', dur: 1.2, color: '#059669', desc: 'Taq polymerase (heat-proof!) extends from the primer, building the complementary strand.' }
];

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  if (s.running) {
    s.t += 0.016 * s.speed;
    var ph = PHASES[s.phase];
    if (s.t >= ph.dur) {
      s.t = 0;
      s.phase = (s.phase + 1) % 3;
      if (s.phase === 0) {                 // completed a full cycle
        s.copies *= 2;
        s.cycle++;
        if (s.cycle >= 8) { s.running = false; s.cycle = 8; s.copies = 256; }
        document.getElementById('cycles').value = s.cycle;
        document.getElementById('cyclesv').textContent = s.cycle;
      }
    }
  }
  var cur = PHASES[s.phase];

  /* temperature gauge */
  var gx = w * 0.16, gy = h * 0.5;
  var targT = s.phase === 0 ? 95 : s.phase === 1 ? 55 : 72;
  var showT = s.running ? targT : 25;
  var barH = h * 0.55;
  ctx.fillStyle = '#f1f3f6';
  LK.roundRect(ctx, gx - 26, gy - barH / 2, 52, barH, 14); ctx.fill();
  ctx.strokeStyle = '#e4e7ec'; ctx.lineWidth = 2; ctx.stroke();
  var fillH = (showT / 100) * (barH - 14);
  ctx.fillStyle = cur.color;
  LK.roundRect(ctx, gx - 21, gy + barH / 2 - 7 - fillH, 42, fillH, 10); ctx.fill();
  ctx.fillStyle = '#0f1b33'; ctx.font = '700 15px Inter, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(showT + '°C', gx, gy + barH / 2 + 28);
  ctx.font = '600 11px Inter, sans-serif'; ctx.fillStyle = '#6b7891';
  ctx.fillText('thermal cycler', gx, gy - barH / 2 - 14);
  ctx.textAlign = 'start';

  /* DNA strands visualization */
  var dx0 = w * 0.32, dy0 = h * 0.30;
  var strandW = Math.min(w * 0.5, 420);
  function helix2(x, y, len, openFrac, color1, color2, label) {
    ctx.lineWidth = 4;
    for (var k = 0; k <= 40; k++) {
      var u = k / 40;
      var open = u < openFrac;
      var sep = open ? 34 : 8 * (1 - Math.abs(u - openFrac) * 2);
      ctx.strokeStyle = color1;
      ctx.beginPath();
      ctx.moveTo(x + u * len - 3, y - Math.sin(u * 9) * sep * 0.3 - sep / 2);
      ctx.lineTo(x + u * len + 3, y - sep / 2 + Math.cos(u * 9) * 4);
      ctx.stroke();
    }
    // two backbones
    [[-1, color1], [1, color2]].forEach(bb => {
      ctx.strokeStyle = bb[1]; ctx.lineWidth = 4;
      ctx.beginPath();
      for (var k2 = 0; k2 <= 60; k2++) {
        var u2 = k2 / 60;
        var sep2 = u2 < openFrac ? 34 : 8;
        var py0 = y + bb[0] * sep2 / 2 + Math.sin(u2 * 12) * 3;
        k2 ? ctx.lineTo(x + u2 * len, py0) : ctx.moveTo(x + u2 * len, py0);
      }
      ctx.stroke();
    });
    if (label) {
      ctx.fillStyle = '#6b7891'; ctx.font = '600 11px Inter, sans-serif';
      ctx.fillText(label, x, y + 46);
    }
  }
  var openFrac = s.phase === 0 ? Math.min(1, s.t / 0.7) : 1;
  var copiesShown = Math.min(4, 1 + Math.floor(s.cycle / 2));
  for (var c2 = 0; c2 < copiesShown; c2++) {
    helix2(dx0 + c2 * 22, dy0 + c2 * 74, strandW - c2 * 22, openFrac,
      '#f97316', '#0369a1', c2 === 0 ? 'template' : 'copy ' + c2);
  }
  // primers on annealing
  if (s.phase === 1) {
    ctx.fillStyle = '#b45309';
    ctx.fillRect(dx0 + 6, dy0 - 42, 70, 7);
    ctx.fillRect(dx0 + 6, dy0 + 36, 70, 7);
    ctx.font = '600 10.5px Inter, sans-serif';
    ctx.fillText('primers bind', dx0 + 84, dy0 - 36);
  }
  if (s.phase === 2) {
    ctx.fillStyle = '#059669';
    ctx.font = '600 12px Inter, sans-serif';
    ctx.fillText('Taq polymerase →→→', dx0 + strandW * 0.5, dy0 + 60);
  }

  /* exponential graph */
  var px0 = w * 0.78, px1 = w - 40, py0 = h * 0.20, py1 = h - 60;
  ctx.strokeStyle = '#e4e7ec'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(px0, py0); ctx.lineTo(px0, py1); ctx.lineTo(px1, py1); ctx.stroke();
  ctx.strokeStyle = '#f97316'; ctx.lineWidth = 3;
  ctx.beginPath();
  for (var c3 = 0; c3 <= 8; c3++) {
    var yv = Math.pow(2, c3);
    var pyy = py1 - (Math.log2(yv) / 8) * (py1 - py0);
    var pxx = px0 + (c3 / 8) * (px1 - px0);
    c3 ? ctx.lineTo(pxx, pyy) : ctx.moveTo(pxx, pyy);
  }
  ctx.stroke();
  ctx.fillStyle = '#dc2626';
  ctx.beginPath(); ctx.arc(px0 + (s.cycle / 8) * (px1 - px0), py1 - (s.cycle / 8) * (py1 - py0), 5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#6b7891'; ctx.font = '600 11px Inter, sans-serif';
  ctx.fillText('copies (log)', px0 - 6, py0 - 10);
  ctx.fillText('cycles', px1 - 36, py1 + 18);

  document.getElementById('stage').innerHTML = '<b style="color:' + cur.color + ';">' + cur.name + '</b> — ' + cur.desc;
  document.getElementById('copies').innerHTML = 'DNA copies: <b>' + s.copies + '</b>' +
    (s.cycle >= 8 ? ' — in a real PCR: 30 cycles → 1,073,741,824!' : '');
}

LK.slider('cycles', function (v) {
  s.cycle = v;
  s.copies = Math.pow(2, v);
  s.running = false;
  document.getElementById('cyclesv').textContent = v;
});
LK.slider('spd', function (v) { s.speed = v; document.getElementById('spdv').textContent = v.toFixed(1) + '×'; });
LK.button('runBtn', function () {
  if (s.cycle >= 8) { s.cycle = 0; s.copies = 1; document.getElementById('cycles').value = 0; document.getElementById('cyclesv').textContent = 0; }
  s.phase = 0; s.t = 0;
  s.running = !s.running;
  this.textContent = s.running ? '\u23F8 Pause' : '\u25B6 Run PCR';
});
st.draw = draw;
