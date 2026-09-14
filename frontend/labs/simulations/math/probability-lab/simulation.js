'use strict';
var s = { mode: 'coin', counts: [0, 0], N: 0 };
var K = 6; // number of outcomes
var LABELS_COIN = ['Heads', 'Tails'];
var st = LK.setupCanvas(document.getElementById('cv'));

function outcomes() { return s.mode === 'coin' ? 2 : 6; }
function theo() { return 1 / outcomes(); }
function labels() {
  var out = [];
  for (var i = 0; i < outcomes(); i++) out.push(s.mode === 'coin' ? LABELS_COIN[i] : String(i + 1));
  return out;
}
function roll() { return Math.floor(Math.random() * outcomes()); }
function run(k) {
  for (var i = 0; i < k; i++) { s.counts[roll()]++; s.N++; }
  if (s.N >= 500) document.getElementById('lawBanner').classList.remove('hidden');
  upd();
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var padL = 70, padB = 56, padT = 40;
  var n = outcomes();
  var cw = (w - padL - 30) / n;
  var maxC = Math.max(4, theo() * s.N * 1.25);
  var chartH = h - padB - padT;
  // y gridlines
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  var stepY = niceStep(maxC);
  for (var g = 0; g <= maxC; g += stepY) {
    var gy = padT + chartH - (g / maxC) * chartH;
    ctx.strokeStyle = LK.C.grid2; ctx.beginPath(); ctx.moveTo(padL, gy); ctx.lineTo(w - 20, gy); ctx.stroke();
    ctx.fillText(String(g), padL - 26, gy + 4);
  }
  // theoretical line
  var ty = padT + chartH - (theo() * s.N / maxC) * chartH;
  ctx.strokeStyle = LK.C.target; ctx.lineWidth = 2.5; ctx.setLineDash([10, 7]);
  ctx.beginPath(); ctx.moveTo(padL, ty); ctx.lineTo(w - 20, ty); ctx.stroke();
  ctx.setLineDash([]);
  // bars
  labels().forEach(function (lb, i) {
    var c = s.counts[i];
    var bh = (c / maxC) * chartH;
    var bx = padL + i * cw + cw * 0.18;
    var bw = cw * 0.64;
    var grad = ctx.createLinearGradient(0, padT + chartH - bh, 0, padT + chartH);
    grad.addColorStop(0, LK.C.brand); grad.addColorStop(1, '#818cf8');
    ctx.fillStyle = grad;
    ctx.fillRect(bx, padT + chartH - bh, bw, bh);
    ctx.strokeStyle = LK.C.grid2; ctx.strokeRect(bx, padT + chartH - bh, bw, bh);
    // labels
    ctx.fillStyle = LK.C.ink; ctx.textAlign = 'center';
    ctx.font = '600 15px system-ui, sans-serif';
    ctx.fillText(lb, bx + bw / 2, h - padB + 24);
    ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
    ctx.fillText(c + ' (' + (s.N ? (100 * c / s.N).toFixed(1) : '0.0') + '%)', bx + bw / 2, h - padB + 42);
    ctx.textAlign = 'start';
  });
  // legend
  ctx.fillStyle = LK.C.target;
  ctx.fillRect(w - 250, 12, 26, 0); ctx.fillRect(w - 250, 10, 26, 3);
  ctx.fillStyle = LK.C.sub; ctx.fillText('theoretical ' + (theo() * 100).toFixed(1) + '%', w - 216, 17);
}

function niceStep(maxC) {
  var raw = maxC / 5, p = Math.pow(10, Math.floor(Math.log10(raw)));
  var c = raw / p;
  return (c < 1.5 ? 1 : c < 3.5 ? 2 : c < 7.5 ? 5 : 10) * p;
}

function upd() {
  document.getElementById('nTrials').textContent = s.N + (s.N === 1 ? ' trial' : ' trials');
  var html = '';
  labels().forEach(function (lb, i) {
    var exp = s.N ? s.counts[i] / s.N : 0;
    html += '<div class="lk-readout">' + lb + ': experimental <b>' + exp.toFixed(3) + '</b> vs theoretical <b>' + theo().toFixed(3) + '</b></div>';
  });
  if (s.mode === 'die' && s.N) {
    var mean = 0;
    for (var i = 0; i < 6; i++) mean += (i + 1) * s.counts[i];
    html += '<div class="lk-readout">Mean of rolls: <b>' + (mean / s.N).toFixed(2) + '</b> (expected 3.50)</div>';
  }
  document.getElementById('stats').innerHTML = html;
}

LK.segment('modeSeg', function (i) {
  s.mode = i === 0 ? 'coin' : 'die';
  s.counts = new Array(outcomes()).fill(0); s.N = 0;
  document.getElementById('lawBanner').classList.add('hidden');
  upd();
});
LK.button('run1', function () { run(1); });
LK.button('run10', function () { run(10); });
LK.button('run100', function () { run(100); });
LK.button('run1000', function () { run(1000); });
LK.button('resetBtn', function () {
  s.counts = new Array(outcomes()).fill(0); s.N = 0;
  document.getElementById('lawBanner').classList.add('hidden');
  upd();
});

st.draw = draw; upd();
