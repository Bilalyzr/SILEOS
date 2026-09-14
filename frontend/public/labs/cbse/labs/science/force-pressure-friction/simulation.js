'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, wt: 500, foot: 0, push: 0, surf: 0, sink: 0, blockX: 0, blockV: 0, t: 0 };

var FEET = [
  { name: 'elephant foot', A: 0.07, w: 130 },
  { name: 'ski', A: 0.30, w: 250 },
  { name: 'stiletto heel', A: 0.0005, w: 14 }
];
var SURFS = [
  { name: 'ice', muS: 0.12, muK: 0.06, color: '#dbeafe', grip: 'slippery' },
  { name: 'wood floor', muS: 0.45, muK: 0.3, color: '#f5d0a9', grip: 'moderate' },
  { name: 'carpet', muS: 0.85, muK: 0.6, color: '#e7d3b8', grip: 'rough' }
];

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  s.t += 0.016;
  if (s.mode === 0) drawPressure(ctx, w, h);
  else drawFriction(ctx, w, h);
}

/* ---------------- pressure ---------------- */
function drawPressure(ctx, w, h) {
  var foot = FEET[s.foot];
  var P = s.wt / foot.A / 1000;   // kPa
  var target = LK.clamp(Math.log10(P + 1) / 3.4, 0.05, 1); // log scale for sink depth
  s.sink += (target - s.sink) * 0.08;

  // sand pit
  var gy = h * 0.72;
  ctx.fillStyle = '#e8d5ae';
  ctx.fillRect(0, gy, w, h - gy);
  ctx.strokeStyle = '#c9ae7d'; ctx.lineWidth = 2;
  for (var g = 0; g < w; g += 22) {
    ctx.beginPath(); ctx.moveTo(g, gy + 8); ctx.lineTo(g + 9, gy + 14); ctx.stroke();
  }
  // object
  var cx = w / 2;
  var sinkPx = s.sink * 70;
  ctx.save();
  ctx.translate(cx, gy - 90 + sinkPx);
  ctx.font = '56px serif'; ctx.textAlign = 'center';
  ctx.fillText(s.foot === 0 ? '🐘' : s.foot === 1 ? '⛷️' : '👠', 0, 40);
  ctx.textAlign = 'start';
  // contact area bar
  ctx.fillStyle = '#78350f';
  var bw = foot.w;
  ctx.fillRect(-bw / 2, 88, bw, 8);
  ctx.restore();

  // sink depth marker
  ctx.strokeStyle = LK.C.target; ctx.lineWidth = 2; ctx.setLineDash([5, 5]);
  ctx.beginPath(); ctx.moveTo(cx + 110, gy); ctx.lineTo(cx + 110, gy + sinkPx); ctx.stroke();
  ctx.setLineDash([]);
  if (sinkPx > 4) {
    ctx.fillStyle = LK.C.target; ctx.font = '600 13px system-ui, sans-serif';
    ctx.fillText('sinks ' + Math.round(sinkPx) + ' px', cx + 120, gy + sinkPx / 2);
  }
  document.getElementById('pRead').innerHTML =
    'Force F = <b>' + s.wt + ' N</b> over area A = <b>' + foot.A + ' m²</b> (' + foot.name + ')<br>' +
    'Pressure P = F/A = <b>' + P.toFixed(0) + ' kPa</b> — ' +
    (P > 800 ? 'ouch! concentrates enormous force 🩸' : P > 50 ? 'firm but safe' : 'spreads the load — floats on sand');
}

