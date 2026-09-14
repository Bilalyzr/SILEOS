'use strict';
var st = LK.setupCanvas(document.getElementById('cv'));
var s = { pH: 7 };

// universal-indicator rainbow, pH 0..14
var RAMP = ['#c62828', '#e53935', '#f4511e', '#fb8c00', '#ffb300', '#fdd835',
            '#c0ca33', '#7cb342', '#43a047', '#00897b', '#00acc1', '#039be5',
            '#5e35b1', '#7e57c2', '#4527a0'];
function rampColor(ph) { return RAMP[Math.max(0, Math.min(14, Math.round(ph)))]; }

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);

  /* ---- pH colour scale ---- */
  var barX = 60, barW = w - 120, barY = 70, barH = 34;
  var n = RAMP.length, segW = barW / 14;
  for (var i = 0; i < n; i++) {
    ctx.fillStyle = RAMP[i];
    ctx.fillRect(barX + i * segW, barY, segW + 1, barH);
  }
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2;
  ctx.strokeRect(barX, barY, barW, barH);
  ctx.font = '12px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  for (var t = 0; t <= 14; t++) {
    ctx.textAlign = 'center';
    ctx.fillText(String(t), barX + t * segW, barY + barH + 18);
  }
  ctx.textAlign = 'start';
  ctx.font = '600 14px system-ui, sans-serif';
  ctx.fillText('acidic', barX, barY - 12);
  ctx.fillText('neutral', barX + 7 * segW - 24, barY - 12);
  ctx.fillText('basic', barX + barW - 42, barY - 12);

  // marker
  var mx = barX + s.pH / 14 * barW;
  LK.arrow(ctx, mx, barY - 26, Math.PI / 2, LK.C.ink, 12);
  ctx.fillStyle = LK.C.ink; ctx.font = 'bold 14px system-ui, sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(s.name, mx, barY - 34);
  ctx.textAlign = 'start';

  /* ---- beaker with indicator colour ---- */
  var bx = w / 2 - 110, by = barY + barH + 70, bw = 220, bh = 210;
  var fillFrac = 0.62;
  ctx.save();
  ctx.strokeStyle = '#64748b'; ctx.lineWidth = 5;
  // beaker outline with spout
  ctx.beginPath();
  ctx.moveTo(bx - 8, by);
  ctx.lineTo(bx, by); ctx.lineTo(bx, by + bh);
  ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by);
  ctx.lineTo(bx + bw + 8, by);
  ctx.stroke();
  // liquid
  var topY = by + bh * (1 - fillFrac);
  ctx.fillStyle = rampColor(s.pH);
  ctx.globalAlpha = 0.85;
  ctx.fillRect(bx + 2.5, topY, bw - 5, by + bh - topY - 2.5);
  ctx.globalAlpha = 1;
  // surface line
  ctx.strokeStyle = rampColor(s.pH); ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(bx + 2.5, topY); ctx.lineTo(bx + bw - 2.5, topY); ctx.stroke();
  // bubbles for acids / bases character
  ctx.fillStyle = 'rgba(255,255,255,.55)';
  for (var b = 0; b < 6; b++) {
    var bxp = bx + 30 + ((b * 47 + (s.pH * 13) % 40) % (bw - 60));
    var byp = topY + 30 + ((b * 61) % (bh * fillFrac - 55));
    ctx.beginPath(); ctx.arc(bxp, byp, 3.5, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();

  /* ---- litmus strips ---- */
  var ly = by + bh - 40;
  strip(bx - 120, ly, '#ef4444', s.pH < 7 ? '#c62828' : (s.pH > 7 ? '#7c3aed' : '#ef4444'));
  strip(bx - 120, ly + 44, '#3b82f6', s.pH < 7 ? '#c62828' : (s.pH > 7 ? '#3b82f6' : '#3b82f6'));
  ctx.font = '12.5px system-ui, sans-serif'; ctx.fillStyle = LK.C.sub;
  ctx.fillText('red litmus', bx - 120, ly + 62);
  ctx.fillText('blue litmus', bx - 120, ly + 106);

  function strip(x, y, before, after) {
    ctx.fillStyle = before; ctx.globalAlpha = 0.35;
    ctx.fillRect(x, y, 60, 26);
    ctx.globalAlpha = 1;
    ctx.fillStyle = after; ctx.fillRect(x, y, 60, 26);
    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1; ctx.strokeRect(x, y, 60, 26);
    ctx.fillStyle = LK.C.sub; ctx.font = '11px system-ui, sans-serif';
    ctx.fillText('dipped', x + 8, y + 17);
  }
}

function upd() {
  var kind = s.pH < 7 ? 'ACIDIC' : s.pH > 7 ? 'BASIC (alkaline)' : 'NEUTRAL';
  var phEl = document.getElementById('phRead');
  phEl.textContent = 'pH ' + s.pH.toFixed(1);
  phEl.style.color = rampColor(s.pH);
  document.getElementById('kind').innerHTML = 'This solution is <b>' + kind + '</b>';
  var h = Math.pow(10, -s.pH);
  document.getElementById('hConc').innerHTML = '[H\u207A] \u2248 10<sup>' + LK.fmt(-s.pH, 1) + '</sup> mol/L';
  var red = s.pH < 7 ? 'stays red' : s.pH > 7 ? 'stays red' : 'no change (stays red)';
  var blue = s.pH < 7 ? 'turns RED' : s.pH > 7 ? 'stays blue' : 'no change (stays blue)';
  document.getElementById('litmus').innerHTML =
    'Blue litmus: <b>' + blue + '</b><br>Red litmus: <b>' + (s.pH > 7 ? 'turns BLUE' : red) + '</b>';
}

document.getElementById('substance').addEventListener('change', function () {
  s.pH = parseFloat(this.value);
  s.name = this.options[this.selectedIndex].text.replace(/\s*\(.*\)/, '');
  upd();
});
var sel = document.getElementById('substance');
s.name = sel.options[sel.selectedIndex].text;
st.draw = draw; upd();
