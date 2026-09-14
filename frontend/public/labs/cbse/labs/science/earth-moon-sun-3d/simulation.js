'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { xr: true, bg: 0x05070f, minR: 4, maxR: 60, camPos: [0, 9, 24] });
var scene = st.scene;
scene.add(L3.stars(2600, 200));

var s = { moon: 0, day: 80, eclipse: false };

/* sun far away */
var sun = L3.sphere(3.2, 0xf59e0b, { emissive: 0xff8c00, emissiveIntensity: 1.6, seg: 48 });
sun.position.set(-60, 6, -18);
scene.add(sun);
scene.add(L3.glow('rgba(255,170,40,0.9)', 16)).position.copy(sun.position);
var sunLight = new THREE.DirectionalLight(0xfff2d8, 2.4);
sunLight.position.copy(sun.position);
scene.add(sunLight);

/* earth with land + tilt */
var earthPivot = new THREE.Group();
earthPivot.position.set(0, 0, 0);
scene.add(earthPivot);
var earthTilt = new THREE.Group();
earthTilt.rotation.z = 23.5 * Math.PI / 180;
earthPivot.add(earthTilt);
var earth = L3.sphere(2.2, 0x2563eb, { roughness: 0.7 });
earthTilt.add(earth);
// simple continents as green patches
[[-0.9, 0.6, 1.7], [1.2, -0.3, 1.5], [0.4, 1.5, -1.4], [-1.1, -1.2, -1.0]].forEach(function (p) {
  var land = L3.sphere(0.72, 0x16a34a, { roughness: 0.85 });
  land.position.set(p[0], p[1], p[2]);
  land.scale.set(1, 0.55, 0.9);
  earth.add(land);
});
// atmosphere hint
var atmo = L3.sphere(2.35, 0x60a5fa, {});
atmo.material.transparent = true; atmo.material.opacity = 0.12;
earthTilt.add(atmo);

/* moon + orbit ring */
var moonPivot = new THREE.Group();
earthPivot.add(moonPivot);
var moon = L3.sphere(0.6, 0xd4d4d8, { roughness: 0.95 });
moon.position.x = 6;
moonPivot.add(moon);
var orbit = new THREE.Mesh(
  new THREE.RingGeometry(5.9, 6.02, 96),
  new THREE.MeshBasicMaterial({ color: 0x64748b, side: THREE.DoubleSide, transparent: true, opacity: 0.5 })
);
orbit.rotation.x = -Math.PI / 2;
earthPivot.add(orbit);

/* sun-earth line */
var line = new THREE.Line(
  new THREE.BufferGeometry().setFromPoints([sun.position.clone(), new THREE.Vector3(0, 0, 0)]),
  new THREE.LineBasicMaterial({ color: 0xfbbf24, transparent: true, opacity: 0.25 })
);
scene.add(line);

/* moon-phase name from angle (0 = between earth and sun = new moon) */
var PHASES = [
  [0, 'New Moon \uD83C\uDF11'], [45, 'Waxing Crescent \uD83C\uDF12'], [90, 'First Quarter \uD83C\uDF13'],
  [135, 'Waxing Gibbous \uD83C\uDF14'], [180, 'Full Moon \uD83C\uDF15'], [225, 'Waning Gibbous \uD83C\uDF16'],
  [270, 'Last Quarter \uD83C\uDF17'], [315, 'Waning Crescent \uD83C\uDF18']
];
function phaseName(deg) {
  var best = PHASES[0];
  PHASES.forEach(function (p) { if (Math.abs(p[0] - deg) < Math.abs(best[0] - deg)) best = p; });
  return best[1];
}

/* shadow cones for eclipse mode */
var moonShadow = new THREE.Mesh(
  new THREE.ConeGeometry(0.6, 6, 24, 1, true),
  new THREE.MeshBasicMaterial({ color: 0xdc2626, transparent: true, opacity: 0.28, side: THREE.DoubleSide })
);

function upd() {
  var lunar = (s.moon > 160 && s.moon < 200);   // moon opposite sun
  var solar = (s.moon < 20 || s.moon > 340);    // moon between sun and earth
  document.getElementById('phaseChip').textContent = phaseName(s.moon);
  var ex;
  if (!s.eclipse) {
    ex = lunar ? 'Full moon: the Sun lights the face we see.'
      : solar ? 'New moon: the dark side faces us.'
      : 'Watch the terminator (day–night line) move across the Moon as you slide the orbit.';
  } else if (lunar) {
    ex = '\uD83C\uDF15 <b>LUNAR ECLIPSE</b> — Earth sits exactly between Sun and Moon; Earth\u2019s shadow covers the Moon (it can turn copper-red).';
  } else if (solar) {
    ex = '\u2600\uFE0F <b>SOLAR ECLIPSE</b> — the Moon slips between Sun and Earth; its tiny shadow sweeps Earth. Day turns to night for minutes!';
  } else {
    ex = 'Aligned system, but the Moon is off the Sun\u2019s line — no eclipse this time. The Moon\u2019s orbit is tilted ~5\u00B0, so perfect alignment is rare (and special!).';
  }
  document.getElementById('explain').innerHTML = ex;

  if (s.eclipse && (lunar || solar)) {
    if (!moonShadow.parent) scene.add(moonShadow);
    var mp = new THREE.Vector3();
    moon.getWorldPosition(mp);
    moonShadow.position.copy(mp);
    // point shadow away from sun
    var dir = mp.clone().sub(sun.position).normalize();
    moonShadow.position.addScaledVector(dir, 3);
    moonShadow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    moonShadow.visible = true;
  } else {
    moonShadow.visible = false;
  }
}

XRK.button(document.getElementById('vrBtnHolder'), st.renderer, { mode: 'immersive-vr', label: '\uD83E\uDD73 Enter VR' });

st.frame = function (t) {
  moonPivot.rotation.y = s.moon * Math.PI / 180 + Math.PI;   // 180° so deg 0 = new moon
  earth.rotation.y = s.day * Math.PI / 180;
  moon.rotation.y += 0.002;                                   // tidally locked-ish
  sun.rotation.y = t * 0.05;
};

LK.slider('moon', function (v) {
  s.moon = v;
  document.getElementById('moov').textContent = v + '\u00B0';
  upd();
});
LK.slider('day', function (v) {
  s.day = v;
  document.getElementById('dayv').textContent = v + '\u00B0';
});
LK.check('eclipseChk', function (on) { s.eclipse = on; upd(); });
upd();
