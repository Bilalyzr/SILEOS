'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { ang: 35 };

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);

  /* ---------------- left: right triangle ---------------- */
  var base = Math.min(w * 0.55, h * 0.62);
  var ox = 90, oy = h - 110;
  var rad = s.ang * Math.PI / 180;
  var tipX = ox + base, tipY = oy;
  var apexX = ox + base * Math.cos(rad) * 0 + ox * 0;  // right angle at (tipX, oy)? build: A at ox, B at tip, C above A by base*tan
  var rightX = ox + base * Math.cos(rad);
  var topY = oy - base * Math.tan(rad) * 0.0; // placeholder

  // Triangle: right angle at B=(bx0+adj, oy). A=(ox,oy). C=(ox, oy - opp)
  var adj = base * Math.cos(rad);
  var opp = base * Math.sin(rad) / Math.cos(rad) * Math.cos(rad); // = base*sin
  opp = base * Math.tan(rad) * Math.cos(rad); // same as base*sin(rad)
  var Ax = ox, Ay = oy;
  var Bx = ox + adj, By = oy;
  var Cx = ox, Cy = oy - opp;

  // fill triangle
  ctx.fillStyle = 'rgba(79,70,229,.07)';
  ctx.beginPath(); ctx.moveTo(Ax, Ay); ctx.lineTo(Bx, By); ctx.lineTo(Cx, Cy); ctx.closePath(); ctx.fill();

  // hypotenuse (brand)
  ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(Bx, By); ctx.lineTo(Cx, Cy); ctx.stroke();
  // adjacent (teal)
  ctx.strokeStyle = LK.C.m;
  ctx.beginPath(); ctx.moveTo(Ax, Ay); ctx.lineTo(Bx, By); ctx.stroke();
  // opposite (amber)
  ctx.strokeStyle = LK.C.b;
  ctx.beginPath(); ctx.moveTo(Ax, Ay); ctx.lineTo(Cx, Cy); ctx.stroke();

  // right-angle square at B
  ctx.strokeStyle = LK.C.sub; ctx.lineWidth = 1.5;
  ctx.strokeRect(Bx - 18, By - 18, 18, 18);

  // angle arc at A
  ctx.strokeStyle = LK.C.target; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.arc(Ax, Ay, 44, -rad, 0); ctx.stroke();
  ctx.fillStyle = LK.C.target; ctx.font = 'bold 15px Georgia, serif';
  ctx.fillText('θ', Ax + 54 * Math.cos(rad / 2), Ay - 54 * Math.sin(rad / 2) + 4);

  // labels
  ctx.font = 'italic 600 14px Georgia, serif';
  ctx.fillStyle = LK.C.b;   ctx.fillText('opposite', Ax - 84, (Ay + Cy) / 2);
  ctx.fillStyle = LK.C.m;   ctx.fillText('adjacent', (Ax + Bx) / 2 - 28, Ay + 24);
  ctx.fillStyle = LK.C.brand; ctx.fillText('hypotenuse', (Bx + Cx) / 2 - 30, (By + Cy) / 2 - 10);

  /* ---------------- right: unit circle ---------------- */
  var ucx = w * 0.78, ucy = h * 0.38, uR = Math.min(h * 0.24, w * 0.12);
  ctx.strokeStyle = LK.C.grid2; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(ucx - uR - 16, ucy); ctx.lineTo(ucx + uR + 16, ucy); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(ucx, ucy - uR - 16); ctx.lineTo(ucx, ucy + uR + 16); ctx.stroke();
  ctx.strokeStyle = LK.C.sub;
  ctx.beginPath(); ctx.arc(ucx, ucy, uR, 0, Math.PI * 2); ctx.stroke();
  // point on circle
  var px0 = ucx + Math.cos(rad) * uR, py0 = ucy - Math.sin(rad) * uR;
  ctx.strokeStyle = LK.C.m;
  ctx.beginPath(); ctx.moveTo(ucx, ucy); ctx.lineTo(px0, ucy); ctx.stroke();      // cos
  ctx.strokeStyle = LK.C.b;
  ctx.beginPath(); ctx.moveTo(px0, ucy); ctx.lineTo(px0, py0); ctx.stroke();      // sin
  ctx.strokeStyle = LK.C.brand;
  ctx.beginPath(); ctx.moveTo(ucx, ucy); ctx.lineTo(px0, py0); ctx.stroke();      // radius=1
  ctx.fillStyle = LK.C.brand;
  ctx.beginPath(); ctx.arc(px0, py0, 6, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = LK.C.sub; ctx.font = '600 12px system-ui, sans-serif';
  ctx.fillText('unit circle — radius = hypotenuse = 1', ucx - uR - 6, ucy + uR + 30);
  ctx.fillText('cos θ', (ucx + px0) / 2 - 16, ucy + 16);
  ctx.fillText('sin θ', px0 + 6, (ucy + py0) / 2);

  /* ---------------- readouts ---------------- */
  var sinT = Math.sin(rad), cosT = Math.cos(rad), tanT = Math.tan(rad);
  document.getElementById('rSin').textContent = sinT.toFixed(4);
  document.getElementById('rCos').textContent = cosT.toFixed(4);
  document.getElementById('rTan').textContent = tanT.toFixed(4);
  document.getElementById('identity').innerHTML =
    'sin²θ + cos²θ = <b>' + (sinT * sinT + cosT * cosT).toFixed(4) + '</b> — always 1! ✓';

  // heights & distances live problem
  var d = 20;                                     // metres from tower
  var towerH = d * tanT;
  document.getElementById('prob').innerHTML =
    'A student stands <b>' + d + ' m</b> from a tower and looks up at <b>θ = ' + s.ang + '°</b>.';
  document.getElementById('answer').innerHTML =
    'Tower height = d × tan θ = ' + d + ' × ' + tanT.toFixed(3) + ' = <b>' + towerH.toFixed(1) + ' m</b>';
}

LK.slider('ang', function (v) {
  s.ang = v;
  document.getElementById('angv').textContent = v + '\u00B0';
});

st.draw = draw;
