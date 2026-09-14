'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

/* XR mode: setAnimationLoop driven; camera controlled by the headset inside the session */
var st = L3.init(document.getElementById('cv'), {
  xr: true, minR: 6, maxR: 60, camPos: [0, 4, 14], autoSpin: false
});
var scene = st.scene;
var EYE = 1.55;                    // average student eye height — the system orbits around you
var CENTER = new THREE.Vector3(0, EYE, 0);
st.orbit.target.copy(CENTER);

scene.add(L3.stars(2400, 90));    // close sphere of stars: you are IN space

/* ---------- sun (you stand here) ---------- */
var sun = L3.sphere(0.45, 0xffb300, { emissive: 0xff8c00, emissiveIntensity: 1.5, seg: 48 });
sun.position.copy(CENTER);
scene.add(sun);
var glow = L3.glow('rgba(255,170,40,0.9)', 3.2);
glow.position.copy(CENTER);
scene.add(glow);
var sunLight = new THREE.PointLight(0xffe0b0, 3, 40, 1.4);
sunLight.position.copy(CENTER);
scene.add(sunLight);

/* ---------- planets at room scale ---------- */
var P = [
  ['Mercury', 0.09, 1.1,  0x9e9e9e, 88,   ['Fastest lap: one year in 88 Earth days', 'No atmosphere at all']],
  ['Venus',   0.16, 1.7,  0xe8b84b, 225,  ['Hottest planet: about 465°C', 'Spins backwards!']],
  ['Earth',   0.17, 2.4,  0x2e6fd8, 365,  ['Home — 71% ocean', 'Moon orbits every 27.3 days', 'Tilt 23.5° gives seasons']],
  ['Mars',    0.12, 3.1,  0xc1440e, 687,  ['The red planet', 'Olympus Mons: tallest volcano']],
  ['Jupiter', 0.42, 4.3,  0xd8a26a, 4333, ['Gas giant — biggest planet', 'Great Red Spot storm']],
  ['Saturn',  0.36, 5.4,  0xe3c07b, 10759,['Rings of ice and rock', 'Would float on water']],
  ['Uranus',  0.24, 6.3,  0x7de0e3, 30687,['Rolls on its side', 'Coldest atmosphere']],
  ['Neptune', 0.23, 7.1,  0x3a5bd9, 60190,['Fastest winds: 2000 km/h', 'Year = 165 Earth years']]
];

var planets = [];
P.forEach(function (d, i) {
  var pivot = new THREE.Object3D();
  pivot.position.copy(CENTER);
  pivot.rotation.y = i * 0.9;
  scene.add(pivot);
  var holder = new THREE.Object3D();
  holder.position.x = d[2];
  pivot.add(holder);
  var mesh = L3.sphere(d[1], d[3]);
  holder.add(mesh);
  if (i === 2) {   // Earth's moon
    var mp = new THREE.Object3D();
    mesh.add(mp);
    var moon = L3.sphere(0.045, 0xbfbfbf);
    moon.position.x = 0.32;
    mp.add(moon);
    holder.userData.moonPivot = mp;
  }
  if (i === 5) {   // Saturn's ring
    var ring = new THREE.Mesh(
      new THREE.TorusGeometry(d[1] * 1.9, 0.02, 2, 64),
      new THREE.MeshStandardMaterial({ color: 0xd9c9a3, roughness: 0.9 })
    );
    ring.rotation.x = Math.PI / 2.4;
    mesh.add(ring);
  }
  var lb = L3.label(d[0], '#dbe6ff', 0.55);
  lb.position.y = d[1] + 0.22;
  holder.add(lb);
  // orbit ring on the floor-height plane through CENTER
  var orbit = new THREE.Mesh(
    new THREE.RingGeometry(d[2] - 0.012, d[2] + 0.012, 96),
    new THREE.MeshBasicMaterial({ color: 0x6b7ba8, side: THREE.DoubleSide, transparent: true, opacity: 0.5 })
  );
  orbit.rotation.x = -Math.PI / 2;
  orbit.position.copy(CENTER);
  scene.add(orbit);
  planets.push({ name: d[0], days: d[4], facts: d[5], pivot: pivot, mesh: mesh, holder: holder, lb: lb });
});

/* ---------- fact panel (VR HUD / flat overlay) ---------- */
var hud = null;
function showFacts(pl) {
  if (hud) scene.remove(hud);
  var lines = [{ text: pl.name }].concat(pl.facts.map(function (f) { return { text: '• ' + f }; }))
    .concat([{ text: 'Year: ' + pl.days + ' Earth days' }]);
  hud = XRK.panel(lines, { scale: 0.55 });
  hud.position.set(0, EYE + 0.55, -1.7);
  scene.add(hud);
  document.getElementById('info').innerHTML =
    '<b style="color:#7dd3fc;">' + pl.name + '</b><br>' +
    pl.facts.map(function (f) { return '• ' + f; }).join('<br>') +
    '<br>One year: <b>' + pl.days + ' Earth days</b>';
  planets.forEach(function (p2) { p2.mesh.material.emissive.setHex(0x000000); });
  pl.mesh.material.emissive.setHex(0x224466);
}

/* ---------- controllers (VR) ---------- */
var raycaster = new THREE.Raycaster();
XRK.controllers(st.renderer, scene, {
  onSelect: function (controller) {
    XRK.rayFromController(controller, raycaster);
    var hit = raycaster.intersectObjects(planets.map(function (p) { return p.mesh; }), true)[0];
    if (hit) {
      var pl = planets.filter(function (p) { return p.mesh === hit.object || p.mesh.children.indexOf(hit.object) >= 0; })[0];
      if (pl) showFacts(pl);
    }
  }
});

/* ---------- VR button ---------- */
XRK.button(document.getElementById('vrBtnHolder'), st.renderer, {
  mode: 'immersive-vr', label: '\uD83E\uDD73 Enter VR',
  onStart: function () {
    // hide flat-mode helpers so the headset view is clean
    planets.forEach(function (p) { p.lb.visible = true; });
  }
});

/* ---------- flat-mode click ---------- */
var mouse = new THREE.Vector2();
document.getElementById('cv').addEventListener('pointerup', function (e) {
  if (st.renderer.xr.isPresenting) return;
  var r = this.getBoundingClientRect();
  mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
  raycaster.setFromCamera(mouse, st.camera);
  var hit = raycaster.intersectObjects(planets.map(function (p) { return p.mesh; }), true)[0];
  if (hit) {
    var pl = planets.filter(function (p) { return p.mesh === hit.object || p.mesh.children.indexOf(hit.object) >= 0; })[0];
    if (pl) showFacts(pl);
  }
});

/* ---------- animation ---------- */
var DAYS_PER_SEC = 15, simDays = 0;
var SPEEDS = [0, 1, 5, 15, 40, 120, 365];
LK.slider('spd', function (v) {
  DAYS_PER_SEC = SPEEDS[v] || 15;
  document.getElementById('spdv').textContent = v === 0 ? 'paused' : DAYS_PER_SEC + ' d/s';
});

st.frame = function (t) {
  var dt = Math.min(0.05, t - (st.__t || t)); st.__t = t;
  simDays += DAYS_PER_SEC * dt;
  sun.rotation.y += dt * 0.3;
  planets.forEach(function (p) {
    p.pivot.rotation.y = (simDays / p.days) * Math.PI * 2;
    p.mesh.rotation.y += dt * 1.4;
    if (p.holder.userData.moonPivot) p.holder.userData.moonPivot.rotation.y = (simDays / 27.3) * Math.PI * 2;
  });
};
