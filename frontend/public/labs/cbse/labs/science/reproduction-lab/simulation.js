'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, p: 0, play: false };

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var cx = w / 2, cy = h / 2;
  var u = s.p / 100;

  if (s.mode === 0) {
    // amoeba binary fission: elongate → nucleus divides → cytoplasm splits
    var elong = 1 + u * 1.4;
    ctx.fillStyle = 'rgba(5,150,105,.15)';
    ctx.strokeStyle = '#059669'; ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.ellipse(cx, cy, 70 * elong, 62, 0, 0, Math.PI * 2);
    ctx.fill(); ctx.stroke();
    // nucleus (divides)
    var sep = u * 70 * elong * 0.55;
    [-sep, sep].forEach(dx => {
      ctx.fillStyle = '#0369a1';
      ctx.beginPath(); ctx.arc(cx + dx * (u > 0.55 ? 1 : 0), cy, 17, 0, Math.PI * 2); ctx.fill();
    });
    if (u < 0.55) {
      ctx.fillStyle = '#0369a1';
      ctx.beginPath(); ctx.arc(cx, cy, 17, 0, Math.PI * 2); ctx.fill();
    }
    // split waist
    if (u > 0.6) {
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 8 + (u - 0.6) * 30;
      ctx.beginPath(); ctx.moveTo(cx, cy - 63); ctx.lineTo(cx, cy + 63); ctx.stroke();
    }
    document.getElementById('explain').innerHTML = u < 0.4 ? '<b>Amoeba</b>: the cell grows and genetic material duplicates…'
      : u < 0.7 ? 'The nucleus <b>divides first</b>, then the cytoplasm pinches inward…'
      : 'Two identical daughter cells — <b>binary fission</b> complete! One parent → two clones.';
  } else if (s.mode === 1) {
    // yeast budding
    ctx.fillStyle = 'rgba(180,83,9,.14)'; ctx.strokeStyle = '#b45309'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(cx - 40, cy, 52, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#fde68a';
    ctx.beginPath(); ctx.arc(cx - 40, cy, 18, 0, Math.PI * 2); ctx.fill();
    var budR = 6 + u * 40;
    var budX = cx + 26 + u * 16, budY = cy - 30 - u * 14;
    ctx.fillStyle = 'rgba(249,115,22,.20)'; ctx.strokeStyle = '#ea580c';
    ctx.beginPath(); ctx.arc(budX, budY, budR, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    if (u > 0.7) {
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 5;
      ctx.beginPath(); ctx.moveTo(budX - budR * 0.8, budY + budR * 0.8); ctx.lineTo(budX - budR * 0.4 - 6, budY + budR); ctx.stroke();
    }
    if (u > 0.85) {
      ctx.fillStyle = 'rgba(249,115,22,.20)';
      ctx.beginPath(); ctx.arc(budX + 30, budY - 34, budR * 0.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    document.getElementById('explain').innerHTML = u < 0.35 ? '<b>Yeast</b>: a bulge swells out of the parent cell…'
      : u < 0.75 ? 'The bud grows; the nucleus divides and one copy moves in…'
      : 'The bud pinches off — a new yeast cell! <b>Budding</b> can even leave chain scars.';
  } else if (s.mode === 2) {
    // rhizopus sporangia bursting
    ctx.strokeStyle = '#6b7891'; ctx.lineWidth = 5;
    for (var hy = 0; hy < 3; hy++) {
      ctx.beginPath();
      ctx.moveTo(cx - 150, cy + 60 - hy * 55);
      ctx.quadraticCurveTo(cx - 60, cy + 70 - hy * 55, cx + hy * 50 - 20, cy - 50 - hy * 40);
      ctx.stroke();
    }
    var sR = 12 + u * 30;
    ctx.fillStyle = 'rgba(51,65,85,.15)'; ctx.strokeStyle = '#0f1b33'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(cx + 40, cy - 90, sR, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // spores fly after 60%
    for (var sp = 0; sp < 14; sp++) {
      var vis = u > 0.6;
      if (!vis) break;
      var ang = sp * 0.449;
      var rr = (u - 0.6) / 0.4 * (90 + (sp % 4) * 30);
      ctx.fillStyle = '#dc2626';
      ctx.beginPath(); ctx.arc(cx + 40 + Math.cos(ang) * rr, cy - 90 + Math.sin(ang) * rr * 0.8, 4.5, 0, Math.PI * 2); ctx.fill();
    }
    document.getElementById('explain').innerHTML = u < 0.5 ? '<b>Bread mould (Rhizopus)</b>: blob-like <b>sporangia</b> swell on stalks…'
      : u < 0.75 ? 'Each sporangium packs hundreds of tiny <b>spores</b>…'
      : 'The case bursts — spores ride the air! Each landing spot can start a new mould. One parent, hundreds of offspring.';
  } else {
    // flower → pollination → seed
    ctx.strokeStyle = '#059669'; ctx.lineWidth = 7;
    ctx.beginPath(); ctx.moveTo(cx, cy + 160); ctx.quadraticCurveTo(cx - 30, cy + 60, cx, cy); ctx.stroke();
    ctx.fillStyle = '#22c55e';
    ctx.beginPath(); ctx.ellipse(cx - 42, cy + 60, 34, 12, -0.6, 0, Math.PI * 2); ctx.fill();
    // petals open with u
    var open = LK.clamp(u * 2, 0, 1);
    for (var pt2 = 0; pt2 < 6; pt2++) {
      var an = pt2 * Math.PI / 3 + 0.3;
      var px0 = cx + Math.cos(an) * 58 * open, py0 = cy - 20 + Math.sin(an) * 58 * open;
      ctx.fillStyle = 'rgba(249,115,22,' + (0.5 + open * 0.4) + ')';
      ctx.beginPath(); ctx.ellipse(px0, py0, 22, 13, an, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = '#b45309';
    ctx.beginPath(); ctx.arc(cx, cy - 20, 14 + open * 4, 0, Math.PI * 2); ctx.fill();
    // pollen flying after 50%
    if (u > 0.5) {
      var fly = (u - 0.5) / 0.5;
      ctx.fillStyle = '#f59e0b';
      for (var f = 0; f < 6; f++) {
        ctx.beginPath();
        ctx.arc(cx + 80 + fly * 120 + f * 14, cy - 70 - Math.sin(f + fly * 5) * 22 - fly * 40, 4, 0, Math.PI * 2);
        ctx.fill();
      }
      // bee
      ctx.font = '26px serif';
      ctx.fillText('🐝', cx + 90 + fly * 100, cy - 60 - Math.sin(fly * 9) * 18);
    }
    if (u > 0.8) {
      ctx.fillStyle = '#059669';
      ctx.beginPath(); ctx.ellipse(cx - 130, cy + 90, 10 + (u - 0.8) * 60, 14, 0.4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#064e3b'; ctx.font = '600 11px Inter, sans-serif';
      ctx.fillText('seed → new plant', cx - 150, cy + 118);
    }
    document.getElementById('explain').innerHTML = u < 0.3 ? 'The flower opens: petals advertise, nectar rewards…'
      : u < 0.55 ? 'Colour + scent + nectar attract pollinators — this is <b>sexual</b> reproduction territory!'
      : u < 0.8 ? '🐝 The bee carries <b>pollen</b> (male cells) to another flower — cross-pollination mixes genes.'
      : 'Fertilised ovule becomes a <b>seed</b>; the cycle restarts. Variety ensured!';
  }
}

LK.segment('modeSeg', function (i) { s.mode = i; s.p = 0; draw(); });
LK.slider('prog', function (v) { s.p = v; document.getElementById('progv').textContent = v + '%'; s.play = false; draw(); });
LK.button('playBtn', function () {
  s.play = true;
  var timer = setInterval(function () {
    if (!s.play) { clearInterval(timer); return; }
    s.p += 1.2;
    if (s.p >= 100) { s.p = 100; s.play = false; clearInterval(timer); }
    document.getElementById('prog').value = s.p;
    document.getElementById('progv').textContent = Math.round(s.p) + '%';
  }, 30);
});
st.draw = draw; draw();
