'use strict';
var R_BULB = 6; // ohms per bulb
var s = { mode: 'series', V: 6, closed: true };
var st = LK.setupCanvas(document.getElementById('cv'));

// ---- circuit geometry (built per frame in css px) ----
var paths = [];        // array of polylines [{pts:[{x,y}], len}]
var bulbs = [];        // [{x,y,bright}]
var switchGeo = null;  // {x1,x2,y,closed}
var batteryGeo = null; // {x,y1,y2}
var lastT = 0, flow = 0; // flow: electron phase (px along path)

function Req() {
  if (s.mode === 'one') return R_BULB;
  if (s.mode === 'series') return 2 * R_BULB;
  return R_BULB / 2;
}
function current() { return s.closed ? s.V / Req() : 0; }

function buildLayout() {
  var w = st.w, h = st.h;
  var mx = Math.min(w * 0.72, 640), my = Math.min(h * 0.74, 480);
  var x0 = (w - mx) / 2, x1 = x0 + mx, y0 = (h - my) / 2 + 10, y1 = y0 + my;
  paths = []; bulbs = []; switchGeo = null; batteryGeo = null;

  var pl = function (pts) {
    var len = 0;
    for (var i = 1; i < pts.length; i++) len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    paths.push({ pts: pts, len: len });
  };

  var batY1 = y0 + my * 0.35, batY2 = y0 + my * 0.55;
  batteryGeo = { x: x0, y1: batY1, y2: batY2 };
  var swX1 = x0 + mx * 0.38, swX2 = x0 + mx * 0.52;
  switchGeo = { x1: swX1, x2: swX2, y: y1 };

  pl([{ x: x0, y: batY1 }, { x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 },
      { x: swX2, y: y1 }]);
  pl([{ x: swX1, y: y1 }, { x: x0, y: y1 }, { x: x0, y: batY2 }]);

  if (s.mode === 'one') {
    bulbs.push({ x: (x0 + x1) / 2, y: y0, bright: 0 });
  } else if (s.mode === 'series') {
    bulbs.push({ x: x0 + mx * 0.35, y: y0, bright: 0 });
    bulbs.push({ x: x0 + mx * 0.72, y: y0, bright: 0 });
  } else {
    var b1 = x0 + mx * 0.55, b2 = x0 + mx * 0.85;
    pl([{ x: b1, y: y0 }, { x: b1, y: y1 }]);
    pl([{ x: b2, y: y0 }, { x: b2, y: y1 }]);
    bulbs.push({ x: b1, y: (y0 + y1) / 2, bright: 0 });
    bulbs.push({ x: b2, y: (y0 + y1) / 2, bright: 0 });
  }
}

function pointOn(path, d) {
  var pts = path.pts;
  d = ((d % path.len) + path.len) % path.len;
  for (var i = 1; i < pts.length; i++) {
    var seg = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    if (d <= seg) {
      var t = d / seg;
      return { x: pts[i - 1].x + (pts[i].x - pts[i - 1].x) * t, y: pts[i - 1].y + (pts[i].y - pts[i - 1].y) * t };
    }
    d -= seg;
  }
  return pts[pts.length - 1];
}

var dots = [];
for (var i = 0; i < 46; i++) dots.push(Math.random());

