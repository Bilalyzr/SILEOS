'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, cur: 2, dir: 1, t: 0 };

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  s.t += 0.016;
  if (s.mode === 0) drawWire(ctx, w, h);
  else drawSolenoid(ctx, w, h);
}

/* compass needle helper: angle of needle given field direction */
function compass(ctx, x, y, ang, size) {
  size = size || 26;
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.arc(x, y, size * 0.72, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2; ctx.stroke();
  ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
  ctx.fillStyle = '#ef4444';
  ctx.beginPath(); ctx.moveTo(size * 0.58, 0); ctx.lineTo(-2, -size * 0.16); ctx.lineTo(-2, size * 0.16); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#64748b';
  ctx.beginPath(); ctx.moveTo(-size * 0.58, 0); ctx.lineTo(-2, -size * 0.16); ctx.lineTo(-2, size * 0.16); ctx.closePath(); ctx.fill();
  ctx.restore();
}

function drawWire(ctx, w, h) {
  var cy = h / 2;
  // wire (into/out of screen style is confusing; use vertical wire across screen)
  var wx = w * 0.42;
  var I = s.cur * s.dir;

  // field circles around the wire
  var maxR = Math.min(w - wx, wx, h / 2) - 26;
  for (var r = 42; r <= maxR; r += 42) {
    var alpha = LK.clamp(s.cur / 5, 0, 1) * 0.75;
    ctx.strokeStyle = 'rgba(79,70,229,' + alpha + ')';
    ctx.lineWidth = 2.2;
    // dashed circles that rotate with current direction
    ctx.save();
    ctx.translate(wx, cy);
    ctx.rotate(s.t * s.cur * 0.35 * s.dir);
    ctx.setLineDash([14, 10]);
    ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke();
    ctx.restore();
    // direction arrowheads on the circle
    var a = s.t * s.cur * 0.35 * s.dir;
    for (var k = 0; k < 4; k++) {
      var th = a + k * Math.PI / 2;
      var ax = wx + Math.cos(th) * r, ay = cy + Math.sin(th) * r;
      LK.arrow(ctx, ax, ay, th + Math.PI / 2 * (I >= 0 ? 1 : -1), 'rgba(79,70,229,' + alpha + ')', 8);
    }
  }
  ctx.setLineDash([]);

  // the wire
  ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 7;
  ctx.beginPath(); ctx.moveTo(wx, 30); ctx.lineTo(wx, h - 30); ctx.stroke();
  // current direction arrows + moving carriers
  var carriers = 9;
  for (var c = 0; c < carriers; c++) {
    var yy = ((s.t * 90 * s.dir * s.cur / 2 + c * (h - 60) / carriers) % (h - 60) + (h - 60)) % (h - 60) + 30;
    ctx.fillStyle = '#2563eb';
    ctx.beginPath(); ctx.arc(wx, yy, 5, 0, Math.PI * 2); ctx.fill();
  }
  // battery
  battery(ctx, wx, 6, I);
  // compasses around
  var comps = [[wx - 150, cy - 110], [wx + 150, cy - 110], [wx - 190, cy], [wx + 190, cy], [wx - 150, cy + 110], [wx + 150, cy + 110]];
  comps.forEach(function (cp) {
    // field tangent at that point
    var dx = cp[0] - wx, dy = cp[1] - cy;
    var tangent = Math.atan2(-dx, dy) * s.dir * Math.sign(s.cur || 1);
    if (s.cur === 0) tangent = -Math.PI / 2;   // Earth's field: north!
    compass(ctx, cp[0], cp[1], tangent, 30);
  });
  document.getElementById('fieldRead').innerHTML = s.cur === 0
    ? 'Current <b>0 A</b> — compasses point to geographic north (Earth\u2019s field only).'
    : 'Current <b>' + (s.cur * 1) + ' A</b> ' + (s.dir > 0 ? '↑ upward' : '↓ downward') +
      ' — concentric field ' + (s.dir > 0 ? 'anticlockwise' : 'clockwise') + ' (seen from above). Doubling current doubles the field strength.';
}

function drawSolenoid(ctx, w, h) {
  var cy = h / 2;
  var I = s.cur * s.dir;
  var coilW = Math.min(w * 0.5, 420), coilH = 130;
  var x0 = w / 2 - coilW / 2;
  var loops = 8;

  // field lines through the core + returning outside
  ctx.lineWidth = 2;
  var strength = s.cur / 5;
  // inner straight lines
  [-1, 0, 1].forEach(function (k) {
    var y = cy + k * 34;
    ctx.strokeStyle = 'rgba(79,70,229,' + LK.clamp(strength, 0.05, 0.85) + ')';
    ctx.beginPath();
    ctx.moveTo(x0 + 30, y);
    ctx.lineTo(x0 + coilW - 30, y);
    ctx.stroke();
    // big return loop
    ctx.beginPath();
    ctx.moveTo(x0 + coilW - 30, y);
    ctx.bezierCurveTo(x0 + coilW + 120, y, x0 + coilW + 120, cy + k * 220 + (k === 0 ? 160 : 0) * 0, x0 + coilW / 2, cy + (k === 0 ? 170 : k * 210));
    ctx.bezierCurveTo(x0 - 120, cy + k * 210 - (k === 0 ? 0 : 0), x0 - 120, y, x0 + 30, y);
    ctx.stroke();
    // arrows along core
    var ax = x0 + coilW * 0.5 + Math.sin(s.t * 2) * coilW * 0.3;
    LK.arrow(ctx, ax, y, I >= 0 ? 0 : Math.PI, 'rgba(79,70,229,.9)', 10);
  });

  // coil loops
  for (var l = 0; l <= loops; l++) {
    var lx = x0 + (coilW * l) / loops;
    ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.ellipse(lx, cy, 20, coilH / 2, 0, 0, Math.PI * 2);
    ctx.stroke();
    // current carriers racing around the loop
    var ph = (s.t * 6 * s.dir * (s.cur / 2 + 0.3) + l) % 1;
    var ang = ph * Math.PI * 2;
    ctx.fillStyle = '#2563eb';
    ctx.beginPath();
    ctx.arc(lx + Math.cos(ang) * 20, cy + Math.sin(ang) * coilH / 2, 4.5, 0, Math.PI * 2);
    ctx.fill();
  }
  // N and S labels (flip with direction)
  var nSide = I >= 0 ? 0 : 1;
  ctx.fillStyle = '#ef4444'; ctx.font = 'bold 34px Georgia, serif';
  ctx.fillText(nSide === 0 ? 'N' : 'S', x0 - 44, cy + 12);
  ctx.fillStyle = '#3b82f6';
  ctx.fillText(nSide === 0 ? 'S' : 'N', x0 + coilW + 22, cy + 12);

  document.getElementById('fieldRead').innerHTML = s.cur === 0
    ? 'No current — the coil is just a wire spiral, no magnetism.'
    : 'Solenoid with ' + loops + ' loops, <b>' + s.cur + ' A</b>: field lines run straight inside ' +
      (s.dir > 0 ? 'left→right (N on the right)' : 'right→left (N on the left)') +
      ' and loop back outside — exactly like a bar magnet. More loops or more current = stronger electromagnet.';
}

function battery(ctx, x, y, I) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = '#fff'; ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2;
  ctx.fillRect(-26, -1, 52, 26);
  ctx.strokeRect(-26, -1, 52, 26);
  ctx.fillStyle = LK.C.sub; ctx.font = 'bold 12px system-ui, sans-serif';
  ctx.fillText((Math.abs(I)).toFixed(1) + 'A', -12, 17);
  ctx.fillStyle = LK.C.ok;
  ctx.fillText(I >= 0 ? '↑' : '↓', 20, 17);
  ctx.restore();
}

LK.segment('modeSeg', function (i) { s.mode = i; });
LK.slider('cur', function (v) {
  s.cur = v;
  document.getElementById('curv').textContent = v.toFixed(1) + ' A';
});
LK.button('revBtn', function () { s.dir *= -1; });

st.draw = draw;
