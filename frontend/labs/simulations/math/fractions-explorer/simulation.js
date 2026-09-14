'use strict';
var s = { a1: 1, b1: 2, a2: 3, b2: 4 };
var st = LK.setupCanvas(document.getElementById('cv'));

function frac(n, d) { return d === 0 ? 0 : n / d; }

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var barW = Math.min(w - 140, 720), x0 = 70;
  var rows = [
    { y: h * 0.22, n: s.a1, d: s.b1, color: LK.C.brand, label: 'A' },
    { y: h * 0.58, n: s.a2, d: s.b2, color: LK.C.m, label: 'B' }
  ];
  rows.forEach(function (r) {
    var bh = Math.min(64, h * 0.14);
    // outline box
    ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2;
    ctx.strokeRect(x0, r.y, barW, bh);
    // unit partitions
    ctx.lineWidth = 1; ctx.strokeStyle = LK.C.grid2;
    for (var i = 1; i < r.d; i++) {
      var gx = x0 + (barW * i) / r.d;
      ctx.beginPath(); ctx.moveTo(gx, r.y); ctx.lineTo(gx, r.y + bh); ctx.stroke();
    }
    // filled part
    ctx.fillStyle = r.color;
    ctx.globalAlpha = 0.85;
    ctx.fillRect(x0, r.y, Math.min(barW * r.n / r.d, barW), bh);
    ctx.globalAlpha = 1;
    // labels
    ctx.fillStyle = LK.C.ink;
    ctx.font = 'bold 26px Georgia, serif'; ctx.textAlign = 'right';
    ctx.fillText(r.label, x0 - 40, r.y + bh / 2 + 4);
    ctx.font = 'bold 22px Georgia, serif'; ctx.textAlign = 'center';
    ctx.fillText(r.n + '/' + r.d, x0 + barW / 2, r.y + bh + 30);
    ctx.textAlign = 'start';
  });
}

function upd() {
  var vA = frac(s.a1, s.b1), vB = frac(s.a2, s.b2);
  var sym = vA > vB ? 'A > B' : vA < vB ? 'A < B' : 'A = B';
  var el = document.getElementById('cmp');
  el.textContent = sym;
  el.style.color = vA === vB ? LK.C.ok : LK.C.ink;
  document.getElementById('decA').innerHTML =
    'A = ' + s.a1 + '/' + s.b1 + ' = <b>' + vA.toFixed(3) + '</b> = ' + (vA * 100).toFixed(1) + '%';
  document.getElementById('decB').innerHTML =
    'B = ' + s.a2 + '/' + s.b2 + ' = <b>' + vB.toFixed(3) + '</b> = ' + (vB * 100).toFixed(1) + '%';
}

function bind(id, key) {
  LK.slider(id, function (v) {
    s[key] = v;
    document.getElementById(id + 'v').textContent = v;
    draw(); upd();
  });
}
bind('a1', 'a1'); bind('b1', 'b1'); bind('a2', 'a2'); bind('b2', 'b2');
st.draw = draw; draw(); upd();
