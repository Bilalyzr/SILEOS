'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));

var ORDER = ['K', 'Na', 'Ca', 'Mg', 'Al', 'Zn', 'Fe', 'Pb', 'H', 'Cu', 'Ag', 'Au'];
var METAL_COLOR = { K: '#a3e635', Na: '#a3e635', Ca: '#e2e8f0', Mg: '#e2e8f0', Al: '#cbd5e1',
                    Zn: '#94a3b8', Fe: '#78716c', Pb: '#64748b', H: null, Cu: '#d97706', Ag: '#c0c8d4', Au: '#fbbf24' };
var SOLUTIONS = [
  { name: 'Copper sulphate', formula: 'CuSO₄', metal: 'Cu', color: '#2ea8e6', deposit: '#d97706' },
  { name: 'Iron(II) sulphate', formula: 'FeSO₄', metal: 'Fe', color: '#7fae72', deposit: '#78716c' },
  { name: 'Zinc sulphate', formula: 'ZnSO₄', metal: 'Zn', color: '#e8edf5', deposit: '#94a3b8' },
  { name: 'Silver nitrate', formula: 'AgNO₃', metal: 'Ag', color: '#dfe7f0', deposit: '#c0c8d4' },
  { name: 'Magnesium sulphate', formula: 'MgSO₄', metal: 'Mg', color: '#eef2f7', deposit: '#e2e8f0' }
];
var METALS = ['K', 'Na', 'Ca', 'Mg', 'Zn', 'Fe', 'Cu', 'Ag', 'Au'];

var s = { sol: 0, met: null, anim: 0, result: null };

function renderChips() {
  document.getElementById('solBox').innerHTML = SOLUTIONS.map(function (so, i) {
    return '<div class="miniBeaker' + (i === s.sol ? ' sel' : '') + '" data-i="' + i + '">' +
      '<canvas width="34" height="40" data-sol="' + i + '"></canvas>' +
      '<div class="nm">' + so.formula + '</div></div>';
  }).join('');
  document.querySelectorAll('#solBox .miniBeaker').forEach(function (b) {
    b.addEventListener('click', function () {
      s.sol = +b.getAttribute('data-i'); s.met = null; s.result = null;
      renderChips();
    });
  });
  // tiny beaker icons
  document.querySelectorAll('canvas[data-sol]').forEach(function (cv) {
    var i = +cv.getAttribute('data-sol');
    var c2 = cv.getContext('2d');
    c2.fillStyle = SOLUTIONS[i].color;
    c2.fillRect(6, 14, 22, 22);
    c2.strokeStyle = '#334155'; c2.lineWidth = 2;
    c2.strokeRect(5, 8, 24, 30);
  });

  var solMetal = SOLUTIONS[s.sol].metal;
  document.getElementById('metBox').innerHTML = METALS.map(function (m) {
    return '<span class="metalChip' + (m === s.met ? ' sel' : '') + '"' +
      ' data-m="' + m + '" style="color:' + (m === s.met ? '#fff' : METAL_COLOR[m]) + ';">' + m + '</span>';
  }).join('');
  document.querySelectorAll('#metBox .metalChip').forEach(function (c) {
    c.addEventListener('click', function () {
      s.met = c.getAttribute('data-m');
      drop();
      renderChips();
    });
  });
}

