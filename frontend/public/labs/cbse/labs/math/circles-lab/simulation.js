'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, r: 80, th: 60 };

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var cx = w / 2, cy = h / 2 + 6;
  var r = Math.min(s.r, Math.min(w, h) / 2 - 50);

  // circle
  ctx.strokeStyle = '#f97316'; ctx.lineWidth = 3.5;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = 'rgba(249,115,22,.05)'; ctx.fill();
  // centre
  ctx.fillStyle = '#0f1b33';
  ctx.beginPath(); ctx.arc(cx, cy, 4, 0, Math.PI * 2); ctx.fill();
  ctx.font = '600 12px Inter, sans-serif';
  ctx.fillText('O', cx + 8, cy - 8);

  if (s.mode === 0) {
    // chord at angle span th
    var half = s.th * Math.PI / 360;   // half-angle
    var p1 = { x: cx + Math.cos(-half) * r, y: cy + Math.sin(-half) * r };
    var p2 = { x: cx + Math.cos(half) * r, y: cy + Math.sin(half) * r };
    ctx.strokeStyle = '#0369a1'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
    // perpendicular from centre bisects chord
    var mid = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
    ctx.strokeStyle = '#b45309'; ctx.setLineDash([6, 5]); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(mid.x, mid.y); ctx.stroke();
    ctx.setLineDash([]);
    // right angle mark
    ctx.strokeStyle = '#98a2b3'; ctx.lineWidth = 1.5;
    ctx.strokeRect(mid.x - 6, mid.y - 6, 6, 6);
    ctx.fillStyle = '#0369a1'; ctx.font = '600 12px Inter, sans-serif';
    ctx.fillText('chord', mid.x - 20, mid.y - 12);
    var dOM = Math.hypot(mid.x - cx, mid.y - cy);
    var halfLen = Math.hypot(p1.x - mid.x, p1.y - mid.y);
    document.getElementById('out1').innerHTML = 'Chord length AB = 2r·sin(θ/2) = <b>' + (2 * r * Math.sin(s.th * Math.PI / 360) / 10).toFixed(1) + ' cm</b>';
    document.getElementById('out2').innerHTML = 'OM (centre→chord) = r·cos(θ/2) = <b>' + (Math.cos(s.th * Math.PI / 360) * r / 10).toFixed(1) + ' cm</b>';
    document.getElementById('out3').innerHTML = 'OM ⊥ AB and AM = MB = <b>' + (halfLen / 10).toFixed(1) + ' cm</b> — the bisecting theorem ✓';
  } else if (s.mode === 1) {
    // tangent at angle th
    var a = s.th * Math.PI / 180;
    var pt = { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
    // radius
    ctx.strokeStyle = '#b45309'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(pt.x, pt.y); ctx.stroke();
    // tangent line (perpendicular to radius)
    var t1 = { x: pt.x + Math.sin(a) * 200, y: pt.y - Math.cos(a) * 200 };
    var t2 = { x: pt.x - Math.sin(a) * 200, y: pt.y + Math.cos(a) * 200 };
    ctx.strokeStyle = '#0369a1'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(t1.x, t1.y); ctx.lineTo(t2.x, t2.y); ctx.stroke();
    // right-angle mark
    ctx.save(); ctx.translate(pt.x, pt.y); ctx.rotate(a);
    ctx.strokeStyle = '#dc2626'; ctx.lineWidth = 2;
    ctx.strokeRect(-16, -16, 16, 16);
    ctx.restore();
    ctx.fillStyle = '#0369a1';
    ctx.fillText('tangent (touches at exactly ONE point)', pt.x + 12, pt.y - 10);
    document.getElementById('out1').innerHTML = 'Radius OT = <b>' + (r / 10).toFixed(1) + ' cm</b>, tangent ⊥ radius at T — the 90° rule ✓';
    document.getElementById('out2').innerHTML = 'Tangent length from external point P at distance d: √(d² − r²)';
    document.getElementById('out3').innerHTML = 'Two tangents from the same external point are <b>equal in length</b>.';
  } else {
    // sector
    var a0 = -s.th * Math.PI / 360, a1 = s.th * Math.PI / 360;
    ctx.fillStyle = 'rgba(3,105,161,.18)';
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, r, a0, a1); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = '#0369a1'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a0) * r, cy + Math.sin(a0) * r);
    ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a1) * r, cy + Math.sin(a1) * r); ctx.stroke();
    // arc highlight
    ctx.strokeStyle = '#dc2626'; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.arc(cx, cy, r, a0, a1); ctx.stroke();
    ctx.strokeStyle = '#98a2b3'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(cx, cy, 34, a0, a1); ctx.stroke();
    ctx.fillStyle = '#6b7891';
    ctx.fillText('θ=' + s.th + '°', cx + 40, cy - 8);
    var R = r / 10;
    var sectorArea = Math.PI * R * R * s.th / 360;
    var arcLen = 2 * Math.PI * R * s.th / 360;
    document.getElementById('out1').innerHTML = 'Sector area = (θ/360)·πr² = <b>' + sectorArea.toFixed(1) + ' cm²</b>';
    document.getElementById('out2').innerHTML = 'Arc length = (θ/360)·2πr = <b>' + arcLen.toFixed(1) + ' cm</b>';
    document.getElementById('out3').innerHTML = 'Full circle: area <b>' + (Math.PI * R * R).toFixed(0) + ' cm²</b> · circumference <b>' + (2 * Math.PI * R).toFixed(0) + ' cm</b>';
  }
}

LK.segment('modeSeg', function (i) { s.mode = i; draw(); });
LK.slider('r', function (v) { s.r = v; document.getElementById('rv').textContent = v; draw(); });
LK.slider('th', function (v) { s.th = v; document.getElementById('thv').textContent = v + '°'; draw(); });
st.draw = draw; draw();
