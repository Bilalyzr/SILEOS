'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = LK.setupCanvas(document.getElementById('cv'));
var s = { mode: 0, inten: 2, coriolis: true, t: 0 };
var dots = [];
var D = 150;

function initDots() {
  dots = [];
  for (var i = 0; i < D; i++) {
    dots.push({ x: Math.random(), y: Math.random(), hue: 0 });
  }
}
initDots();

/* pressure field: returns {fx, fy} force direction at (x,y) in 0..1 space */
function forceAt(x, y) {
  if (s.mode === 1) {
    // cyclone: spiral toward center low
    var cx = 0.5, cy = 0.5;
    var dx = cx - x, dy = cy - y;
    var d = Math.hypot(dx, dy) + 1e-4;
    var pull = 1.6 / (d + 0.18) * s.inten * 0.14;
    var fx = dx / d * pull, fy = dy / d * pull;
    if (s.coriolis) {
      // rotate the inflow (northern hemisphere: counterclockwise)
      var sw = 1.35 * s.inten * 0.5;
      fx += -dy / d * sw * pull * 6;
      fy += dx / d * sw * pull * 6;
    }
    return { fx: fx, fy: fy };
  }
  // breeze: land on right (x>0.55), sea on left
  var landHot = s.mode === 0;                    // day: land hot
  var dir = landHot ? 1 : -1;                    // sea breeze flows sea→land (+x), land breeze −x
  var bandY = Math.abs(y - 0.5) < 0.3 ? 1 : 0.4; // strongest mid-map
  var fx = dir * 0.035 * s.inten * 0.6 * bandY;
  var fy = Math.sin(x * 9 + s.t * 0.8 + y * 5) * 0.004;   // gentle turbulence
  return { fx: fx, fy: fy };
}

