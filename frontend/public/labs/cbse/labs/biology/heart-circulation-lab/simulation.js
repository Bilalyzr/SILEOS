'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { bpm: 72, t: 0, particles: [] };

for (var i = 0; i < 46; i++) {
  s.particles.push({ seg: Math.floor(Math.random() * 6), u: Math.random(), oxy: Math.random() < 0.5 });
}

/* circulation path segments: body→RA, RA→RV, RV→lungs, lungs→LA, LA→LV, LV→body */
function segPath(idx) {
  var w = st.w, h = st.h;
  var cx = w * 0.5, cy = h * 0.52;
  var rx = Math.min(w * 0.13, 130), ry = Math.min(h * 0.23, 190);
  var pts = {
    0: [{ x: cx - rx * 2.6, y: cy + ry * 0.9 }, { x: cx - rx * 1.4, y: cy + ry * 0.5 }, { x: cx - rx * 0.4, y: cy + ry * 0.35 }],
    1: [{ x: cx - rx * 0.4, y: cy + ry * 0.35 }, { x: cx - rx * 0.42, y: cy + ry * 0.95 }],
    2: [{ x: cx - rx * 0.42, y: cy + ry * 0.95 }, { x: cx - rx * 1.5, y: cy - ry * 1.15 }, { x: cx - rx * 0.7, y: cy - ry * 1.3 }],
    3: [{ x: cx - rx * 0.7, y: cy - ry * 1.3 }, { x: cx + rx * 0.4, y: cy - ry * 1.15 }, { x: cx + rx * 0.42, y: cy - ry * 0.6 }],
    4: [{ x: cx + rx * 0.42, y: cy - ry * 0.6 }, { x: cx + rx * 0.44, y: cy + ry * 0.9 }],
    5: [{ x: cx + rx * 0.44, y: cy + ry * 0.9 }, { x: cx + rx * 1.6, y: cy + ry * 0.8 }, { x: cx + rx * 2.6, y: cy + ry * 0.2 }, { x: cx, y: cy + ry * 1.9 }, { x: cx - rx * 2.6, y: cy + ry * 0.9 }]
  };
  return pts[idx];
}
function pointOnSeg(idx, u) {
  var pts = segPath(idx);
  // linear interp along polyline
  var total = 0;
  for (var i = 1; i < pts.length; i++) total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
  var d = u * total;
  for (var j = 1; j < pts.length; j++) {
    var seg = Math.hypot(pts[j].x - pts[j - 1].x, pts[j].y - pts[j - 1].y);
    if (d <= seg) {
      var t = d / seg;
      return { x: pts[j - 1].x + (pts[j].x - pts[j - 1].x) * t, y: pts[j - 1].y + (pts[j].y - pts[j - 1].y) * t };
    }
    d -= seg;
  }
  return pts[pts.length - 1];
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  s.t += 0.016;
  var beat = (s.t * s.bpm / 60) % 1;
  var systole = beat < 0.38;
  var squeeze = systole ? Math.sin(beat / 0.38 * Math.PI) : 0;
  var cx = w * 0.5, cy = h * 0.52;
  var rx = Math.min(w * 0.13, 130), ry = Math.min(h * 0.23, 190);

  /* vessels: blue (right side) & red (left) */
  function vessel(pts, color, width, flowDir) {
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round';
    ctx.beginPath();
    pts.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
    ctx.stroke();
    ctx.lineCap = 'butt';
  }
  // draw paths as tubes
  for (var sg = 0; sg < 6; sg++) {
    var pts = segPath(sg);
    vessel(pts, sg === 2 || sg === 0 || sg === 1 ? 'rgba(37,99,235,.35)' : 'rgba(220,38,38,.30)', 12);
  }

  /* heart (two pumps!) */
  function chamber(x, y, r, color, sq) {
    var rr = r * (1 - sq * 0.16);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.ellipse(x, y, rr, rr * 1.12, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 2.5; ctx.stroke();
  }
  // right side (blue blood), left side (red) — note: patient's right = screen left
  chamber(cx - rx * 0.42, cy - ry * 0.15, rx * 0.30, '#dbeafe', squeeze * 0.8);
  chamber(cx - rx * 0.42, cy + ry * 0.55, rx * 0.34, '#93c5fd', squeeze);
  chamber(cx + rx * 0.42, cy - ry * 0.15, rx * 0.30, '#fee2e2', squeeze * 0.8);
  chamber(cx + rx * 0.44, cy + ry * 0.55, rx * 0.40, '#fca5a5', squeeze);   // thicker LV!
  // labels
  ctx.fillStyle = '#1e3a8a'; ctx.font = '600 12px Inter, sans-serif';
  ctx.fillText('RA', cx - rx * 0.55, cy - ry * 0.15);
  ctx.fillText('RV', cx - rx * 0.56, cy + ry * 0.6);
  ctx.fillStyle = '#7f1d1d';
  ctx.fillText('LA', cx + rx * 0.32, cy - ry * 0.15);
  ctx.fillText('LV', cx + rx * 0.3, cy + ry * 0.6);
  ctx.fillStyle = '#6b7891'; ctx.font = '600 11.5px Inter, sans-serif';
  ctx.fillText('lungs', cx - rx * 0.9, cy - ry * 1.45);
  ctx.fillText('body', cx + rx * 1.6, cy + ry * 0.55);
  ctx.fillText(' thicker wall — pushes to whole body', cx + rx * 0.85, cy + ry * 0.9);

  /* blood particles */
  var speed = s.bpm / 72;
  s.particles.forEach(function (p) {
    p.u += 0.004 * speed;
    if (p.u >= 1) {
      p.u = 0;
      p.seg = (p.seg + 1) % 6;
      if (p.seg === 3) p.oxy = true;    // passes lungs: gains O2
      if (p.seg === 5) p.oxy = false;   // gives O2 to body
    }
    var pt = pointOnSeg(p.seg, p.u);
    ctx.fillStyle = p.oxy ? '#dc2626' : '#2563eb';
    ctx.beginPath(); ctx.arc(pt.x, pt.y, 5.5, 0, Math.PI * 2); ctx.fill();
  });

  /* readouts */
  var CO = Math.round(s.bpm * 70 / 1000);   // L/min with 70 mL stroke
  document.getElementById('phase').innerHTML = systole
    ? '💓 <b>SYSTOLE</b> — ventricles contract, blood is pushed out (valves slam: lub)'
    : '💙 <b>DIASTOLE</b> — heart relaxes and refills (dub)';
  document.getElementById('flow').innerHTML =
    'Blue = oxygen-poor (heading to lungs) · Red = oxygen-rich (from lungs → body)';
  document.getElementById('pumpOut').innerHTML =
    'Cardiac output ≈ ' + s.bpm + ' × 70 mL = <b>' + CO + ' L/min</b>' +
    (s.bpm > 120 ? ' — exercising hard!' : s.bpm < 60 ? ' — athlete\u2019s resting heart!' : '');
}

LK.slider('bpm', function (v) { s.bpm = v; document.getElementById('bpmv').textContent = v; });
LK.segment('modeSeg', function (i) {
  var b = [72, 100, 160][i];
  s.bpm = b;
  document.getElementById('bpm').value = b;
  document.getElementById('bpmv').textContent = b;
});
st.draw = draw;