function drop() {
  var so = SOLUTIONS[s.sol];
  var reactive = ORDER.indexOf(s.met) < ORDER.indexOf(so.metal);
  s.result = reactive
    ? { react: true, product: so.metal,
        eq: s.met + ' + ' + so.formula.replace(/(\d+)/g, '$_{$1}') + ' → ' + so.metal + ' + ' + so.formula.replace(so.metal, s.met) }
    : { react: false, why: s.met + ' is below ' + so.metal + ' in the reactivity series — no electron push, no reaction.' };
  s.anim = 0;
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  var so = SOLUTIONS[s.sol];
  var bx = w / 2 - 130, by = h * 0.16, bw = 260, bh = h * 0.58;
  var liquidH = bh * 0.68;

  // beaker
  ctx.fillStyle = so.color; ctx.globalAlpha = 0.9;
  ctx.fillRect(bx + 3, by + bh - liquidH, bw - 6, liquidH - 3);
  ctx.globalAlpha = 1;
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(bx - 8, by); ctx.lineTo(bx, by); ctx.lineTo(bx, by + bh);
  ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by); ctx.lineTo(bx + bw + 8, by);
  ctx.stroke();
  ctx.fillStyle = LK.C.sub; ctx.font = '600 14px system-ui, sans-serif';
  ctx.fillText(so.name + '  (' + so.formula + ')', bx, by + bh + 28);

  // metal strip
  if (s.met) {
    s.anim = Math.min(1, s.anim + 0.012);
    var dropY = by + 30 + (by + bh - liquidH + 40 - by - 30) * s.anim;
    var stripH = 120;
    var stripCol = s.result && s.result.react && s.anim > 0.75 ? so.deposit : (METAL_COLOR[s.met] || '#94a3b8');
    ctx.save();
    ctx.translate(w / 2 + 10, dropY);
    ctx.rotate(-0.12);
    ctx.fillStyle = stripCol;
    LK.roundRect(ctx, -14, -stripH / 2, 28, stripH, 7); ctx.fill();
    ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#fff'; ctx.font = 'bold 13px system-ui, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(s.met, 0, 5);
    ctx.textAlign = 'start';
    ctx.restore();

    // deposit particles after reaction
    if (s.result && s.result.react && s.anim > 0.55) {
      var t = (s.anim - 0.55) / 0.45;
      ctx.fillStyle = so.deposit;
      for (var p = 0; p < 22; p++) {
        var ang = p * 2.39996;
        var rr = t * 40 + (p % 3) * 6;
        var px0 = w / 2 + 10 + Math.cos(ang) * rr;
        var py0 = dropY + Math.sin(ang) * rr * 0.7;
        ctx.beginPath(); ctx.arc(px0, py0, 3.2, 0, Math.PI * 2); ctx.fill();
      }
      // bubbles for very reactive metals
      if (s.met === 'K' || s.met === 'Na' || s.met === 'Ca') {
        ctx.fillStyle = 'rgba(255,255,255,.85)';
        for (var bb = 0; bb < 8; bb++) {
          var bxx = w / 2 + LK.rand(-30, 30);
          var byy = dropY - 30 - ((s.anim * 500 + bb * 60) % 140);
          ctx.beginPath(); ctx.arc(bxx, byy, 3, 0, Math.PI * 2); ctx.fill();
        }
      }
    }

    var obsEl = document.getElementById('obs');
    if (!s.result.react) {
      obsEl.innerHTML = '❌ <b>No reaction.</b> ' + s.result.why;
    } else if (s.anim < 0.55) {
      obsEl.innerHTML = 'Dropping ' + s.met + ' into ' + so.formula + '…';
    } else {
      var extra = (s.met === 'K' || s.met === 'Na' || s.met === 'Ca') ? ' (fizzing violently — these metals even react with water!)' : '';
      obsEl.innerHTML = '✅ <b>Displacement!</b> ' + s.met + ' pushes out ' + so.metal +
        ': the strip gets a ' + so.metal + ' coating' + extra +
        '<br><span style="font-family:Georgia,serif;font-size:16px;">' + s.met + ' + ' + so.formula + ' → ' + s.met + 'SO₄' +
        (so.metal === 'Ag' ? ' + Ag↓' : ' + ' + so.metal + '↓') + '</span>';
    }
  } else {
    document.getElementById('obs').innerHTML = 'Pick a metal strip to drop into ' + so.formula + '.';
  }
}

renderChips();
st.draw = draw;
