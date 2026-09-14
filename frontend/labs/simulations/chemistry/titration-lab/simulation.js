'use strict';
var VA = 25; // mL acid
var s = { ca: 0.1, cb: 0.1, vb: 0, auto: false };
var st = LK.setupCanvas(document.getElementById('cv'));
var drip = 0;

function phAt(ca, cb, vb) {
  var excess = VA * ca - vb * cb;              // mmol of H+ (+) or OH- (-)
  var vt = VA + vb;
  if (Math.abs(excess) < 1e-9) return 7;
  if (excess > 0) return -Math.log10(excess / vt);
  return 14 + Math.log10(-excess / vt);
}
function eqVol() { return VA * s.ca / s.cb; }

function add(ml) {
  var before = phAt(s.ca, s.cb, s.vb);
  s.vb = Math.min(s.vb + ml, eqVol() * 2 + 10);
  var after = phAt(s.ca, s.cb, s.vb);
  if (before < 8.2 && after >= 8.2) flash = 1;   // pink flash at end point
  upd();
}
var flash = 0;

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  if (s.auto) { add(0.02); drip = 1; }
  if (flash > 0) flash -= 0.02;
  if (drip > 0) drip -= 0.03;

  var pH = phAt(s.ca, s.cb, s.vb);
  var ve = eqVol();

  /* ---------- burette + flask (left side) ---------- */
  var cx = w * 0.27;
  // burette
  var bx = cx + 60, bt = 40, bb = 210;
  ctx.fillStyle = '#e2e8f0'; ctx.fillRect(bx - 11, bt, 22, bb - bt);
  // NaOH level
  var used = Math.min(1, s.vb / (2 * ve + 5));
  ctx.fillStyle = '#93c5fd';
  ctx.fillRect(bx - 9, bt + 4, 18, (bb - bt - 20) * (1 - used));
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5;
  ctx.strokeRect(bx - 11, bt, 22, bb - bt);
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(bx, bb); ctx.lineTo(bx, bb + 26); ctx.stroke();
  ctx.fillStyle = LK.C.sub; ctx.font = '12.5px system-ui, sans-serif';
  ctx.fillText('NaOH ' + s.cb.toFixed(2) + ' M', bx + 20, bt + 16);
  ctx.fillText(s.vb.toFixed(2) + ' mL used', bx + 20, bt + 34);
  // drop
  if (s.auto || drip > 0) {
    var dy = bb + 26 + ((s.t2 = (s.t2 || 0) + 0.06) % 1) * (280 - bb - 26);
    ctx.fillStyle = '#3b82f6';
    ctx.beginPath(); ctx.ellipse(bx, dy, 3.2, 5.5, 0, 0, Math.PI * 2); ctx.fill();
  }

  // flask
  var fx = cx - 90, fy = 285, fw = 180, fh = 130;
  var liquidH = fh * 0.62;
  var pink = LK.clamp((pH - 8.2) / 2, 0, 1);
  var baseCol = [252, 231, 243]; // near-white
  var pinkCol = [236, 72, 153];
  var col = baseCol.map(function (c0, i) { return Math.round(c0 + (pinkCol[i] - c0) * pink); });
  ctx.fillStyle = 'rgb(' + col.join(',') + ')';
  ctx.globalAlpha = 0.92;
  ctx.beginPath();
  ctx.moveTo(fx + 30, fy); ctx.lineTo(fx + 30, fy + 40);
  ctx.lineTo(fx, fy + fh); ctx.lineTo(fx + fw, fy + fh);
  ctx.lineTo(fx + fw - 30, fy + 40); ctx.lineTo(fx + fw - 30, fy);
  ctx.closePath(); ctx.fill();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 3; ctx.stroke();
  // flash ring at end point
  if (flash > 0) {
    ctx.strokeStyle = 'rgba(236,72,153,' + flash + ')';
    ctx.lineWidth = 6;
    ctx.strokeRect(fx - 6, fy - 6, fw + 12, fh + 6);
  }
  ctx.fillStyle = LK.C.sub; ctx.font = '13px system-ui, sans-serif';
  ctx.fillText(pH >= 8.2 ? 'phenolphthalein: PINK — base in excess' : 'phenolphthalein: colourless', fx - 10, fy + fh + 24);
  if (Math.abs(s.vb - ve) < 0.05) {
    ctx.fillStyle = LK.C.ok; ctx.font = 'bold 14px system-ui, sans-serif';
    ctx.fillText('\u2713 EQUIVALENCE POINT!', fx + 30, fy - 12);
  }

  /* ---------- pH curve (right side) ---------- */
  var gx0 = w * 0.52, gx1 = w - 46, gy0 = 50, gy1 = h - 60;
  var vMax = ve * 2;
  var TX = function (v) { return gx0 + (v / vMax) * (gx1 - gx0); };
  var PY = function (p) { return gy1 - (p / 14) * (gy1 - gy0); };
  ctx.strokeStyle = LK.C.axis; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(gx0, gy0); ctx.lineTo(gx0, gy1); ctx.lineTo(gx1, gy1); ctx.stroke();
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  for (var p = 0; p <= 14; p += 2) {
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(gx0, PY(p)); ctx.lineTo(gx1, PY(p)); ctx.stroke();
    ctx.fillText(String(p), gx0 - 20, PY(p) + 4);
  }
  for (var v = 0; v <= vMax; v += Math.max(5, Math.round(vMax / 8 / 5) * 5)) {
    ctx.strokeStyle = LK.C.grid2;
    ctx.beginPath(); ctx.moveTo(TX(v), gy0); ctx.lineTo(TX(v), gy1); ctx.stroke();
    ctx.fillText(String(v), TX(v) - 6, gy1 + 18);
  }
  // equivalence volume line
  ctx.strokeStyle = LK.C.ok; ctx.setLineDash([7, 6]); ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(TX(ve), gy0); ctx.lineTo(TX(ve), gy1); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = LK.C.ok; ctx.font = '600 12.5px system-ui, sans-serif';
  ctx.fillText('Veq = ' + ve.toFixed(1) + ' mL', TX(ve) + 8, gy0 + 14);
  ctx.fillStyle = LK.C.sub;
  ctx.fillText('pH vs volume of NaOH (mL)', gx0, gy0 - 16);
  // recorded curve
  ctx.strokeStyle = LK.C.brand; ctx.lineWidth = 3;
  ctx.beginPath();
  for (var vv = 0; vv <= s.vb; vv += vMax / 240) {
    var py = PY(phAt(s.ca, s.cb, vv));
    vv ? ctx.lineTo(TX(vv), py) : ctx.moveTo(TX(vv), py);
  }
  ctx.stroke();
  var cy2 = PY(phAt(s.ca, s.cb, s.vb));
  ctx.fillStyle = LK.C.brand;
  ctx.beginPath(); ctx.arc(TX(s.vb), cy2, 6, 0, Math.PI * 2); ctx.fill();
}

