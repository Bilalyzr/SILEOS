'use strict';
var s = { a: 1, b: -2, c: -3 };
var st = LK.setupCanvas(document.getElementById('cv'));
var view = { scale: 30, cx: 0, cy: 0 };

function f(x) { return s.a * x * x + s.b * x + s.c; }

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  view.scale = Math.min(w / 21, h / 31);
  view.cx = w / 2; view.cy = h / 2;
  var G = LK.grid(st, view, { labelStep: 2 });

  // axis of symmetry
  var vx = -s.b / (2 * s.a);
  if (s.a !== 0) {
    ctx.strokeStyle = LK.C.b; ctx.lineWidth = 1.5; ctx.setLineDash([7, 6]);
    ctx.beginPath(); ctx.moveTo(G.X(vx), 0); ctx.lineTo(G.X(vx), h); ctx.stroke();
    ctx.setLineDash([]);
  }
  // the curve
  ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 3.5;
  ctx.beginPath();
  var first = true;
  for (var px = 0; px <= w; px += 2) {
    var x = (px - view.cx) / view.scale, y = f(x);
    var py = view.cy - y * view.scale;
    if (py < -2000 || py > h + 2000) { first = true; continue; }
    if (first) { ctx.moveTo(px, py); first = false; } else ctx.lineTo(px, py);
  }
  ctx.stroke();

  if (s.a !== 0) {
    var k = f(vx);
    // vertex
    dot(G.X(vx), G.Y(k), LK.C.b, 6);
    LK.chip(ctx, G.X(vx), G.Y(k) + 14, 'vertex (' + LK.fmt(vx, 2) + ', ' + LK.fmt(k, 2) + ')', LK.C.b);
    // roots
    var D = s.b * s.b - 4 * s.a * s.c;
    if (D >= 0) {
      var sq = Math.sqrt(D);
      [[(-s.b - sq) / (2 * s.a)], [(-s.b + sq) / (2 * s.a)]].forEach(function (r) {
        dot(G.X(r[0]), G.Y(0), LK.C.ok, 6);
        LK.chip(ctx, G.X(r[0]), G.Y(0) - 40, 'x = ' + LK.fmt(r[0], 2), LK.C.ok);
      });
    }
  }
}

function dot(px, py, color, r) {
  var ctx = st.ctx;
  ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(px, py, r + 3, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = color; ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.fill();
}

function eqHTML() {
  function term(v, body, first) {
    if (v === 0) return '';
    var sign = v < 0 ? ' \u2212 ' : (first ? '' : ' + ');
    var mag = Math.abs(v);
    var num = (body && mag === 1) ? '' : LK.coef(mag);
    return sign + '<span class="tok-' + body + '">' + num + body + '</span>';
  }
  var html = 'y =';
  var aT = term(s.a, 'm', true), bT = term(s.b, 'b', s.a === 0), cT = term(s.c, 't', s.a === 0 && s.b === 0);
  html += aT + bT + cT;
  if (!aT && !bT && !cT) html += ' 0';
  return html.replace('y =  <', 'y = <');
}

function upd() {
  document.getElementById('eq').innerHTML = eqHTML();
  var D = s.b * s.b - 4 * s.a * s.c;
  if (s.a === 0) {
    document.getElementById('vertex').innerHTML = 'a = 0, so this is a <b>straight line</b>, not a quadratic.';
    document.getElementById('disc').innerHTML = '';
    document.getElementById('roots').innerHTML = s.b === 0 ? '' : 'Root: x = ' + LK.fmt(-s.c / s.b, 2);
    return;
  }
  var vx = -s.b / (2 * s.a), k = f(vx);
  document.getElementById('vertex').innerHTML = 'Vertex: <b>(' + LK.fmt(vx, 2) + ', ' + LK.fmt(k, 2) + ')</b>' +
    ' — a ' + (s.a > 0 ? 'minimum (smile 😀)' : 'maximum (frown ☹️)');
  document.getElementById('disc').innerHTML = 'Discriminant D = b² − 4ac = <b>' + LK.fmt(D, 2) + '</b>';
  if (D > 1e-9) {
    var sq = Math.sqrt(D);
    document.getElementById('roots').innerHTML = 'Two real roots: x = <b>' + LK.fmt((-s.b - sq) / (2 * s.a), 2) + '</b> and <b>' + LK.fmt((-s.b + sq) / (2 * s.a), 2) + '</b>';
  } else if (D > -1e-9) {
    document.getElementById('roots').innerHTML = 'One repeated root: x = <b>' + LK.fmt(vx, 2) + '</b> (curve touches the axis)';
  } else {
    document.getElementById('roots').innerHTML = 'No real roots — the curve never meets the x-axis.';
  }
}

function bind(id, key, valId) {
  LK.slider(id, function (v) {
    s[key] = v;
    document.getElementById(valId).textContent = LK.coef(v);
    upd();
  });
}
bind('sa', 'a', 'sav'); bind('sb', 'b', 'sbv'); bind('sc', 'c', 'scv');
st.draw = draw; upd();
