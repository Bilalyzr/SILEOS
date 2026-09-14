'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, p: 0 };

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var u = s.p / 100;
  var cx = w / 2;

  if (s.mode === 0) {
    // funnel + filter paper + beaker
    ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(cx - 110, h * 0.18); ctx.lineTo(cx, h * 0.46); ctx.lineTo(cx + 110, h * 0.18);
    ctx.stroke();
    // filter paper with pore dots
    ctx.strokeStyle = '#b45309'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(cx - 96, h * 0.22); ctx.quadraticCurveTo(cx, h * 0.52, cx + 96, h * 0.22); ctx.stroke();
    ctx.fillStyle = '#6b7891';
    for (var i = 0; i < 10; i++) {
      ctx.beginPath(); ctx.arc(cx - 80 + i * 18, h * 0.30 + (i % 3) * 8, 1.6, 0, Math.PI * 2); ctx.fill();
    }
    // muddy water pouring
    if (u < 0.5) {
      ctx.fillStyle = '#a16207';
      ctx.fillRect(cx + 150, h * 0.10, 26, 40);
      ctx.fillStyle = 'rgba(161,98,7,.6)';
      ctx.fillRect(cx - 10, h * 0.16, 20, h * 0.2 * (1 - u * 1.6 + 0.5));
    }
    // sand trapped on paper
    var sand = LK.clamp(u * 1.4 - 0.2, 0, 1);
    ctx.fillStyle = '#a16207';
    for (var d2 = 0; d2 < 26; d2++) {
      var fx = cx - 70 + (d2 * 53) % 150;
      var fy = h * 0.34 + (d2 * 31) % 22 + sand * 6;
      ctx.beginPath(); ctx.arc(fx, fy, 4 * sand, 0, Math.PI * 2); ctx.fill();
    }
    // clear filtrate
    var lvl = LK.clamp((u - 0.2) * 0.8, 0, 1);
    ctx.fillStyle = 'rgba(125,211,252,.55)';
    ctx.fillRect(cx - 90, h * 0.80 - lvl * h * 0.24, 180, lvl * h * 0.24);
    ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 3;
    ctx.strokeRect(cx - 94, h * 0.56, 188, h * 0.24);
    document.getElementById('explain').innerHTML = '<b>Filtration</b> separates by <b>particle size</b>: sand (residue) stays on the paper; water (filtrate) passes. Used for purifying drinking water!';
  } else if (s.mode === 1) {
    // evaporation: salt solution → burner → salt crystals
    ctx.fillStyle = 'rgba(56,189,248,.35)';
    var fill = (1 - u) * h * 0.2;
    ctx.fillRect(cx - 90, h * 0.55 - fill, 180, fill + 4);
    ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 3;
    ctx.strokeRect(cx - 94, h * 0.35, 188, h * 0.24);
    // vapour
    ctx.strokeStyle = 'rgba(107,120,145,.5)';
    for (var v2 = 0; v2 < 5; v2++) {
      var vy = h * 0.34 - ((u * 300 + v2 * 40) % 120);
      ctx.beginPath();
      ctx.moveTo(cx - 60 + v2 * 30, vy);
      ctx.quadraticCurveTo(cx - 40 + v2 * 30, vy - 16, cx - 60 + v2 * 30, vy - 30);
      ctx.stroke();
    }
    // salt crystals grow
    if (u > 0.6) {
      var cr = (u - 0.6) / 0.4;
      ctx.fillStyle = '#fff';
      ctx.strokeStyle = '#0369a1'; ctx.lineWidth = 2;
      for (var c2 = 0; c2 < 7; c2++) {
        var sz = 6 + cr * 10;
        LK.roundRect(ctx, cx - 70 + c2 * 22, h * 0.56 - sz, sz, sz, 2);
        ctx.fill(); ctx.stroke();
      }
    }
    // burner
    ctx.fillStyle = '#6b7891';
    ctx.fillRect(cx - 8, h * 0.72, 16, 40);
    var flame2 = 1 + Math.sin(u * 40) * 0.15;
    ctx.fillStyle = '#f97316';
    ctx.beginPath();
    ctx.moveTo(cx, h * 0.70 - 22 * flame2);
    ctx.quadraticCurveTo(cx + 12, h * 0.72, cx, h * 0.74);
    ctx.quadraticCurveTo(cx - 12, h * 0.72, cx, h * 0.70 - 22 * flame2);
    ctx.fill();
    document.getElementById('explain').innerHTML = '<b>Evaporation</b> separates by <b>boiling point</b>: water leaves as vapour, salt stays behind. This is how salt farms harvest sea salt!';
  } else if (s.mode === 2) {
    // winnowing: grain + husk blown
    ctx.fillStyle = '#b45309';
    for (var g2 = 0; g2 < 40; g2++) {
      var gx = cx - 60 + ((g2 * 37) % 120);
      var gy = h * 0.72 - ((g2 * 53) % 40) * 0.4;
      ctx.beginPath(); ctx.ellipse(gx, gy, 5, 3, g2, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = 'rgba(148,163,184,.8)';
    for (var k2 = 0; k2 < 30; k2++) {
      var hx = cx - 40 + ((k2 * 41) % 90) + u * 260;
      var hy = h * 0.66 - ((k2 * 29) % 60) * 0.4 - u * 90 + Math.sin(k2 + u * 8) * 12;
      if (u > 0.05) {
        ctx.beginPath(); ctx.ellipse(hx, hy, 4, 2, k2, 0, Math.PI * 2); ctx.fill();
      }
    }
    // fan / wind
    if (u > 0) {
      ctx.strokeStyle = '#0369a1'; ctx.lineWidth = 2;
      for (var wv = 0; wv < 4; wv++) {
        var wy = h * 0.62 + wv * 16;
        ctx.beginPath();
        ctx.moveTo(cx - 190 + wv * 10, wy);
        ctx.quadraticCurveTo(cx - 130 + u * 40, wy - 8, cx - 70 + u * 120, wy);
        ctx.stroke();
      }
    }
    // basket
    ctx.strokeStyle = '#b45309'; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.ellipse(cx - 40, h * 0.80, 70, 20, 0, 0, Math.PI); ctx.stroke();
    document.getElementById('explain').innerHTML = '<b>Winnowing</b> separates by <b>density</b>: the wind carries light husk away while heavy grain falls back. Farmers have done it for thousands of years!';
  } else if (s.mode === 3) {
    // magnetic: iron nails + sulphur
    ctx.fillStyle = '#fde68a';
    for (var s2 = 0; s2 < 26; s2++) {
      ctx.beginPath(); ctx.arc(cx - 120 + ((s2 * 61) % 240), h * 0.62 - ((s2 * 37) % 30) * 0.5, 3.4, 0, Math.PI * 2); ctx.fill();
    }
    ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 3;
    for (var n2 = 0; n2 < 9; n2++) {
      var nx = cx - 90 + ((n2 * 47) % 190);
      var ny = h * 0.60 - ((n2 * 31) % 26) * 0.5;
      var pull = u * 130;
      var dx = (cx + 150 - nx), dy2 = (h * 0.5 - ny);
      var dd = Math.hypot(dx, dy2);
      var k2 = u > 0.05 ? pull / dd : 0;
      var px0 = nx + dx * Math.min(k2, 0.95), py0 = ny + dy2 * Math.min(k2, 0.95);
      ctx.beginPath(); ctx.moveTo(px0, py0 - 8); ctx.lineTo(px0, py0 + 8); ctx.stroke();
    }
    // magnet
    ctx.fillStyle = '#dc2626';
    ctx.fillRect(cx + 150, h * 0.42, 34, 22);
    ctx.fillStyle = '#e4e7ec';
    ctx.fillRect(cx + 150, h * 0.56, 34, 22);
    ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 2.5;
    ctx.strokeRect(cx + 150, h * 0.42, 34, 36);
    // field hint
    ctx.strokeStyle = 'rgba(220,38,38,.4)';
    ctx.beginPath(); ctx.arc(cx + 150, h * 0.5, 60 + u * 20, Math.PI * 0.6, Math.PI * 1.4); ctx.stroke();
    document.getElementById('explain').innerHTML = '<b>Magnetic separation</b> exploits <b>magnetism</b>: iron jumps to the magnet; non-magnetic sulphur stays. Used to sort scrap metal!';
  } else {
    // chromatography: dyes climb paper
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(cx - 100, h * 0.68, 50, 24);
    ctx.fillStyle = '#0369a1';
    ctx.fillRect(cx + 50, h * 0.68, 50, 24);
    // paper strip
    ctx.fillStyle = '#fff';
    ctx.fillRect(cx - 14, h * 0.16, 28, h * 0.52);
    ctx.strokeStyle = '#e4e7ec'; ctx.strokeRect(cx - 14, h * 0.16, 28, h * 0.52);
    var rise = u * h * 0.5;
    var cols = [['#f59e0b', 1.0, 12], ['#dc2626', 0.72, 22], ['#0369a1', 0.5, 4]];
    cols.forEach(function (c3) {
      ctx.fillStyle = c3[0];
      ctx.globalAlpha = 0.85;
      ctx.fillRect(cx - 14 + c3[2] - 6, h * 0.68 - rise * c3[1], 12, 34);
      ctx.globalAlpha = 1;
    });
    // solvent front line
    if (u > 0.1) {
      ctx.strokeStyle = '#6b7891'; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(cx - 14, h * 0.68 - rise); ctx.lineTo(cx + 14, h * 0.68 - rise); ctx.stroke();
      ctx.setLineDash([]);
    }
    document.getElementById('explain').innerHTML = '<b>Chromatography</b> separates by <b>attraction</b>: each dye climbs at its own speed — the ink reveals it was a <b>mixture</b>! Forensic labs use this on inks and poisons.';
  }
}

LK.segment('modeSeg', function (i) { s.mode = i; s.p = 0; document.getElementById('prog').value = 0; document.getElementById('progv').textContent = '0%'; draw(); });
LK.slider('prog', function (v) { s.p = v; document.getElementById('progv').textContent = v + '%'; draw(); });
st.draw = draw; draw();
