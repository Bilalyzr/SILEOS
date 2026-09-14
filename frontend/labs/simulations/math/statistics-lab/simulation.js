'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { data: [], spread: 10 };

function gen() {
  s.data = [];
  for (var i = 0; i < 25; i++) {
    s.data.push(LK.clamp(Math.round(50 + (Math.random() - 0.5) * 2 * s.spread), 0, 99));
  }
  upd();
}
function symmetric() {
  s.data = [];
  for (var i = 0; i < 25; i++) {
    // values symmetric around 70
    var base = [55, 58, 60, 62, 63, 65, 66, 68, 68, 70, 70, 70, 70, 70, 70, 72, 72, 74, 75, 77, 78, 80, 82, 85, 88];
    s.data = base.slice();
  }
  upd();
}

function stats() {
  var a = s.data.slice().sort(function (x, y) { return x - y; });
  var n = a.length;
  var mean = a.reduce(function (p, c) { return p + c; }, 0) / n;
  var med = n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2;
  // mode: most frequent
  var freq = {}, best = [], bestC = 0;
  a.forEach(function (v) { freq[v] = (freq[v] || 0) + 1; });
  Object.keys(freq).forEach(function (v) {
    if (freq[v] > bestC) { bestC = freq[v]; best = [+v]; }
    else if (freq[v] === bestC) best.push(+v);
  });
  return { sorted: a, mean: mean, med: med, modes: bestC > 1 ? best : [], freq: freq };
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  if (!s.data.length) return;
  var stt = stats();

  /* -------- histogram (left/top) -------- */
  var padL = 56, padB = 46, padT = 60;
  var gx0 = padL, gx1 = w * 0.62, gy0 = padT, gy1 = h - padB;
  var marks0 = Math.floor(Math.min(0, ...s.data) / 10) * 10;
  var marks1 = Math.ceil(Math.max(100, ...s.data) / 10) * 10;
  var bins = Math.round((marks1 - marks0) / 10);
  var counts = new Array(bins).fill(0);
  s.data.forEach(function (v) {
    var b = Math.min(bins - 1, Math.floor((v - marks0) / 10));
    counts[b]++;
  });
  var maxC = Math.max(1, ...counts) * 1.2;
  var bw = (gx1 - gx0) / bins;
  // axes
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(gx0, gy0); ctx.lineTo(gx0, gy1); ctx.lineTo(gx1, gy1); ctx.stroke();
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  for (var c = 0; c <= maxC; c += Math.max(1, Math.round(maxC / 5))) {
    var gy = gy1 - (c / maxC) * (gy1 - gy0);
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(gx0, gy); ctx.lineTo(gx1, gy); ctx.stroke();
    ctx.fillText(String(c), gx0 - 22, gy + 4);
  }
  // bars
  for (var b2 = 0; b2 < bins; b2++) {
    var bh = (counts[b2] / maxC) * (gy1 - gy0);
    var bx = gx0 + b2 * bw;
    var grad = ctx.createLinearGradient(0, gy1 - bh, 0, gy1);
    grad.addColorStop(0, '#818cf8'); grad.addColorStop(1, '#c7d2fe');
    ctx.fillStyle = grad;
    ctx.fillRect(bx + 2, gy1 - bh, bw - 4, bh);
    ctx.strokeStyle = LK.C.grid2; ctx.strokeRect(bx + 2, gy1 - bh, bw - 4, bh);
    ctx.fillStyle = LK.C.sub;
    ctx.fillText(String(marks0 + b2 * 10), bx + bw / 2 - 10, gy1 + 16);
  }
  ctx.fillStyle = LK.C.sub; ctx.font = '600 13px system-ui, sans-serif';
  ctx.fillText('marks histogram (class size 10)', gx0, gy0 - 14);

  // mean / median lines on histogram
  function vline(v, color, label) {
    var x = gx0 + ((v - marks0) / (marks1 - marks0)) * (gx1 - gx0);
    ctx.strokeStyle = color; ctx.lineWidth = 2.5; ctx.setLineDash([7, 5]);
    ctx.beginPath(); ctx.moveTo(x, gy0); ctx.lineTo(x, gy1); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = color; ctx.font = 'bold 12.5px system-ui, sans-serif';
    ctx.fillText(label, x - 18, gy0 - (label === 'mean' ? 30 : 14));
  }
  vline(stt.mean, LK.C.brand, 'mean');
  vline(stt.med, LK.C.m, 'median');

  /* -------- dot plot (right) -------- */
  var dx0 = w * 0.70, dx1 = w - 40;
  ctx.fillStyle = LK.C.sub; ctx.font = '600 13px system-ui, sans-serif';
  ctx.fillText('each dot = one student', dx0, gy0 - 14);
  var yBase = gy1 - 10;
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(dx0 - 10, yBase); ctx.lineTo(dx1, yBase); ctx.stroke();
  var dx = function (v) { return dx0 + ((v - marks0) / (marks1 - marks0)) * (dx1 - dx0); };
  var colHeights = {};
  s.data.forEach(function (v) {
    var key = Math.round(v);
    colHeights[key] = (colHeights[key] || 0) + 1;
    var yy = yBase - colHeights[key] * 16 + 6;
    ctx.fillStyle = v === 100 ? LK.C.target : '#6366f1';
    ctx.beginPath(); ctx.arc(dx(v), yy, 6, 0, Math.PI * 2); ctx.fill();
  });
  [0, 25, 50, 75, 100].forEach(function (t) {
    if (t >= marks0 && t <= marks1) {
      ctx.fillStyle = LK.C.sub; ctx.font = '11.5px system-ui, sans-serif';
      ctx.fillText(String(t), dx(t) - 8, yBase + 18);
    }
  });
}

function upd() {
  var stt = stats();
  document.getElementById('rMean').textContent = stt.mean.toFixed(2);
  document.getElementById('rMed').textContent = stt.med.toFixed(1);
  document.getElementById('rMode').textContent = stt.modes.length ? stt.modes.join(', ') : 'no repeat (all unique)';
  var gap = Math.abs(stt.mean - stt.med);
  document.getElementById('lesson').innerHTML = gap > 2
    ? 'Mean and median differ by <b>' + gap.toFixed(1) + '</b> — the data is skewed! (an outlier dragged the mean)'
    : 'Mean ≈ median — nicely balanced data ✓';
}

LK.slider('spread', function (v) {
  s.spread = v;
  document.getElementById('spreadv').textContent = '±' + v;
});
LK.button('genBtn', gen);
LK.button('symBtn', symmetric);
LK.button('outlierBtn', function () {
  if (s.data.length > 25) s.data.pop();
  s.data.push(100);
  upd();
});

gen();
st.draw = draw;