function upd() {
  var pH = phAt(s.ca, s.cb, s.vb);
  var big = document.getElementById('phBig');
  big.textContent = 'pH ' + pH.toFixed(1);
  big.style.color = pH < 6.5 ? '#c62828' : pH > 7.5 ? '#7e57c2' : '#16a34a';
  document.getElementById('vbRead').innerHTML = 'NaOH added: <b>' + s.vb.toFixed(2) + ' mL</b>';
  var ve = eqVol();
  var st2 = s.vb < ve - 0.001 ? 'Before equivalence (acid in excess)' :
            s.vb > ve + 0.001 ? 'After equivalence (base in excess)' : 'AT EQUIVALENCE — only NaCl + water';
  document.getElementById('eqRead').innerHTML =
    'Equivalence at <b>' + ve.toFixed(1) + ' mL</b><br>' + st2;
}

LK.slider('ca', function (v) { s.ca = v; document.getElementById('cav').textContent = v.toFixed(2) + ' M'; s.vb = 0; upd(); });
LK.slider('cb', function (v) { s.cb = v; document.getElementById('cbv').textContent = v.toFixed(2) + ' M'; s.vb = 0; upd(); });
LK.button('add1', function () { s.auto = false; add(1); });
LK.button('add01', function () { s.auto = false; add(0.1); });
LK.button('autoBtn', function () { s.auto = !s.auto; this.textContent = s.auto ? '⏸ Stop auto-titrate' : '▶ Auto-titrate (drop by drop)'; });
LK.button('resetBtn', function () { s.vb = 0; s.auto = false; document.getElementById('autoBtn').textContent = '▶ Auto-titrate (drop by drop)'; upd(); });

upd();
st.draw = draw;
