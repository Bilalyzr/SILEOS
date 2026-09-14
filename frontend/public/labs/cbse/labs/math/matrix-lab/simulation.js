'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { a: 1, b: 0, c: 0, d: 1 };

/* smiley as a list of primitives: circles and segments in world coords */
function smiley() {
  var parts = [];
  parts.push({ type: 'c', x: 0, y: 0, r: 1.0, main: true });
  parts.push({ type: 'c', x: -0.35, y: 0.3, r: 0.13 });
  parts.push({ type: 'c', x: 0.35, y: 0.3, r: 0.13 });
  parts.push({ type: 'c', x: 0, y: -0.15, r: 0.12 });
  // smile arc approximated by segments
  for (var i = 0; i <= 8; i++) {
    var a = Math.PI * (0.15 + 0.7 * i / 8);
    parts.push({ type: 'p', x: Math.cos(a) * 0.5, y: -0.25 - Math.sin(a) * -0.35 * 0.5 - 0.1 });
  }
  return parts;
}
function apply(p) {
  return { x: s.a * p.x + s.b * p.y, y: s.c * p.x + s.d * p.y };
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var scale = Math.min(w, h) / 6.2;
  var cx = w / 2, cy = h / 2;
  function P(p) { return { x: cx + p.x * scale, y: cy - p.y * scale }; }

  // grid
  ctx.strokeStyle = '#f1f3f6'; ctx.lineWidth = 1;
  for (var g = -5; g <= 5; g++) {
    ctx.beginPath(); ctx.moveTo(cx + g * scale, 0); ctx.lineTo(cx + g * scale, h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, cy + g * scale); ctx.lineTo(w, cy + g * scale); ctx.stroke();
  }
  ctx.strokeStyle = '#e4e7ec';
  ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(w, cy); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, h); ctx.stroke();

  // transformed basis vectors
  function vec(p, color, label) {
    var q = P({ x: 0, y: 0 }), r = P(p);
    ctx.strokeStyle = color; ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.moveTo(q.x, q.y); ctx.lineTo(r.x, r.y); ctx.stroke();
    LK.arrow(ctx, r.x, r.y, Math.atan2(r.y - q.y, r.x - q.x), color, 11);
    ctx.fillStyle = color; ctx.font = '600 13px Inter, sans-serif';
    ctx.fillText(label, r.x + 8, r.y - 6);
  }
  var e1 = apply({ x: 1, y: 0 }), e2 = apply({ x: 0, y: 1 });
  vec(e1, '#b45309', 'M·(1,0)');
  vec(e2, '#0369a1', 'M·(0,1)');

  // original (grey)
  function paint(parts, color, width, alpha) {
    ctx.globalAlpha = alpha;
    parts.forEach(function (p) {
      if (p.type === 'c') {
        var q = P(p);
        ctx.beginPath(); ctx.arc(q.x, q.y, p.r * scale, 0, Math.PI * 2);
        if (p.main) { ctx.fillStyle = color + '22'; ctx.fill(); }
        ctx.strokeStyle = color; ctx.lineWidth = width; ctx.stroke();
      } else if (p.type === 'p') {
        var q2 = P(p);
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(q2.x, q2.y, 3, 0, Math.PI * 2); ctx.fill();
      }
    });
    ctx.globalAlpha = 1;
  }
  // smile polyline for both
  function smile(points, color, width, alpha) {
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.beginPath();
    points.forEach(function (p, i) {
      var q = P(p);
      i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y);
    });
    ctx.stroke(); ctx.globalAlpha = 1;
  }
  var base = smiley();
  var smilePts = base.filter(p => p.type === 'p');
  paint(base.filter(p => p.type !== 'p'), '#98a2b3', 2, 0.55);
  smile(smilePts, '#98a2b3', 2, 0.55);
  var mapped = base.map(function (p) {
    var q = apply(p);
    var o = { type: p.type, x: q.x, y: q.y, r: p.r * Math.sqrt(Math.abs(s.a * s.d - s.b * s.c)) };
    return o;
  });
  paint(mapped.filter(p => p.type !== 'p'), '#f97316', 3.5, 1);
  smile(mapped.filter(p => p.type === 'p'), '#f97316', 3.5, 1);

  var det = s.a * s.d - s.b * s.c;
  document.getElementById('det').innerHTML = 'det M = ad − bc = <b>' + det.toFixed(2) + '</b>' +
    (Math.abs(det) < 0.05 ? ' ⚠️ space collapses to a line — NOT invertible!' : det < 0 ? ' (orientation flipped 🪞)' : '');
  var what = Math.abs(det - 1) < 0.05 && Math.abs(s.b) < 0.05 && Math.abs(s.c) < 0.05 && s.a > 0.9 && s.d > 0.9 ? 'identity — nothing moves'
    : Math.abs(s.a * s.d - s.b * s.c - 1) < 0.08 && Math.abs(s.a - s.d) < 0.08 && Math.abs(s.b + s.c) < 0.08 ? (s.b < 0 ? 'pure ROTATION' : 'reflection-ish rotation')
    : Math.abs(det) < 0.05 ? 'degenerate (a line!)'
    : det < 0 ? 'reflection / flip involved'
    : (Math.abs(s.c) < 0.05 && Math.abs(s.b) > 0.05) || (Math.abs(s.b) < 0.05 && Math.abs(s.c) > 0.05) ? 'shear — a leaning slide'
    : Math.abs(det) > 1.5 ? 'scaling up (area ×' + det.toFixed(1) + ')'
    : 'a custom linear map — area ×' + det.toFixed(2);
  document.getElementById('meaning').innerHTML = 'Effect: <b>' + what + '</b>';
}

function setM(a, b, c, d) {
  s.a = a; s.b = b; s.c = c; s.d = d;
  [['ma', a, 'mav'], ['mb', b, 'mbv'], ['mc', c, 'mcv'], ['md', d, 'mdv']].forEach(function (t) {
    document.getElementById(t[0]).value = a === t[1] ? t[1] : t[1];
    document.getElementById(t[0]).value = t[1];
    document.getElementById(t[2]).textContent = Number(t[1]).toFixed(1);
  });
  draw();
}
['ma', 'mb', 'mc', 'md'].forEach(function (id, i) {
  var key = ['a', 'b', 'c', 'd'][i];
  LK.slider(id, function (v) {
    s[key] = v;
    document.getElementById(id + 'v').textContent = v.toFixed(1);
    draw();
  });
});
LK.segment('preSeg', function (i) {
  var P2 = [[1, 0, 0, 1], [0, 1, -1, 0], [1, 0, 0, -1], [1, 0.8, 0, 1], [2, 0, 0, 2]][i];
  setM(P2[0], P2[1], P2[2], P2[3]);
});
st.draw = draw; draw();