function draw(now) {
  var dt = Math.min(0.05, (now - lastT) / 1000 || 0.016);
  lastT = now;
  buildLayout();
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);

  var I = current();
  var bulbCurrent = s.mode === 'series' ? I : I / bulbs.length;

  // glow + brightness first (under wires)
  bulbs.forEach(function (b) {
    var P = bulbCurrent * bulbCurrent * R_BULB;
    b.bright = s.closed ? LK.clamp(P / 24, 0, 1) : 0;
    if (b.bright > 0.02) {
      var g = ctx.createRadialGradient(b.x, b.y, 4, b.x, b.y, 26 + 55 * b.bright);
      g.addColorStop(0, 'rgba(253,224,71,' + 0.85 * b.bright + ')');
      g.addColorStop(1, 'rgba(253,224,71,0)');
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(b.x, b.y, 26 + 55 * b.bright, 0, Math.PI * 2); ctx.fill();
    }
  });

  // wires
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 3; ctx.lineJoin = 'round';
  paths.forEach(function (p) {
    ctx.beginPath();
    p.pts.forEach(function (pt, i) { i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y); });
    ctx.stroke();
  });

  // battery symbol
  var ba = batteryGeo, bw2 = 20;
  ctx.lineWidth = 4; ctx.strokeStyle = LK.C.ink;
  ctx.beginPath(); ctx.moveTo(ba.x - bw2, ba.y1 + 8); ctx.lineTo(ba.x + bw2, ba.y1 + 8); ctx.stroke();
  ctx.lineWidth = 7;
  ctx.beginPath(); ctx.moveTo(ba.x - bw2 / 2, ba.y2 - 8); ctx.lineTo(ba.x + bw2 / 2, ba.y2 - 8); ctx.stroke();
  ctx.fillStyle = LK.C.sub; ctx.font = 'bold 13px system-ui, sans-serif';
  ctx.fillText('+', ba.x + 28, ba.y1 + 14);
  ctx.fillText('\u2212', ba.x + 28, ba.y2 - 2);
  ctx.textAlign = 'center';
  ctx.fillText(s.V.toFixed(1) + ' V', ba.x - 40, (ba.y1 + ba.y2) / 2 + 4);
  ctx.textAlign = 'start';

  // switch
  var sw = switchGeo;
  ctx.fillStyle = LK.C.ink;
  ctx.beginPath(); ctx.arc(sw.x1, sw.y, 4.5, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(sw.x2, sw.y, 4.5, 0, Math.PI * 2); ctx.fill();
  ctx.lineWidth = 3.5;
  ctx.beginPath(); ctx.moveTo(sw.x1, sw.y);
  if (s.closed) ctx.lineTo(sw.x2 - 3, sw.y);
  else ctx.lineTo(sw.x1 + (sw.x2 - sw.x1) * 0.75, sw.y - 34);
  ctx.stroke();

  // bulbs
  bulbs.forEach(function (b) {
    ctx.fillStyle = b.bright > 0.02 ? '#fef9c3' : '#fff';
    ctx.beginPath(); ctx.arc(b.x, b.y, 17, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5; ctx.stroke();
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(b.x - 7, b.y - 6); ctx.lineTo(b.x + 7, b.y + 6);
    ctx.moveTo(b.x - 7, b.y + 6); ctx.lineTo(b.x + 7, b.y - 6);
    ctx.stroke();
    LK.chip(ctx, b.x, b.y + 40, Math.round(b.bright * 100) + '% bright', b.bright > 0.02 ? LK.C.b : '#94a3b8');
  });

  // moving current carriers
  if (s.closed && I > 0) {
    flow += I * 26 * dt;
    var ctxA = ctx;
    ctxA.fillStyle = '#2563eb';
    var perPath = Math.ceil(dots.length / paths.length);
    paths.forEach(function (p, pi) {
      for (var k = 0; k < perPath; k++) {
        var idx = pi * perPath + k;
        if (idx >= dots.length) break;
        var pos = pointOn(p, dots[idx] * p.len + flow);
        ctxA.beginPath(); ctxA.arc(pos.x, pos.y, 3.4, 0, Math.PI * 2); ctxA.fill();
      }
    });
  }

  // current label
  ctx.fillStyle = '#2563eb'; ctx.font = 'bold 14px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(s.closed ? 'current I = ' + I.toFixed(2) + ' A' : 'switch OPEN — no current', w / 2, h - 16);
  ctx.textAlign = 'start';
}

function upd() {
  var I = current();
  var perBulb = (s.mode === 'series' ? I : I / bulbs.length || 0);
  var P = s.closed ? perBulb * perBulb * R_BULB : 0;
  document.getElementById('req').innerHTML = 'Total resistance R = <b>' + LK.fmt(Req(), 1) + ' \u03A9</b>';
  document.getElementById('cur').innerHTML = 'Current I = V/R = <b>' + I.toFixed(2) + ' A</b>';
  document.getElementById('pow').innerHTML = 'Power per bulb P = I\u00B2R = <b>' + P.toFixed(1) + ' W</b>';
}

LK.segment('modeSeg', function (i) { s.mode = ['one', 'series', 'parallel'][i]; upd(); });
LK.slider('volt', function (v) {
  s.V = v;
  document.getElementById('voltv').textContent = v.toFixed(1) + ' V';
  upd();
});
LK.check('switchChk', function (on) { s.closed = on; upd(); });
LK.pointer(st.canvas, {
  down: function (p) {
    var sw = switchGeo;
    if (sw && Math.hypot(p.x - (sw.x1 + sw.x2) / 2, p.y - sw.y) < 46) {
      s.closed = !s.closed;
      document.getElementById('switchChk').checked = s.closed;
      upd();
    }
  }
});

st.draw = draw; upd();