/* ---------------- friction ---------------- */
function drawFriction(ctx, w, h) {
  var surf = SURFS[s.surf];
  var m = 10;               // kg block
  var g = 10, N = m * g;    // normal force
  var fS = surf.muS * N, fK = surf.muK * N;
  var groundY = h * 0.68;
  // reset button guard: keep block on screen
  if (s.blockX > w - 240 && s.blockV > 0) { s.blockX = w - 240; s.blockV = 0; }

  // surface
  ctx.fillStyle = surf.color;
  ctx.fillRect(0, groundY, w, h - groundY);
  // texture
  ctx.strokeStyle = 'rgba(71,85,105,.35)'; ctx.lineWidth = 1.5;
  var gap = s.surf === 2 ? 8 : s.surf === 1 ? 18 : 42;
  for (var x = 0; x < w; x += gap) {
    ctx.beginPath(); ctx.moveTo(x, groundY + 6); ctx.lineTo(x + 6, groundY + 13); ctx.stroke();
  }
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(0, groundY); ctx.lineTo(w, groundY); ctx.stroke();

  // physics: push vs friction
  var push = s.push * 2;
  var moving = s.blockV > 0.01;
  var fric = moving ? fK : Math.min(push, fS);
  var a = (push - fric) / m * 0.05;
  if (push <= 0.01) { s.blockV *= 0.9; fric = 0; }
  else if (!moving && push > fS) { s.blockV = 0.4; }
  else if (moving) { s.blockV = Math.max(0, s.blockV + a * 0.2); }
  s.blockX += s.blockV * 0.4;
  if (s.blockX < 40) { s.blockX = 40; s.blockV = 0; }

  // block
  var bx = 40 + s.blockX - 40;
  var bs = 74;
  ctx.fillStyle = '#fb923c';
  LK.roundRect(ctx, bx, groundY - bs, bs, bs, 8); ctx.fill();
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5; ctx.stroke();
  ctx.fillStyle = '#7c2d12'; ctx.font = '600 14px system-ui, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('10 kg', bx + bs / 2, groundY - bs / 2 + 5);
  ctx.textAlign = 'start';

  // arrows: push (blue) & friction (red)
  ctx.strokeStyle = '#2563eb'; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(bx + bs / 2, groundY - bs - 16); ctx.lineTo(bx + bs / 2, groundY - bs - 16 - Math.min(70, push * 0.9)); ctx.stroke();
  LK.arrow(ctx, bx + bs / 2, groundY - bs - 16 - Math.min(70, push * 0.9), -Math.PI / 2, '#2563eb', 11);
  if (fric > 0.5) {
    ctx.strokeStyle = LK.C.target;
    ctx.beginPath(); ctx.moveTo(bx + bs / 2, groundY - bs - 16); ctx.lineTo(bx + bs / 2 - Math.min(70, fric * 0.9), groundY - bs - 16); ctx.stroke();
    LK.arrow(ctx, bx + bs / 2 - Math.min(70, fric * 0.9), groundY - bs - 16, Math.PI, LK.C.target, 11);
    ctx.fillStyle = LK.C.target; ctx.font = '600 12.5px system-ui, sans-serif';
    ctx.fillText('friction ' + fric.toFixed(0) + ' N', bx + bs / 2 - 80, groundY - bs - 26);
  }

  // motion streaks
  if (s.blockV > 0.5) {
    ctx.strokeStyle = 'rgba(37,99,235,.5)'; ctx.lineWidth = 2;
    for (var k = 0; k < 3; k++) {
      var sx0 = bx - 14 - k * 16;
      ctx.beginPath(); ctx.moveTo(sx0, groundY - 18 - k * 14); ctx.lineTo(sx0 - 16, groundY - 18 - k * 14); ctx.stroke();
    }
  }
  document.getElementById('fRead').innerHTML =
    surf.name + ': μ<sub>s</sub> = ' + surf.muS + ', μ<sub>k</sub> = ' + surf.muK + ' (' + surf.grip + ')<br>' +
    'Max static friction = ' + fS.toFixed(0) + ' N — ' +
    (s.push * 2 > fS ? 'block is <b>SLIDING</b> at v = ' + s.blockV.toFixed(1) + ' (arb)'
      : 'block holds still until you push past it') +
    '<br>💡 Push needs > ' + fS.toFixed(0) + ' N to start movement on ' + surf.name;
}

/* ---------------- wiring ---------------- */
LK.segment('modeSeg', function (i) {
  s.mode = i;
  document.getElementById('pCard').classList.toggle('hidden', i !== 0);
  document.getElementById('fCard').classList.toggle('hidden', i !== 1);
});
LK.segment('footSeg', function (i) { s.foot = i; });
LK.segment('surfSeg', function (i) { s.surf = i; s.blockX = 0; s.blockV = 0; });
LK.slider('wt', function (v) { s.wt = v; document.getElementById('wtv').textContent = v + ' N'; });
LK.slider('push', function (v) {
  s.push = v;
  document.getElementById('pushv').textContent = (v * 2) + ' N';
  if (v === 0) { s.blockV = 0; }
});

st.draw = draw;
