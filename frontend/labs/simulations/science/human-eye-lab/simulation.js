'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { eye: 0, power: 0 };

// eye model: lens at x=Lx, retina at fixed x; focal drift by defect
var EYE = [
  { name: 'Normal eye', retinaShift: 0, fix: 0, why: 'The lens focuses rays exactly on the retina. Sharp vision at all distances.' },
  { name: 'Myopia (short-sightedness)', retinaShift: -42, fix: -2.5, why: 'Too much curvature / long eyeball → image forms in front of the retina. Distant objects look blurry.' },
  { name: 'Hypermetropia (long-sightedness)', retinaShift: 38, fix: 2.25, why: 'Flat lens / short eyeball → image would form behind the retina. Nearby objects look blurry.' }
];

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var eye = EYE[s.eye];
  var cy = h / 2;
  var lensX = w * 0.40;                  // eye lens position
  var retinaX = w * 0.66 + eye.retinaShift;

  /* ---------- eyeball ---------- */
  ctx.fillStyle = '#fdf6f0';
  ctx.beginPath();
  ctx.ellipse(w * 0.5, cy, w * 0.23, h * 0.30, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#e7c8b8'; ctx.lineWidth = 6; ctx.stroke();
  // cornea bulge
  ctx.beginPath();
  ctx.ellipse(lensX - 34, cy, 30, h * 0.20, 0, 0, Math.PI * 2);
  ctx.fillStyle = '#fff'; ctx.fill();
  ctx.strokeStyle = '#d9b8a8'; ctx.lineWidth = 4; ctx.stroke();
  // iris + pupil
  ctx.fillStyle = '#5b8fb0';
  ctx.beginPath(); ctx.ellipse(lensX - 26, cy, 16, h * 0.16, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.beginPath(); ctx.ellipse(lensX - 26, cy, 7, h * 0.10, 0, 0, Math.PI * 2); ctx.fill();
  // retina (screen at back)
  ctx.strokeStyle = '#f43f5e'; ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.ellipse(w * 0.5, cy, w * 0.23, h * 0.30, 0, Math.PI * 0.68, Math.PI * 1.32);
  ctx.stroke();
  ctx.strokeStyle = '#fda4af'; ctx.lineWidth = 3; ctx.setLineDash([3, 5]);
  ctx.beginPath(); ctx.moveTo(retinaX, cy - h * 0.27); ctx.lineTo(retinaX, cy + h * 0.27); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = '#f43f5e'; ctx.font = '600 13px system-ui, sans-serif';
  ctx.fillText('retina', retinaX - 20, cy + h * 0.30);

  /* ---------- corrective lens in front ---------- */
  var correctPower = eye.fix !== 0 ? eye.fix : 0;
  var showsLens = Math.abs(s.power) > 0.01;
  var specsX = lensX - 110;
  if (showsLens) {
    var convex = s.power > 0;
    ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 5;
    ctx.beginPath();
    if (convex) {  // bulging lens
      ctx.moveTo(specsX, cy - 64);
      ctx.quadraticCurveTo(specsX + 26, cy, specsX, cy + 64);
    } else {
      ctx.moveTo(specsX + 14, cy - 64);
      ctx.quadraticCurveTo(specsX - 12, cy, specsX + 14, cy + 64);
    }
    ctx.stroke();
    ctx.fillStyle = '#38bdf8'; ctx.font = '600 12.5px system-ui, sans-serif';
    ctx.fillText(convex ? 'convex + (for long-sight)' : 'concave − (for short-sight)', specsX - 60, cy - 78);
  }

  /* ---------- rays ---------- */
  // incoming parallel rays from a distant object
  var rayYs = [-70, -35, 35, 70];
  var totalBend = 1 + eye.retinaShift / 150 + s.power * 0.16;
  rayYs.forEach(function (ry) {
    var y0 = cy + ry;
    // to eye lens
    ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(30, y0); ctx.lineTo(lensX, y0); ctx.stroke();
    // after eye lens: converge by 'totalBend'
    var converge = 1 - 1 / totalBend;
    var farX = w - 20;
    var yFar = y0 + (cy - y0) * converge * ((farX - lensX) / (retinaX - lensX) * 0.92);
    ctx.strokeStyle = LK.C.brand;
    ctx.beginPath(); ctx.moveTo(lensX, y0); ctx.lineTo(farX, yFar); ctx.stroke();
    // focal marker: where rays cross the axis
  });
  // approximate focal point x where central rays cross:
  var focalX = lensX + (retinaX - lensX) / totalBend;
  var focused = Math.abs(focalX - retinaX) < 14;
  // focus dot
  ctx.fillStyle = focused ? LK.C.ok : LK.C.target;
  ctx.beginPath(); ctx.arc(Math.min(w - 30, Math.max(lensX + 20, focalX)), cy, focused ? 7 : 9, 0, Math.PI * 2); ctx.fill();
  if (focused) {
    ctx.strokeStyle = LK.C.ok; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(Math.min(w - 30, Math.max(lensX + 20, focalX)), cy, 14, 0, Math.PI * 2); ctx.stroke();
  }

  /* ---------- object (arrow) ---------- */
  ctx.fillStyle = LK.C.b;
  ctx.beginPath(); ctx.moveTo(30, cy - 90); ctx.lineTo(22, cy - 70); ctx.lineTo(38, cy - 70); ctx.closePath(); ctx.fill();
  ctx.fillRect(28, cy - 70, 4, 140);

  /* ---------- text readouts ---------- */
  document.getElementById('diag').innerHTML = eye.why;
  var need = eye.fix;
  var lensRead = document.getElementById('lensRead');
  if (!showsLens) lensRead.innerHTML = eye.eye !== 0 && false ? '' : 'No lens — use the Power slider to add one.';
  var verdict;
  if (!showsLens) {
    verdict = s.eye === 0 ? 'Bare eye focuses perfectly ✓' : 'Image falls ' + (s.eye === 1 ? 'short of' : 'beyond') + ' the retina ✗';
  } else if (focused) {
    verdict = '🎯 Image focused on the retina — perfect correction!';
  } else {
    verdict = focalX < retinaX ? 'Rays still converge too early — ' : 'Rays still too weak — ';
    verdict += (need < 0 && s.power > need) || (need > 0 && s.power < need) ? 'adjust power toward ' + (need < 0 ? '−' : '+') + Math.abs(need).toFixed(2) + ' D' : 'overshoot slightly';
  }
  lensRead.innerHTML = verdict + (showsLens ? '<br>Lens power: <b>' + (s.power > 0 ? '+' : '') + s.power.toFixed(2) + ' D</b>' : '');
  ctx.fillStyle = focused ? LK.C.ok : LK.C.target;
  ctx.font = 'bold 15px system-ui, sans-serif';
  ctx.fillText(focused ? 'FOCUSED ✓' : 'blurry ✗', retinaX - 40, cy - h * 0.33);
}

LK.segment('eyeSeg', function (i) {
  s.eye = i;
  document.getElementById('power').value = 0;
  s.power = 0;
  document.getElementById('powerv').textContent = '0.00 D';
});
LK.slider('power', function (v) {
  s.power = v;
  document.getElementById('powerv').textContent = (v > 0 ? '+' : '') + v.toFixed(2) + ' D';
});

st.draw = draw;
