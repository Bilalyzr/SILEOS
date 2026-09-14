'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { field: true, compass: true, mouse: null, dragging: false };
var W = 90, H = 34;   // magnet size
var mags = [
  { x: 0, y: 0, angle: 0, loose: false },          // fixed
  { x: 210, y: 120, angle: Math.PI, loose: true }  // draggable
];

function center() { return { x: st.w / 2, y: st.h / 2 + 10 }; }
function magRect(m) {
  var c = center();
  return { x: c.x + m.x, y: c.y + m.y };
}
// pole positions of magnet m (local -W/2..W/2 along its angle)
function poles(m) {
  var r = magRect(m), a = m.angle, ca = Math.cos(a), sa = Math.sin(a);
  return {
    n: { x: r.x + ca * W / 2, y: r.y + sa * W / 2, type: 'N' },
    s: { x: r.x - ca * W / 2, y: r.y - sa * W / 2, type: 'S' }
  };
}
function allPoles() {
  var out = [];
  mags.forEach(function (m) { var p = poles(m); out.push(p.n, p.s); });
  return out;
}
// magnetic field at point (dipole monopole approximation)
function fieldAt(x, y) {
  var fx = 0, fy = 0;
  allPoles().forEach(function (p) {
    var dx = x - p.x, dy = y - p.y;
    var d2 = dx * dx + dy * dy + 260;
    var inv = (p.type === 'N' ? 1 : -1) * 2.6e6 / (d2 * Math.sqrt(d2));
    fx += dx * inv; fy += dy * inv;
  });
  return { x: fx, y: fy, len: Math.hypot(fx, fy) };
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#fffdf5'; ctx.fillRect(0, 0, w, h);

  /* field lines traced from N poles */
  if (s.field) {
    ctx.lineWidth = 1.4;
    allPoles().forEach(function (p) {
      if (p.type !== 'N') return;
      for (var k = 0; k < 7; k++) {
        var a0 = k / 7 * Math.PI * 2;
        var x = p.x + Math.cos(a0) * 8, y = p.y + Math.sin(a0) * 8;
        ctx.strokeStyle = 'rgba(79,70,229,0.38)';
        ctx.beginPath(); ctx.moveTo(x, y);
        for (var step = 0; step < 420; step++) {
          var f = fieldAt(x, y);
          if (f.len < 0.05) break;
          x += f.x / f.len * 4.2; y += f.y / f.len * 4.2;
          ctx.lineTo(x, y);
          // stop if we reached an S pole or left screen
          if (x < -30 || x > w + 30 || y < -30 || y > h + 30) break;
          var hitS = allPoles().some(function (q) { return q.type === 'S' && Math.hypot(x - q.x, y - q.y) < 9; });
          if (hitS) break;
        }
        ctx.stroke();
      }
    });
  }

  /* magnets */
  mags.forEach(function (m) {
    var r = magRect(m);
    ctx.save();
    ctx.translate(r.x, r.y); ctx.rotate(m.angle);
    // S half
    ctx.fillStyle = '#3b82f6';
    ctx.fillRect(-W / 2, -H / 2, W / 2, H);
    // N half
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(0, -H / 2, W / 2, H);
    ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2.5;
    ctx.strokeRect(-W / 2, -H / 2, W, H);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 16px system-ui, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('S', -W / 4, 6);
    ctx.fillText('N', W / 4, 6);
    ctx.textAlign = 'start';
    ctx.restore();
    if (m.loose) {
      ctx.fillStyle = LK.C.sub; ctx.font = '12px system-ui, sans-serif';
      ctx.fillText('drag me', r.x - 22, r.y + H / 2 + 16);
    }
  });

  /* compass at pointer */
  if (s.compass && s.mouse && !s.dragging) {
    var f = fieldAt(s.mouse.x, s.mouse.y);
    var ang = Math.atan2(f.y, f.x);
    var cx = s.mouse.x, cy = s.mouse.y;
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.arc(cx, cy, 20, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = LK.C.ink; ctx.lineWidth = 2; ctx.stroke();
    // needle red N end along field (field points N->S outside... compass N points along B)
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(ang);
    ctx.fillStyle = '#ef4444';
    ctx.beginPath(); ctx.moveTo(16, 0); ctx.lineTo(-3, -4); ctx.lineTo(-3, 4); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#64748b';
    ctx.beginPath(); ctx.moveTo(-16, 0); ctx.lineTo(-3, -4); ctx.lineTo(-3, 4); ctx.closePath(); ctx.fill();
    ctx.restore();
  }
}

/* ---- magnet attraction / repulsion physics on the loose magnet ---- */
var snapShown = false;
function physics() {
  var m = mags[1];
  var p = poles(m), f = { x: 0, y: 0 };
  allPoles().forEach(function (q) {
    if (q === p.n || q === p.s) return;
    [[p.n, 1], [p.s, 1]].forEach(function (pair) {
      var pp = pair[0];
      var dx = q.x - pp.x, dy = q.y - pp.y;
      var d = Math.max(26, Math.hypot(dx, dy));
      var sign = (pp.type === q.type) ? -1 : 1;      // like repel, unlike attract
      var mag = sign * 5.2e6 / (d * d);
      f.x += dx / d * mag; f.y += dy / d * mag;
    });
  });
  m.x += LK.clamp(f.x, -6, 6); m.y += LK.clamp(f.y, -6, 6);
  m.x = LK.clamp(m.x, -st.w / 2 + W, st.w / 2 - W);
  m.y = LK.clamp(m.y, -st.h / 2 + H, st.h / 2 - H);
  // detect close attraction for the banner
  var near = allPoles().some(function (q) {
    if (q === p.n || q === p.s) return false;
    return Math.hypot(q.x - p.n.x, q.y - p.n.y) < W * 0.95 || Math.hypot(q.x - p.s.x, q.y - p.s.y) < W * 0.95;
  });
  if (near && !snapShown) {
    snapShown = true;
    document.getElementById('snapBanner').classList.remove('hidden');
    setTimeout(function () { document.getElementById('snapBanner').classList.add('hidden'); snapShown = false; }, 1800);
  }
  var like = allPoles().some(function (q) {
    if (q === p.n || q === p.s) return false;
    return (q.type === p.n.type && Math.hypot(q.x - p.n.x, q.y - p.n.y) < 130) ||
           (q.type === p.s.type && Math.hypot(q.x - p.s.x, q.y - p.s.y) < 130);
  });
  document.getElementById('statusText').innerHTML = like
    ? '<b style="color:#ef4444;">Like poles nearby — pushing apart!</b>'
    : 'Drag the <b>grey magnet</b> — feel where it snaps!';
}
setInterval(physics, 30);

/* ---- interaction ---- */
LK.pointer(st.canvas, {
  down: function (p) {
    var m = mags[1], r = magRect(m);
    if (Math.abs(p.x - r.x) < 70 && Math.abs(p.y - r.y) < 60) {
      s.dragging = true;
      s.grab = { dx: r.x - p.x, dy: r.y - p.y };
    }
  },
  move: function (p, d) {
    s.mouse = p;
    if (d && s.dragging) {
      var c = center();
      mags[1].x = LK.clamp(p.x + s.grab.dx - c.x, -st.w / 2 + W, st.w / 2 - W);
      mags[1].y = LK.clamp(p.y + s.grab.dy - c.y, -st.h / 2 + H, st.h / 2 - H);
    }
  },
  up: function () { s.dragging = false; },
  out: function () { s.mouse = null; s.dragging = false; }
});
LK.check('fieldChk', function (on) { s.field = on; });
LK.check('compChk', function (on) { s.compass = on; });
LK.button('flipBtn', function () { mags[1].angle += Math.PI; });
LK.button('resetBtn', function () {
  mags[1] = { x: 210, y: 120, angle: Math.PI, loose: true };
});

st.draw = draw;
