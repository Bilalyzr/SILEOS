'use strict';
var s = { h0: 60, p0: 20, a: 0.6, b: 0.02, g: 0.4 };
var T = 60;               // seasons
var data = { t: [], h: [], p: [], extinct: false };
var st = LK.setupCanvas(document.getElementById('cv'));
var playHead = 0, playing = true, lastT = 0;

function simulate() {
  var dt = 0.02, d = { t: [0], h: [s.h0], p: [s.p0], extinct: false };
  var h = s.h0, p = s.p0, t = 0, frame = 0;
  var dlt = 0.008; // predator reproduction per eaten rabbit (fixed)
  while (t < T) {
    var dh = s.a * h - s.b * h * p;
    var dp = dlt * h * p - s.g * p;
    h += dh * dt; p += dp * dt; t += dt; frame++;
    if (h < 0.5 || p < 0.5) { d.extinct = true; h = Math.max(0, h); p = Math.max(0, p); }
    if (frame % 5 === 0) { d.t.push(t); d.h.push(h); d.p.push(p); }
    if (d.extinct && t > 2) break;
  }
  data = d;
  document.getElementById('crashBanner').classList.toggle('hidden', !d.extinct);
}

function draw(now) {
  var dt = Math.min(0.05, (now - lastT) / 1000 || 0.016);
  lastT = now;
  if (playing) playHead = Math.min(data.t.length - 1, playHead + dt * 45);

  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var padL = 62, padR = 26, padT = 40, padB = 46;
  var x0 = padL, x1 = w - padR, y0 = padT, y1 = h - padB;
  var maxPop = 10;
  for (var i = 0; i <= playHead; i++) maxPop = Math.max(maxPop, data.h[i], data.p[i]);
  maxPop *= 1.12;
  var TX = function (t) { return x0 + (t / T) * (x1 - x0); };
  var PY = function (v) { return y1 - (v / maxPop) * (y1 - y0); };

  // grid
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  var stepP = maxPop > 400 ? 200 : maxPop > 200 ? 100 : maxPop > 80 ? 50 : 20;
  for (var g = 0; g <= maxPop; g += stepP) {
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(x0, PY(g)); ctx.lineTo(x1, PY(g)); ctx.stroke();
    ctx.fillText(String(g), x0 - 30, PY(g) + 4);
  }
  for (var tt = 0; tt <= T; tt += 10) {
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(TX(tt), y0); ctx.lineTo(TX(tt), y1); ctx.stroke();
    ctx.fillText(String(tt), TX(tt) - 4, y1 + 18);
  }
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0, y1); ctx.lineTo(x1, y1); ctx.stroke();
  ctx.fillStyle = LK.C.sub; ctx.font = '13px system-ui, sans-serif';
  ctx.fillText('population vs seasons', x0, y0 - 14);

  // series
  function series(arr, color, width) {
    ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.beginPath();
    for (var i = 0; i <= playHead; i++) {
      i ? ctx.lineTo(TX(data.t[i]), PY(arr[i])) : ctx.moveTo(TX(data.t[0]), PY(arr[0]));
    }
    ctx.stroke();
    if (playHead > 0) {
      ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(TX(data.t[Math.floor(playHead)]), PY(arr[Math.floor(playHead)]), 5.5, 0, Math.PI * 2); ctx.fill();
    }
  }
  series(data.h, LK.C.ok, 3.2);
  series(data.p, LK.C.target, 3.2);

  // legend
  ctx.font = '600 14px system-ui, sans-serif';
  ctx.fillStyle = LK.C.ok;  ctx.fillText('— 🐇 prey', x1 - 220, y0 + 2);
  ctx.fillStyle = LK.C.target; ctx.fillText('— 🦊 predators', x1 - 120, y0 + 2);

  var hi = Math.floor(playHead);
  document.getElementById('now').innerHTML =
    'Season ' + data.t[hi].toFixed(0) + ': 🐇 <b>' + Math.round(data.h[hi]) + '</b> prey, 🦊 <b>' + Math.round(data.p[hi]) + '</b> predators';
  if (playHead >= data.t.length - 1 && playing && data.t.length > 2) playing = false;
}

function rebind(id, key, valId, dec) {
  LK.slider(id, function (v) {
    s[key] = v;
    document.getElementById(valId).textContent = v.toFixed(dec);
    simulate(); playHead = 0; playing = true;
  });
}
rebind('h0', 'h0', 'h0v', 0); rebind('p0', 'p0', 'p0v', 0);
rebind('alpha', 'a', 'alphav', 2); rebind('beta', 'b', 'betav', 3); rebind('gamma', 'g', 'gammav', 2);
LK.button('replayBtn', function () { simulate(); playHead = 0; playing = true; });

simulate();
st.draw = draw;
