'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { bg: 0x0a0e1a, minR: 12, maxR: 70, camPos: [16, 10, 30] });
var scene = st.scene;
scene.add(L3.stars(600, 400));

var s = { tilt: 10 };   // 0..100

/* ---------- double cone ---------- */
var coneMat = new THREE.MeshStandardMaterial({
  color: 0x60a5fa, roughness: 0.4, metalness: 0.1,
  transparent: true, opacity: 0.28, side: THREE.DoubleSide, depthWrite: false
});
var topCone = new THREE.Mesh(new THREE.ConeGeometry(10, 16, 64, 1, true), coneMat);
topCone.position.y = 8;
scene.add(topCone);
var botCone = new THREE.Mesh(new THREE.ConeGeometry(10, 16, 64, 1, true), coneMat);
botCone.position.y = -8; botCone.rotation.x = Math.PI;
scene.add(botCone);
// wireframe ribs
var wireMat = new THREE.MeshBasicMaterial({ color: 0x93c5fd, wireframe: true, transparent: true, opacity: 0.16 });
[topCone, botCone].forEach(function (c) {
  var w2 = new THREE.Mesh(new THREE.ConeGeometry(10, 16, 24, 1, true), wireMat);
  w2.position.copy(c.position); w2.rotation.copy(c.rotation);
  scene.add(w2);
});
// axis
var axis = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 40, 8),
  new THREE.MeshBasicMaterial({ color: 0x64748b }));
scene.add(axis);

/* ---------- cutting plane + section curve ---------- */
var plane = new THREE.Mesh(new THREE.PlaneGeometry(30, 30),
  new THREE.MeshStandardMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.32, side: THREE.DoubleSide }));
scene.add(plane);
var sectionCurve = new THREE.Line(
  new THREE.BufferGeometry(),
  new THREE.LineBasicMaterial({ color: 0xfbbf24, linewidth: 2 })
);
scene.add(sectionCurve);

function sectionType() {
  // cone half-angle ~ atan(10/16) = 32deg. tilt 0..100 maps to plane angle 0..75deg vs horizontal.
  var ang = s.tilt / 100 * 75;
  if (ang < 12) return { name: 'Circle', color: 0xfbbf24,
    info: 'Plane ⊥ axis — every point is the same distance from the axis.',
    eq: 'x² + y² = r²' };
  if (ang < 38) return { name: 'Ellipse', color: 0x34d399,
    info: 'Plane cuts one cone at a slant — the circle gets stretched.',
    eq: 'x²/a² + y²/b² = 1  (a ≠ b)' };
  if (ang < 52) return { name: 'Parabola', color: 0xf472b6,
    info: 'Plane parallel to the cone\u2019s slant side — one open arm.',
    eq: 'y² = 4ax' };
  return { name: 'Hyperbola', color: 0x38bdf8,
    info: 'Plane steep enough to slice BOTH cones — two mirror arms.',
    eq: 'x²/a² − y²/b² = 1' };
}

function rebuild() {
  var ang = s.tilt / 100 * 75 * Math.PI / 180;
  plane.rotation.set(0, 0, ang);
  plane.position.set(0, Math.sin(ang) * -3 + 2, 0);

  // trace the intersection curve numerically: cone x²+z² = ((16−y)/16*10)² for top cone (y: 0..16)
  var pts = [];
  var y;
  var n = 0;
  for (var t = -1.55; t <= 1.55; t += 0.02) {
    // point on cone surface param by (y, θ)
    y = 0.5 + (t + 1.55) / 3.1 * 15;                    // 0.5..15.5 on top cone
    var r = (16 - y) / 16 * 10;
    var th = t * 6;
    var x = Math.cos(th) * r, z = Math.sin(th) * r;
    // rotate point onto plane test: plane normal after rotation about z:
    // keep simple — mark points where plane would cut (distance to plane < 0.6)
    var d = Math.cos(ang) * (y - plane.position.y) + Math.sin(ang) * x;
    if (Math.abs(d) < 0.55) pts.push(new THREE.Vector3(x, y, z));
  }
  // fallback ring so something is always visible
  if (pts.length < 12) {
    pts = [];
    for (var a = 0; a <= Math.PI * 2 + 0.01; a += 0.1) {
      var yv = 4;
      var rv = (16 - yv) / 16 * 10;
      pts.push(new THREE.Vector3(Math.cos(a) * rv, yv, Math.sin(a) * rv));
    }
  }
  sectionCurve.geometry.dispose();
  sectionCurve.geometry = new THREE.BufferGeometry().setFromPoints(pts);
  var sec = sectionType();
  sectionCurve.material.color.setHex(sec.color);
  document.getElementById('cName').textContent = sec.name;
  document.getElementById('cName').style.color = '#' + new THREE.Color(sec.color).getHexString();
  document.getElementById('cInfo').textContent = sec.info;
  document.getElementById('cEq').innerHTML = '<span style="font-family:Georgia,serif;font-size:17px;">' + sec.eq + '</span>';
}

LK.slider('tilt', function (v) {
  s.tilt = v;
  document.getElementById('tiltv').textContent = v;
  rebuild();
});
LK.segment('quickSeg', function (i) {
  var presets = [5, 25, 45, 80];
  s.tilt = presets[i];
  document.getElementById('tilt').value = presets[i];
  document.getElementById('tiltv').textContent = presets[i];
  rebuild();
});

rebuild();
