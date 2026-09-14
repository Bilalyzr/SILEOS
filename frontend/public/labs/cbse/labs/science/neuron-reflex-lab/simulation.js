'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, pulse: -1, speed: 1, t: 0 };

/* neuron path: dendrite → soma → axon (with myelin gaps) → terminal */
function neuronPath() {
  return [
    { x: 0.04, y: 0.40 }, { x: 0.16, y: 0.34 }, { x: 0.28, y: 0.42 },   // dendrites
    { x: 0.36, y: 0.38 },                                                 // soma
    { x: 0.46, y: 0.38 }, { x: 0.92, y: 0.38 }                            // axon
  ];
}
function pt(frac) {  // position along a polyline given 0..1
  var pts = neuronPath().map(p => ({ x: p.x * st.w, y: p.y * st.h }));
  var total = 0;
  for (var i = 1; i < pts.length; i++) total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
  var d = frac * total;
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

function drawNeuron(ctx, alpha) {
  ctx.globalAlpha = alpha;
  var w = st.w, h = st.h;
  var pts = neuronPath().map(p => ({ x: p.x * w, y: p.y * h }));
  // dendrite branches
  ctx.strokeStyle = '#b45309'; ctx.lineWidth = 3;
  [[0, -60], [-30, -60], [0, 60], [-30, 60]].forEach(off => {
    ctx.beginPath();
    ctx.moveTo(pts[0].x + 10, pts[0].y);
    ctx.quadraticCurveTo(pts[0].x - 20, pts[0].y + off[1] * 0.6, pts[0].x - 44 + off[0], pts[0].y + off[1]);
    ctx.stroke();
  });
  // main line
  ctx.strokeStyle = '#b45309'; ctx.lineWidth = 4;
  ctx.beginPath();
  pts.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
  ctx.stroke();
  // soma
  ctx.fillStyle = '#fde68a'; ctx.strokeStyle = '#b45309'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(w * 0.36, h * 0.38, 34, 28, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.fillStyle = '#b45309'; ctx.beginPath(); ctx.arc(w * 0.36, h * 0.38, 9, 0, Math.PI * 2); ctx.fill();
  // myelin sheath segments on axon
  ctx.fillStyle = '#0369a1';
  for (var m = 0; m < 7; m++) {
    var x0 = w * 0.48 + m * (w * 0.40 / 7);
    LK.roundRect(ctx, x0, h * 0.38 - 14, w * 0.40 / 7 - 8, 28, 12);
    ctx.fill();
  }
  // terminal branches
  ctx.strokeStyle = '#b45309'; ctx.lineWidth = 3;
  [[-40, -46], [10, -58], [40, -30], [-10, 50], [36, 44]].forEach(off => {
    ctx.beginPath();
    ctx.moveTo(w * 0.92, h * 0.38);
    ctx.quadraticCurveTo(w * 0.95, h * 0.38 + off[1] * 0.5, w * 0.95 + off[0] * 0.4, h * 0.38 + off[1]);
    ctx.stroke();
    ctx.fillStyle = '#dc2626';
    ctx.beginPath(); ctx.arc(w * 0.95 + off[0] * 0.4, h * 0.38 + off[1], 5, 0, Math.PI * 2); ctx.fill();
  });
  // labels
  ctx.fillStyle = '#6b7891'; ctx.font = '600 12.5px Inter, sans-serif';
  ctx.fillText('dendrites', w * 0.03, h * 0.38 - 70);
  ctx.fillText('cell body (soma)', w * 0.30, h * 0.38 + 60);
  ctx.fillText('axon + myelin sheath (insulation!)', w * 0.52, h * 0.38 - 34);
  ctx.fillText('synaptic terminals', w * 0.90, h * 0.38 + 80);
  ctx.globalAlpha = 1;
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  s.t += 0.016;

  if (s.mode === 0) {
    drawNeuron(ctx, 1);
    if (s.pulse >= 0) {
      s.pulse += 0.0035 * s.speed;
      var p = pt(s.pulse);
      // glow pulse
      var g = ctx.createRadialGradient(p.x, p.y, 2, p.x, p.y, 26);
      g.addColorStop(0, 'rgba(249,115,22,.95)');
      g.addColorStop(1, 'rgba(249,115,22,0)');
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(p.x, p.y, 26, 0, Math.PI * 2); ctx.fill();
      // synaptic burst at end
      if (s.pulse > 0.96) {
        var tx = w * 0.95, ty = h * 0.38;
        ctx.fillStyle = 'rgba(220,38,38,.8)';
        for (var b = 0; b < 10; b++) {
          var a = b * 0.628 + s.t * 2;
          ctx.beginPath(); ctx.arc(tx + Math.cos(a) * (18 + (s.t * 40 % 20)), ty + Math.sin(a) * 14, 3.4, 0, Math.PI * 2); ctx.fill();
        }
        document.getElementById('status').innerHTML = '🧪 Signal reached the <b>synaptic terminal</b> — neurotransmitters (red dots) jump the gap to the next cell!';
      } else {
        document.getElementById('status').innerHTML = '⚡ Pulse at ' + Math.round(s.pulse * 100) + '% of the way…';
      }
      if (s.pulse > 1.15) s.pulse = -1;
    }
  } else {
    // reflex arc: hand → sensory → spinal cord → motor → muscle
    var y0 = h * 0.16;
    // components
    function box(x, y, w2, h2, color, label) {
      ctx.fillStyle = color;
      LK.roundRect(ctx, x - w2 / 2, y - h2 / 2, w2, h2, 12); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = '600 12px Inter, sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(label, x, y + 4);
      ctx.textAlign = 'start';
    }
    // hand (receptor)
    ctx.font = '40px serif'; ctx.textAlign = 'center';
    ctx.fillText('✋', w * 0.10, h * 0.62);
    ctx.font = '600 12px Inter, sans-serif';
    ctx.fillStyle = '#6b7891';
    ctx.fillText('receptor (skin)', w * 0.10, h * 0.68);
    ctx.fillText('🔥', w * 0.10, h * 0.50);
    // spinal cord
    box(w * 0.55, h * 0.22, 90, 34, '#20345b', 'spinal cord');
    box(w * 0.55, h * 0.06, 90, 26, '#98a2b3', 'brain (told later!)');
    // muscle
    ctx.font = '34px serif';
    ctx.fillText('💪', w * 0.92, h * 0.60);
    ctx.font = '600 12px Inter, sans-serif';
    ctx.fillStyle = '#6b7891';
    ctx.fillText('effector (muscle)', w * 0.92, h * 0.68);
    ctx.textAlign = 'start';
    // wires
    ctx.strokeStyle = '#f97316'; ctx.lineWidth = 3.5;   // sensory
    ctx.beginPath();
    ctx.moveTo(w * 0.12, h * 0.58);
    ctx.bezierCurveTo(w * 0.20, h * 0.42, w * 0.42, h * 0.30, w * 0.51, h * 0.24);
    ctx.stroke();
    ctx.strokeStyle = '#0369a1';                        // motor
    ctx.beginPath();
    ctx.moveTo(w * 0.59, h * 0.24);
    ctx.bezierCurveTo(w * 0.72, h * 0.32, w * 0.86, h * 0.44, w * 0.90, h * 0.56);
    ctx.stroke();
    ctx.strokeStyle = '#98a2b3'; ctx.setLineDash([5, 5]); ctx.lineWidth = 2;  // to brain
    ctx.beginPath(); ctx.moveTo(w * 0.55, h * 0.19); ctx.lineTo(w * 0.55, h * 0.09); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#f97316'; ctx.font = '600 12.5px Inter, sans-serif';
    ctx.fillText('sensory neuron →', w * 0.18, h * 0.36);
    ctx.fillStyle = '#0369a1';
    ctx.fillText('→ motor neuron', w * 0.72, h * 0.50);
    // pulse along reflex path
    if (s.pulse >= 0) {
      s.pulse += 0.006 * s.speed;
      var u = s.pulse;
      // piecewise: 0-0.5 sensory, 0.5-0.6 cord, 0.6-1 muscle
      var px0, py0;
      if (u < 0.5) {
        var uu = u / 0.5;
        var x1 = w * 0.12, y1 = h * 0.58, x2 = w * 0.51, y2 = h * 0.24;
        px0 = x1 + (x2 - x1) * uu; py0 = y1 + (y2 - y1) * uu - Math.sin(uu * Math.PI) * 40;
      } else if (u < 0.6) {
        px0 = w * 0.55; py0 = h * 0.22;
      } else {
        var uu2 = (u - 0.6) / 0.4;
        px0 = w * 0.59 + (w * 0.90 - w * 0.59) * uu2;
        py0 = h * 0.24 + (h * 0.56 - h * 0.24) * uu2 - Math.sin(uu2 * Math.PI) * 34;
      }
      var g2 = ctx.createRadialGradient(px0, py0, 2, px0, py0, 24);
      g2.addColorStop(0, 'rgba(220,38,38,.95)'); g2.addColorStop(1, 'rgba(220,38,38,0)');
      ctx.fillStyle = g2;
      ctx.beginPath(); ctx.arc(px0, py0, 24, 0, Math.PI * 2); ctx.fill();
      document.getElementById('status').innerHTML = u < 0.5 ? '🔥 Heat detected — signal racing to the spinal cord…'
        : u < 0.6 ? '🧠 Spinal cord decides INSTANTLY (brain is only informed!)'
        : u < 1 ? '💪 Motor neuron ordering the muscle: PULL BACK!'
        : '✅ Reflex complete — hand saved in ~0.05 s, pain felt only afterwards.';
      if (u > 1.2) s.pulse = -1;
    }
  }
}

LK.button('fireBtn', function () { s.pulse = 0; });
LK.slider('spd', function (v) { s.speed = v; document.getElementById('spdv').textContent = v.toFixed(2) + '×'; });
LK.segment('modeSeg', function (i) { s.mode = i; s.pulse = -1; });
st.draw = draw;
