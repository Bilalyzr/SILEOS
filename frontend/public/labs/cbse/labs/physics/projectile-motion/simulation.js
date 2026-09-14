'use strict';
var s = { ang: 45, u: 30, g: 9.8 };
var st = LK.setupCanvas(document.getElementById('cv'));
var flight = null;      // {t, x, y} live state
var trails = [];        // finished paths [{pts:[[x,y]...], g, hitRange}]

function predict() {
  var th = s.ang * Math.PI / 180, u = s.u, g = s.g;
  return {
    R: u * u * Math.sin(2 * th) / g,
    H: u * u * Math.sin(th) * Math.sin(th) / (2 * g),
    T: 2 * u * Math.sin(th) / g
  };
}

function pathFor(ang, u, g) {
  var th = ang * Math.PI / 180, pts = [];
  var T = 2 * u * Math.sin(th) / g;
  for (var t = 0; t <= T; t += T / 120) {
    pts.push([u * Math.cos(th) * t, u * Math.sin(th) * t - 0.5 * g * t * t]);
  }
  return pts;
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var pr = predict();
  var worldW = pr.R, worldH = pr.H;
  trails.forEach(function (tr) {
    worldW = Math.max(worldW, tr.hitRange);
    worldH = Math.max(worldH, tr.h);
  });
  worldW *= 1.1; worldH *= 1.25;
  var ppm = Math.min((w - 110) / worldW, (h - 100) / Math.max(worldH, 1));
  var X = function (x) { return 70 + x * ppm; };
  var Y = function (y) { return h - 60 - y * ppm; };

  // ground + grid
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(30, Y(0)); ctx.lineTo(w - 20, Y(0)); ctx.stroke();
  ctx.strokeStyle = LK.C.grid2; ctx.lineWidth = 1;
  for (var gm = 0; gm <= worldW; gm += nice(worldW / 8)) {
    ctx.beginPath(); ctx.moveTo(X(gm), Y(0)); ctx.lineTo(X(gm), Y(0) + 8); ctx.stroke();
    ctx.fillStyle = LK.C.sub; ctx.font = '11.5px system-ui, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(String(Math.round(gm)) + ' m', X(gm), Y(0) + 22);
  }
  ctx.textAlign = 'start';

  // old trails
  trails.forEach(function (tr) {
    ctx.strokeStyle = 'rgba(79,70,229,.30)'; ctx.lineWidth = 2;
    ctx.beginPath();
    tr.pts.forEach(function (p, i) { i ? ctx.lineTo(X(p[0]), Y(p[1])) : ctx.moveTo(X(p[0]), Y(p[1])); });
    ctx.stroke();
  });

  // current trajectory
  var cur = pathFor(s.ang, s.u, s.g);
  ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 2.5; ctx.setLineDash([6, 6]);
  ctx.beginPath();
  cur.forEach(function (p, i) { i ? ctx.lineTo(X(p[0]), Y(p[1])) : ctx.moveTo(X(p[0]), Y(p[1])); });
  ctx.stroke();
  ctx.setLineDash([]);

  // launcher
  ctx.save();
  ctx.translate(X(0), Y(0));
  ctx.rotate(-s.ang * Math.PI / 180);
  ctx.fillStyle = LK.C.ink;
  ctx.fillRect(0, -6, 46, 12);
  ctx.restore();
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText('cannon, ' + s.ang + '\u00B0', X(0) - 10, Y(0) + 22);

  // live projectile
  if (flight) {
    ctx.fillStyle = LK.C.target;
    ctx.beginPath(); ctx.arc(X(flight.x), Y(Math.max(0, flight.y)), 9, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = LK.C.ink; ctx.font = '600 13px system-ui, sans-serif';
    ctx.fillText('x=' + flight.x.toFixed(1) + ' m, y=' + Math.max(0, flight.y).toFixed(1) + ' m',
                 X(flight.x) + 14, Y(flight.y) - 10);
  }
}

function nice(v) {
  var p = Math.pow(10, Math.floor(Math.log10(v || 1)));
  var c = v / p;
  return (c < 1.5 ? 1 : c < 3.5 ? 2 : c < 7.5 ? 5 : 10) * p;
}

var anim = null;
function tick() {
  if (!flight) return;
  var pr = predict();
  flight.t += 0.016 * LK.clamp(pr.T / 2.6, 0.4, 3);
  var th = s.ang * Math.PI / 180, u = flight.u, g = flight.g;
  flight.x = u * Math.cos(th) * flight.t;
  flight.y = u * Math.sin(th) * flight.t - 0.5 * g * flight.t * flight.t;
  document.getElementById('rLive').innerHTML =
    'In flight: t = ' + flight.t.toFixed(2) + ' s, x = ' + flight.x.toFixed(1) + ' m, y = ' + Math.max(0, flight.y).toFixed(1) + ' m';
  if (flight.y <= 0) {
    trails.push({ pts: pathFor(flight.ang0, u, g), hitRange: flight.x, h: predictFor(flight.ang0, u, g).H });
    if (trails.length > 4) trails.shift();
    document.getElementById('rLive').innerHTML =
      'Landed at <b>' + flight.x.toFixed(1) + ' m</b> after <b>' + flight.t.toFixed(2) + ' s</b> (predicted R = ' + pr.R.toFixed(1) + ' m) \u2713';
    flight = null;
  }
  function predictFor(a, uu, gg) {
    var t2 = a * Math.PI / 180;
    return { H: uu * uu * Math.sin(t2) * Math.sin(t2) / (2 * gg) };
  }
}
setInterval(tick, 16);

function upd() {
  var pr = predict();
  document.getElementById('rRange').innerHTML = 'Range R = u\u00B2sin2\u03B8/g = <b>' + pr.R.toFixed(1) + ' m</b>';
  document.getElementById('rHeight').innerHTML = 'Max height H = u\u00B2sin\u00B2\u03B8/2g = <b>' + pr.H.toFixed(1) + ' m</b>';
  document.getElementById('rTime').innerHTML = 'Time of flight T = 2u sin\u03B8/g = <b>' + pr.T.toFixed(2) + ' s</b>';
}

LK.slider('ang', function (v) { s.ang = v; document.getElementById('angv').textContent = v + '\u00B0'; upd(); });
LK.slider('spd', function (v) { s.u = v; document.getElementById('spdv').textContent = v + ' m/s'; upd(); });
LK.segment('gSeg', function (i) { s.g = [9.8, 1.62, 3.71, 24.79][i]; upd(); });
LK.button('launchBtn', function () { if (!flight) flight = { t: 0, x: 0, y: 0, u: s.u, g: s.g, ang0: s.ang }; });
LK.button('clearBtn', function () { trails = []; flight = null; });

st.draw = draw; upd();
