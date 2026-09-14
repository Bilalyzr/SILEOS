'use strict';
var s = { mode: 'mirror', n: 1.5, src: null };
var st = LK.setupCanvas(document.getElementById('cv'));

function O() { return { x: st.w / 2, y: st.h / 2 }; }

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var o = O();
  if (!s.src) s.src = { x: o.x - 220, y: o.y - 190 };
  var S = s.src;
  var refr = s.mode === 'refract';

  // media
  if (refr) {
    ctx.fillStyle = 'rgba(13,148,136,.10)';
    ctx.fillRect(0, o.y, w, h - o.y);
    ctx.strokeStyle = LK.C.m; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(0, o.y); ctx.lineTo(w, o.y); ctx.stroke();
    ctx.fillStyle = LK.C.sub; ctx.font = '13px system-ui, sans-serif';
    ctx.fillText('air  (n\u2081 = 1.0)', 16, o.y - 12);
    ctx.fillText('glass  (n\u2082 = ' + s.n.toFixed(2) + ')', 16, o.y + 24);
  } else {
    // mirror with hatching
    ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(w * 0.08, o.y); ctx.lineTo(w * 0.92, o.y); ctx.stroke();
    ctx.lineWidth = 1.5;
    for (var hx = w * 0.08; hx < w * 0.92; hx += 16) {
      ctx.beginPath(); ctx.moveTo(hx, o.y + 3); ctx.lineTo(hx + 10, o.y + 14); ctx.stroke();
    }
    ctx.fillStyle = LK.C.sub; ctx.font = '13px system-ui, sans-serif';
    ctx.fillText('plane mirror (front-silvered)', w * 0.08, o.y + 32);
  }

  // normal
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 1.5; ctx.setLineDash([7, 7]);
  ctx.beginPath(); ctx.moveTo(o.x, o.y - 190); ctx.lineTo(o.x, o.y + 190); ctx.stroke();
  ctx.setLineDash([]);

  var dx = S.x - o.x, dy = S.y - o.y;
  var dist = Math.hypot(dx, dy);
  var sinT = Math.abs(dx) / dist;
  var cosT = -dy / dist;                 // above interface: dy negative -> positive cos
  var theta1 = Math.atan2(Math.abs(dx), -dy) * 180 / Math.PI;
  var sgn = dx >= 0 ? 1 : -1;            // source on right side of normal?

  // incident ray (from torch to O)
  ray(S, o, LK.C.brand, 3.5, true);
  torch(S);

  // normal-angle arc
  arcDeg(o, sgn, theta1);

  if (refr) {
    var sin2 = sinT / s.n;
    var theta2 = Math.asin(Math.min(1, sin2)) * 180 / Math.PI;
    var L2 = 300;
    var end2 = { x: o.x + sgn * Math.sin(theta2 * Math.PI / 180) * L2, y: o.y + Math.cos(theta2 * Math.PI / 180) * L2 };
    // weak partial reflection
    var refl = { x: o.x - sgn * Math.abs(dx) / dist * 220, y: o.y + (-dy) / dist * -220 };
    ray(o, refl, 'rgba(79,70,229,.35)', 2, true);
    ray(o, end2, LK.C.ok, 3.5, true);
    ctx.fillStyle = LK.C.sub; ctx.font = '600 15px system-ui, sans-serif';
    ctx.fillText('\u03B81 = ' + theta1.toFixed(1) + '\u00B0', o.x + sgn * 24 + (sgn < 0 ? -70 : 0), o.y - 40);
    ctx.fillText('\u03B82 = ' + theta2.toFixed(1) + '\u00B0', end2.x + (sgn > 0 ? -46 : -46), end2.y - 12);
    document.getElementById('angles').innerHTML =
      'Angle of incidence \u03B81 = <b>' + theta1.toFixed(1) + '\u00B0</b><br>Angle of refraction \u03B82 = <b>' + theta2.toFixed(1) + '\u00B0</b>';
    document.getElementById('law').innerHTML =
      'Snell: n\u2081 sin\u03B81 = n\u2082 sin\u03B82 \u2192 <b>1.0\u00D7' + sinT.toFixed(3) + ' = ' + s.n.toFixed(2) + '\u00D7' + sin2.toFixed(3) + '</b> \u2713';
  } else {
    var L2r = 280;
    var endR = { x: o.x - sgn * sinT * L2r, y: o.y + cosT * L2r };
    ray(o, endR, LK.C.ok, 3.5, true);
    ctx.fillStyle = LK.C.sub; ctx.font = '600 15px system-ui, sans-serif';
    ctx.fillText('\u03B8i = ' + theta1.toFixed(1) + '\u00B0', o.x + sgn * 26 + (sgn < 0 ? -60 : 0), o.y - 40);
    ctx.fillText('\u03B8r = ' + theta1.toFixed(1) + '\u00B0', endR.x + (sgn > 0 ? -60 : 6), endR.y / 1.35);
    document.getElementById('angles').innerHTML =
      'Angle of incidence \u03B8i = <b>' + theta1.toFixed(1) + '\u00B0</b><br>Angle of reflection \u03B8r = <b>' + theta1.toFixed(1) + '\u00B0</b>';
    document.getElementById('law').innerHTML = 'Law of reflection: <b>\u03B8i = \u03B8r</b> \u2713 and the ray, normal &amp; reflected ray lie in one plane.';
  }
}

function ray(a, b, color, width, arrowed) {
  var ctx = st.ctx;
  ctx.strokeStyle = color; ctx.lineWidth = width;
  ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
  if (arrowed) {
    var ang = Math.atan2(b.y - a.y, b.x - a.x);
    LK.arrow(ctx, a.x + (b.x - a.x) * 0.55, a.y + (b.y - a.y) * 0.55, ang, color, 13);
  }
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(b.x, b.y, 4.5, 0, Math.PI * 2); ctx.fill();
}

function torch(p) {
  var ctx = st.ctx;
  ctx.fillStyle = LK.C.b;
  ctx.beginPath(); ctx.arc(p.x, p.y, 15, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 13px system-ui, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('\u{1F526}', p.x, p.y + 5);
  ctx.textAlign = 'start';
}

function arcDeg(o, sgn, deg) {
  var ctx = st.ctx;
  var a0 = -Math.PI / 2; // normal direction (up)
  var a1 = a0 + sgn * deg * Math.PI / 180;
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(o.x, o.y, 58, Math.min(a0, a1), Math.max(a0, a1)); ctx.stroke();
}

LK.segment('modeSeg', function (i) {
  s.mode = i === 0 ? 'mirror' : 'refract';
  document.getElementById('nCard').classList.toggle('hidden', s.mode === 'mirror');
});
LK.slider('nIdx', function (v) {
  s.n = v;
  document.getElementById('nIdxv').textContent = v.toFixed(2);
  document.getElementById('lightSpeed').innerHTML =
    'Light speed in glass = c/n = <b>' + (3e8 / v / 1e8).toFixed(2) + '\u00D710\u2078 m/s</b>';
});
LK.pointer(st.canvas, {
  down: function (p) {
    if (Math.hypot(p.x - s.src.x, p.y - s.src.y) < 40) drag = true;
  },
  move: function (p, d) {
    if (d && drag) {
      var o = O();
      s.src.x = LK.clamp(p.x, 30, st.w - 30);
      s.src.y = LK.clamp(p.y, 30, o.y - 24);
    }
  },
  up: function () { drag = false; }
});
var drag = false;

st.draw = draw;
