'use strict';
var s = { light: 60, co2: 60, temp: 30 };
var st = LK.setupCanvas(document.getElementById('cv'));
var bubbles = [];
var spawnAcc = 0, lastT = 0;

function sat(v, k) { return 1 - Math.exp(-k * v); }          // 0..1 saturating
function rate() {
  var tempF = Math.exp(-Math.pow(s.temp - 30, 2) / (2 * 9 * 9));
  return 55 * Math.min(sat(s.light / 100, 3), sat(s.co2 / 100, 3)) * tempF - 4;
}

function draw(now) {
  var dt = Math.min(0.05, (now - lastT) / 1000 || 0.016);
  lastT = now;
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);

  var r = rate();   // bubbles per minute (signed)

  /* ---------- scene ---------- */
  // background light level
  var amb = s.light / 100;
  ctx.fillStyle = 'rgba(255,244,214,' + amb * 0.35 + ')';
  ctx.fillRect(0, 0, w, h);

  // sun / lamp
  var sx = w * 0.16, sy = h * 0.16;
  var glowR = 30 + amb * 50;
  var glowA = 0.25 + 0.75 * amb;
  var gg = ctx.createRadialGradient(sx, sy, 4, sx, sy, glowR);
  gg.addColorStop(0, 'rgba(253,224,71,' + glowA + ')');
  gg.addColorStop(1, 'rgba(253,224,71,0)');
  ctx.fillStyle = gg;
  ctx.beginPath(); ctx.arc(sx, sy, glowR, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = s.light > 0 ? '#f59e0b' : '#94a3b8';
  ctx.beginPath(); ctx.arc(sx, sy, 24, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText('light ' + s.light + '%', sx - 30, sy + 46);

  // beaker
  var bx = w * 0.42, by = h * 0.24, bw = Math.min(300, w * 0.34), bh = h * 0.62;
  ctx.fillStyle = 'rgba(191,219,254,.35)';
  ctx.fillRect(bx, by + bh * 0.12, bw, bh * 0.88);
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(bx - 10, by); ctx.lineTo(bx, by); ctx.lineTo(bx, by + bh);
  ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by); ctx.lineTo(bx + bw + 10, by);
  ctx.stroke();

  // Hydrilla plant
  var px = bx + bw / 2, pbase = by + bh - 6;
  ctx.strokeStyle = '#15803d'; ctx.lineWidth = 4; ctx.lineCap = 'round';
  var stems = [-40, -15, 12, 38];
  stems.forEach(function (off, i) {
    ctx.beginPath(); ctx.moveTo(px, pbase);
    ctx.quadraticCurveTo(px + off * 0.4, pbase - bh * 0.3, px + off, pbase - bh * 0.52);
    ctx.stroke();
    ctx.fillStyle = '#22c55e';
    for (var l = 1; l <= 3; l++) {
      var lx = px + off * (l / 3.4), ly = pbase - bh * 0.52 * (l / 3.2);
      ctx.beginPath(); ctx.ellipse(lx - 9, ly, 13, 5, -0.5 - l * 0.2, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.ellipse(lx + 9, ly - 4, 13, 5, 0.5 + l * 0.2, 0, Math.PI * 2); ctx.fill();
    }
  });

  // bubbles
  var ratePerSec = Math.max(0, r) / 60;
  spawnAcc += ratePerSec * dt * 3;   // visual exaggeration
  while (spawnAcc >= 1) {
    spawnAcc--;
    bubbles.push({ x: px + LK.rand(-34, 34), y: pbase - bh * 0.3, sway: Math.random() * 6.28, v: LK.rand(26, 46) });
  }
  ctx.fillStyle = 'rgba(255,255,255,.92)';
  ctx.strokeStyle = 'rgba(96,165,250,.9)';
  for (var i = bubbles.length - 1; i >= 0; i--) {
    var b = bubbles[i];
    b.y -= b.v * dt; b.sway += dt * 4;
    b.x += Math.sin(b.sway) * 0.5;
    if (b.y < by + bh * 0.16) { bubbles.splice(i, 1); continue; }
    ctx.beginPath(); ctx.arc(b.x, b.y, 3.6, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }

  // thermometer
  var tx = bx + bw + 34, ty0 = by + 30, ty1 = by + bh - 10;
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 2;
  ctx.strokeRect(tx, ty0, 16, ty1 - ty0);
  var tf = (s.temp - 5) / 40;
  var tcol = s.temp > 35 ? LK.C.target : s.temp < 15 ? '#3b82f6' : LK.C.ok;
  ctx.fillStyle = tcol;
  var th2 = (ty1 - 6 - (ty0 + 6)) * tf;
  ctx.fillRect(tx + 3, ty1 - 6 - th2, 10, th2);
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText(s.temp + '\u00B0C', tx - 6, ty0 - 10);

  /* ---------- readouts ---------- */
  var rb = document.getElementById('rateBig');
  rb.textContent = Math.round(r) + ' bubbles/min';
  rb.style.color = r > 20 ? LK.C.ok : r > 0 ? LK.C.b : LK.C.target;
  var limiting = s.light <= 5 ? 'LIGHT' : s.co2 <= 5 ? 'CO\u2082' :
    (sat(s.light / 100, 3) < sat(s.co2 / 100, 3) ? 'LIGHT' : 'CO\u2082');
  document.getElementById('status').innerHTML =
    r <= 0 ? 'No photosynthesis — the plant only <b>respires</b> (uses O\u2082, releases CO\u2082).'
      : 'Photosynthesis running. Right now the limiting factor is <b>' + limiting + '</b>.' +
        (s.temp > 35 ? ' ⚠️ Enzymes are heat-stressed!' : '');
}

function bind(id, key, valId, suf) {
  LK.slider(id, function (v) {
    s[key] = v;
    document.getElementById(valId).textContent = v + suf;
  });
}
bind('light', 'light', 'lightv', '%');
bind('co2', 'co2', 'co2v', '%');
bind('temp', 'temp', 'tempv', '\u00B0C');
st.draw = draw;
