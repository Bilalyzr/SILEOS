'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { xr: true, bg: 0x0b1120, minR: 2, maxR: 16, camPos: [0, 2.2, 6.5] });
st.orbit.target.set(0, 1.4, 0);
var scene = st.scene;
scene.add(L3.stars(500, 40));
var EYE = 1.4;

var s = { temp: 25 };
var N = 180;
var parts = [];
var box = new THREE.Box3(new THREE.Vector3(-1.4, 0.1, -1.4), new THREE.Vector3(1.4, 2.2, 1.4));
var geo = new THREE.SphereGeometry(0.085, 14, 14);
var matO = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.25, metalness: 0.1 });
var matH = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.3 });

/* each water molecule = 1 big O + 2 small H */
var molecules = [];
for (var i = 0; i < N / 3; i++) {
  var g = new THREE.Group();
  var o = new THREE.Mesh(geo, matO); o.scale.setScalar(1.5); g.add(o);
  [-1, 1].forEach(function (sgn) {
    var h = new THREE.Mesh(geo, matH);
    h.position.set(sgn * 0.13, 0.1, 0);
    g.add(h);
  });
  scene.add(g);
  molecules.push({ g: g, home: null, v: new THREE.Vector3(), phase: Math.random() * 6.28 });
}
/* lattice home positions (ice) */
var homes = [];
for (var x = 0; x < 5; x++) for (var y = 0; y < 4; y++) for (var z = 0; z < 3; z++) {
  homes.push(new THREE.Vector3(-1.15 + x * 0.575 + (y % 2) * 0.12, 0.35 + y * 0.5, -1.0 + z * 0.7));
}
molecules.forEach(function (m, i) { m.home = homes[i % homes.length].clone(); });

/* invisible container visual */
var frame = new THREE.LineSegments(
  new THREE.EdgesGeometry(new THREE.BoxGeometry(3.2, 2.5, 2.8)),
  new THREE.LineBasicMaterial({ color: 0x64748b, transparent: true, opacity: 0.55 })
);
frame.position.set(0, 1.35, 0);
scene.add(frame);

function stateOf(t) {
  if (t <= 0) return { name: 'Ice (solid)', info: 'Molecules locked in a <b>hexagonal lattice</b> — they vibrate but keep their places.' };
  if (t < 100) return { name: 'Liquid water', info: 'Molecules slide past each other — <b>hydrogen bonds</b> break and reform constantly.' };
  return { name: 'Steam (gas)', info: 'Molecules fly free — bonds broken, they zip around at ~600 m/s!' };
}

function upd() {
  var stt = stateOf(s.temp);
  document.getElementById('stateName').textContent = stt.name;
  document.getElementById('stateInfo').innerHTML = stt.info +
    '<br>Melting at 0°C · Boiling at 100°C';
}

XRK.button(document.getElementById('vrBtnHolder'), st.renderer, { mode: 'immersive-vr', label: '\uD83E\uDD73 Enter VR' });

var dt = 0.016;
st.frame = function (t) {
  var heat = LK.clamp((s.temp + 30) / 160, 0, 1);         // 0=coldest 1=hottest
  var frozen = s.temp <= 0;
  var gas = s.temp >= 100;
  molecules.forEach(function (m, i) {
    var p = m.g.position;
    if (frozen) {
      // drift toward lattice home + tiny vibration
      p.lerp(m.home, 0.06);
      p.x += Math.sin(t * 9 + m.phase) * 0.006 * (1 - heat * 0.5);
      p.y += Math.cos(t * 8 + m.phase) * 0.006;
    } else if (gas) {
      // random flight, bounce off container walls
      if (m.v.length() < 0.01) m.v.set(LK.rand(-1, 1), LK.rand(-0.3, 1), LK.rand(-1, 1)).normalize().multiplyScalar(0.09 * (0.6 + heat));
      p.addScaledVector(m.v, dt * (0.7 + heat));
      if (p.x < box.min.x || p.x > box.max.x) m.v.x *= -1;
      if (p.y < box.min.y || p.y > box.max.y) m.v.y *= -1;
      if (p.z < box.min.z || p.z > box.max.z) m.v.z *= -1;
      p.clamp(box.min, box.max);
    } else {
      // liquid: wander in the lower half, settle under gravity
      if (m.v.length() < 0.01) m.v.set(LK.rand(-1, 1), 0, LK.rand(-1, 1)).multiplyScalar(0.02);
      m.v.y -= 0.004;                                       // gravity
      m.v.multiplyScalar(0.985);
      p.addScaledVector(m.v, dt * 2.2);
      var liquidTop = box.min.y + (box.max.y - box.min.y) * 0.45;
      if (p.y < box.min.y + 0.05) { p.y = box.min.y + 0.05; m.v.y = Math.abs(m.v.y) * 0.3; }
      if (p.y > liquidTop) { p.y = liquidTop; m.v.y = -Math.abs(m.v.y); }
      if (p.x < box.min.x || p.x > box.max.x) m.v.x *= -1;
      if (p.z < box.min.z || p.z > box.max.z) m.v.z *= -1;
      p.clamp(box.min, box.max);
    }
    // gentle whole-molecule spin so students see the bent shape
    m.g.rotation.y = t * (frozen ? 0.4 : 1.6) + m.phase;
  });
};

LK.slider('temp', function (v) {
  s.temp = v;
  document.getElementById('tempv').textContent = v + '\u00B0C';
  if (s.temp >= 100) molecules.forEach(function (m) { m.v.set(0, 0, 0); });
  upd();
});
LK.segment('quickSeg', function (i) {
  var T = [-10, 25, 110][i];
  s.temp = T;
  document.getElementById('temp').value = T;
  document.getElementById('tempv').textContent = T + '\u00B0C';
  molecules.forEach(function (m) { m.v.set(0, 0, 0); });
  upd();
});
upd();