function draw() {
  var ctx = st.ctx, w = st.w, h = st.h;
  ctx.clearRect(0, 0, w, h);
  s.t += 0.016;

  /* background zones */
  if (s.mode === 1) {
    // ocean + spiral bands
    var g = ctx.createRadialGradient(w / 2, h / 2, 20, w / 2, h / 2, w * 0.55);
    g.addColorStop(0, 'rgba(2,6,23,1)');
    g.addColorStop(0.35, 'rgba(12,32,64,1)');
    g.addColorStop(1, 'rgba(2,6,23,1)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    // eye
    ctx.fillStyle = 'rgba(233,213,255,0.10)';
    ctx.beginPath(); ctx.arc(w / 2, h / 2, 26, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = 'rgba(196,181,253,.8)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(w / 2, h / 2, 26, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = '#c4b5fd'; ctx.font = '600 12px system-ui, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('EYE (calm, lowest pressure)', w / 2, h / 2 + 46);
    ctx.textAlign = 'start';
    // spiral arms
    ctx.strokeStyle = 'rgba(148,163,184,.16)'; ctx.lineWidth = 26;
    for (var arm = 0; arm < 3; arm++) {
      ctx.beginPath();
      for (var a2 = 0; a2 < 4.2; a2 += 0.08) {
        var rr = 40 + a2 * 62;
        var ang = a2 * 1.25 + arm * 2.09 - s.t * 0.55;
        var px0 = w / 2 + Math.cos(ang) * rr, py0 = h / 2 + Math.sin(ang) * rr * 0.9;
        a2 === 0 ? ctx.moveTo(px0, py0) : ctx.lineTo(px0, py0);
      }
      ctx.stroke();
    }
  } else {
    // sea (left) vs land (right)
    var split = 0.55;
    var seaGrad = ctx.createLinearGradient(0, 0, w * split, 0);
    seaGrad.addColorStop(0, '#0c2d48'); seaGrad.addColorStop(1, s.mode === 0 ? '#10557a' : '#0a2440');
    ctx.fillStyle = seaGrad;
    ctx.fillRect(0, 0, w * split, h);
    var landGrad = ctx.createLinearGradient(w * split, 0, w, 0);
    var hot = s.mode === 0;
    landGrad.addColorStop(0, hot ? '#7c4a1d' : '#3d4a2d');
    landGrad.addColorStop(1, hot ? '#b4692a' : '#27351f');
    ctx.fillStyle = landGrad;
    ctx.fillRect(w * split, 0, w * (1 - split), h);
    // beach line
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(w * split, 0); ctx.lineTo(w * split, h); ctx.stroke();
    ctx.font = '600 13px system-ui, sans-serif';
    ctx.fillStyle = hot ? '#bae6fd' : '#94c8e8';
    ctx.fillText('SEA  (cool, high pressure)', 18, 30);
    ctx.fillStyle = hot ? '#ffe0b3' : '#cddac2';
    ctx.fillText(hot ? 'LAND  (hot, low pressure — air rises)' : 'LAND  (cool, high pressure)', w * split + 18, 30);
    // sun/moon
    if (hot) {
      ctx.fillStyle = '#fbbf24';
      ctx.beginPath(); ctx.arc(w * 0.8, 60, 20, 0, Math.PI * 2); ctx.fill();
    } else {
      ctx.fillStyle = '#e2e8f0';
      ctx.beginPath(); ctx.arc(w * 0.8, 60, 16, 0, Math.PI * 2); ctx.fill();
    }
    // rising air arrows over hot zone
    var riseX = hot ? w * 0.78 : w * 0.28;
    ctx.strokeStyle = 'rgba(255,255,255,.5)'; ctx.lineWidth = 2;
    for (var k = 0; k < 3; k++) {
      var bx = riseX + (k - 1) * 34;
      var yy = h - 80 - ((s.t * 40 + k * 60) % 160);
      ctx.beginPath(); ctx.moveTo(bx, yy + 16); ctx.lineTo(bx, yy); ctx.stroke();
      LK.arrow(ctx, bx, yy, -Math.PI / 2, 'rgba(255,255,255,.5)', 7);
    }
  }

  /* wind particles */
  dots.forEach(function (p) {
    var f = forceAt(p.x, p.y);
    p.x += f.fx * 0.4; p.y += f.fy * 0.4;
    // respawn when leaving bounds or entering the eye
    if (s.mode === 1 && Math.hypot(p.x - 0.5, p.y - 0.5) < 0.045) {
      var a3 = Math.random() * Math.PI * 2;
      p.x = 0.5 + Math.cos(a3) * 0.55; p.y = 0.5 + Math.sin(a3) * 0.55;
    }
    if (p.x < -0.02 || p.x > 1.02 || p.y < -0.02 || p.y > 1.02) {
      p.x = Math.random(); p.y = Math.random();
    }
    var px0 = p.x * w, py0 = p.y * h;
    // colour by speed
    var sp = Math.hypot(f.fx, f.fy);
    p.hue = LK.clamp(190 - sp * 140, 20, 210);
    ctx.fillStyle = 'hsl(' + p.hue + ',85%,68%)';
    ctx.globalAlpha = 0.9;
    ctx.beginPath(); ctx.arc(px0, py0, 2.6, 0, Math.PI * 2); ctx.fill();
    // motion streak
    ctx.strokeStyle = 'hsla(' + p.hue + ',85%,68%,.35)'; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(px0, py0); ctx.lineTo(px0 - f.fx * w * 1.6, py0 - f.fy * h * 1.6); ctx.stroke();
    ctx.globalAlpha = 1;
  });

  /* readouts */
  var pr;
  if (s.mode === 1) {
    pr = 'Centre: <b>very LOW</b> pressure (≈950 hPa) → air forced inward.<br>' +
      (s.coriolis ? 'Coriolis ON: winds spiral <b>anticlockwise</b> (Northern Hemisphere) — a cyclone is born! Switch it off to see air rush straight in.'
                  : 'Coriolis OFF: air rushes straight in — no real cyclone can form without Earth\u2019s spin!');
  } else if (s.mode === 0) {
    pr = 'Day: land heats fast → <b>low</b> pressure over land, <b>high</b> over sea.<br>Wind blows <b>sea → land</b>: the cool sea breeze (kite-flying time in coastal India!).';
  } else {
    pr = 'Night: land cools fast → <b>high</b> pressure over land.<br>Wind reverses to <b>land → sea</b>: the gentle land breeze (fishermen sail out at dawn on it).';
  }
  document.getElementById('pressRead').innerHTML = pr;
}

LK.segment('modeSeg', function (i) { s.mode = i; initDots(); });
LK.slider('inten', function (v) {
  s.inten = v;
  document.getElementById('intenv').textContent = ['calm', 'medium', 'severe'][v - 1];
});
LK.check('corChk', function (on) { s.coriolis = on; });

st.draw = draw;
