'use strict';
var s = { T: 300, vfrac: 1 };
var N = 90, BASE = 150;      // px/s speed at 300 K
var st = LK.setupCanvas(document.getElementById('cv'));
var parts = [];

function boxRect() {
  var w = st.w, h = st.h;
  var bw = (w * 0.78) * s.vfrac, bh = h * 0.62;
  return { x0: 70, y0: (h - bh) / 2 + 10, x1: 70 + bw, y1: (h - bh) / 2 + 10 + bh };
}

function initParts() {
  parts = [];
  var b = boxRect();
  for (var i = 0; i < N; i++) {
    var v = BASE * Math.sqrt(s.T / 300);
    var a = Math.random() * Math.PI * 2;
    parts.push({
      x: b.x0 + 10 + Math.random() * (b.x1 - b.x0 - 20),
      y: b.y0 + 10 + Math.random() * (b.y1 - b.y0 - 20),
      vx: Math.cos(a) * v, vy: Math.sin(a) * v
    });
  }
}

function retune() {
  var v = BASE * Math.sqrt(s.T / 300);
  var sp = function (p) { return Math.hypot(p.vx, p.vy); };
  parts.forEach(function (p) {
    var k = v / (sp(p) || 1);
    p.vx *= k; p.vy *= k;
  });
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var b = boxRect();
  var dt = 1 / 60;
  var vTarget = BASE * Math.sqrt(s.T / 300);

  // heat tint
  var hot = LK.clamp((s.T - 300) / 300, -0.65, 1);
  ctx.fillStyle = hot > 0 ? 'rgba(239,68,68,' + hot * 0.10 + ')' : 'rgba(59,130,246,' + (-hot) * 0.14 + ')';
  ctx.fillRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0);

  // particles + wall collisions
  ctx.fillStyle = '#4338ca';
  parts.forEach(function (p) {
    p.x += p.vx * dt; p.y += p.vy * dt;
    if (p.x < b.x0 + 4) { p.x = b.x0 + 4; p.vx = Math.abs(p.vx); }
    if (p.x > b.x1 - 4) { p.x = b.x1 - 4; p.vx = -Math.abs(p.vx); }
    if (p.y < b.y0 + 4) { p.y = b.y0 + 4; p.vy = Math.abs(p.vy); }
    if (p.y > b.y1 - 4) { p.y = b.y1 - 4; p.vy = -Math.abs(p.vy); }
    ctx.beginPath(); ctx.arc(p.x, p.y, 3.4, 0, Math.PI * 2); ctx.fill();
  });

  // walls (left, top, bottom fixed; right = piston)
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.moveTo(b.x0, b.y0 - 2.5); ctx.lineTo(b.x0, b.y1 + 2.5); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(b.x0, b.y0); ctx.lineTo(b.x1, b.y0); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(b.x0, b.y1); ctx.lineTo(b.x1, b.y1); ctx.stroke();
  // piston
  ctx.fillStyle = '#94a3b8';
  ctx.fillRect(b.x1, b.y0 - 14, 14, (b.y1 - b.y0) + 28);
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2;
  ctx.strokeRect(b.x1, b.y0 - 14, 14, (b.y1 - b.y0) + 28);
  ctx.beginPath(); ctx.moveTo(b.x1 + 14, (b.y0 + b.y1) / 2); ctx.lineTo(b.x1 + 90, (b.y0 + b.y1) / 2); ctx.stroke();
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText('piston', b.x1 + 24, (b.y0 + b.y1) / 2 - 12);
  ctx.fillText((s.vfrac * 10).toFixed(1) + ' L', b.x0 + 8, b.y1 + 24);

  // Bunsen-ish heater glow under box
  if (s.T > 310) {
    var gl = ctx.createRadialGradient(w * 0.4, b.y1 + 40, 5, w * 0.4, b.y1 + 40, 130);
    gl.addColorStop(0, 'rgba(249,115,22,' + LK.clamp((s.T - 300) / 500, 0, .55) + ')');
    gl.addColorStop(1, 'rgba(249,115,22,0)');
    ctx.fillStyle = gl;
    ctx.fillRect(w * 0.4 - 140, b.y1, 280, 90);
  }

  // pressure gauge
  var P = 101.3 * (s.T / 300) / s.vfrac;
  var gx = w - 108, gy = 96, r = 62;
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 8;
  ctx.beginPath(); ctx.arc(gx, gy, r, Math.PI * 0.75, Math.PI * 2.25); ctx.stroke();
  // ticks
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 2;
  for (var i = 0; i <= 8; i++) {
    var a = Math.PI * 0.75 + (i / 8) * Math.PI * 1.5;
    ctx.beginPath();
    ctx.moveTo(gx + Math.cos(a) * (r - 10), gy + Math.sin(a) * (r - 10));
    ctx.lineTo(gx + Math.cos(a) * (r + 10), gy + Math.sin(a) * (r + 10));
    ctx.stroke();
  }
  var frac = LK.clamp(P / 450, 0, 1);
  var na = Math.PI * 0.75 + frac * Math.PI * 1.5;
  ctx.strokeStyle = P > 300 ? LK.C.target : LK.C.ok; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.moveTo(gx, gy);
  ctx.lineTo(gx + Math.cos(na) * (r - 16), gy + Math.sin(na) * (r - 16)); ctx.stroke();
  ctx.fillStyle = LK.C.ink; ctx.beginPath(); ctx.arc(gx, gy, 6, 0, Math.PI * 2); ctx.fill();
  ctx.font = 'bold 15px system-ui, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(P.toFixed(0) + ' kPa', gx, gy + 30);
  ctx.textAlign = 'start';
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText('pressure gauge', gx - 44, gy - r - 10);
}

function upd() {
  var P = 101.3 * (s.T / 300) / s.vfrac;
  var V = s.vfrac * 10;
  document.getElementById('rP').innerHTML = 'Pressure P \u2248 <b>' + P.toFixed(0) + ' kPa</b>';
  document.getElementById('rV').innerHTML = 'Volume V = <b>' + V.toFixed(1) + ' L</b> &nbsp;·&nbsp; T = <b>' + s.T + ' K</b>';
  document.getElementById('rConst').innerHTML = 'PV / T = <b>' + ((P * V) / s.T).toFixed(2) + '</b> — constant! (PV = nRT \u2713)';
}

LK.slider('temp', function (v) { s.T = v; document.getElementById('tempv').textContent = v + ' K'; retune(); upd(); });
LK.slider('vol', function (v) {
  s.vfrac = v / 100;
  document.getElementById('volv').textContent = v + ' %';
  var b = boxRect();
  parts.forEach(function (p) {
    p.x = Math.min(p.x, b.x1 - 4);
    p.y = LK.clamp(p.y, b.y0 + 4, b.y1 - 4);
  });
  upd();
});

initParts();
upd();
st.draw = draw;
