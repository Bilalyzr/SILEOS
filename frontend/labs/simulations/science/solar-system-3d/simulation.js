'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { minR: 30, maxR: 420, camPos: [0, 130, 210] });
var scene = st.scene;

scene.add(L3.stars(2600, 1600));

/* ---------- sun ---------- */
var sun = L3.sphere(9, 0xffb300, { emissive: 0xff8c00, emissiveIntensity: 1.4, seg: 64 });
scene.add(sun);
scene.add(L3.glow('rgba(255,170,40,0.85)', 55));
var sunLight = new THREE.PointLight(0xffe0b0, 2.2, 1200, 1.6);
scene.add(sunLight);

/* ---------- planets: [name, radius, dist, color, yearDays, facts] ---------- */
var P = [
  ['Mercury', 1.7, 18,  0x9e9e9e, 88,   ['Smallest planet, closest to Sun', 'A year lasts just 88 Earth days', 'No atmosphere — scorching days, freezing nights']],
  ['Venus',   2.6, 26,  0xe8b84b, 225,  ['Hottest planet (≈465°C) — runaway greenhouse', 'Spins backwards, very slowly', 'A day on Venus is longer than its year!']],
  ['Earth',   2.8, 35,  0x2e6fd8, 365,  ['The only known planet with life', '71% of the surface is water', 'Axis tilted 23.5° → seasons']],
  ['Mars',    2.1, 45,  0xc1440e, 687,  ['The red planet — iron oxide dust', 'Has Olympus Mons, the tallest volcano', 'Two small moons: Phobos & Deimos']],
  ['Jupiter', 6.2, 68,  0xd8a26a, 4333, ['Largest planet — a gas giant', 'The Great Red Spot is a giant storm', 'Has 90+ moons, including Ganymede']],
  ['Saturn',  5.4, 92,  0xe3c07b, 10759,['Famous rings of ice & rock', 'Least dense planet — would float on water!', 'Titan, its moon, has lakes of methane']],
  ['Uranus',  3.6, 114, 0x7de0e3, 30687,['Rolls on its side (tilt ≈ 98°)', 'Coldest atmosphere in the solar system', 'Made of icy hydrogen compounds']],
  ['Neptune', 3.5, 132, 0x3a5bd9, 60190,['Farthest planet — deep blue', 'Fastest winds: over 2000 km/h', 'One orbit takes 165 Earth years']]
];

var planets = [];
P.forEach(function (d, i) {
  var pivot = new THREE.Object3D();          // orbits around sun
  pivot.rotation.y = Math.random() * Math.PI * 2;
  scene.add(pivot);

  var holder = new THREE.Object3D();
  holder.position.x = d[2];
  pivot.add(holder);

  var mesh = L3.sphere(d[1], d[3]);
  holder.add(mesh);

  // Earth's tilt + moon
  if (i === 2) {
    holder.rotation.z = 23.5 * Math.PI / 180;
    var moonPivot = new THREE.Object3D();
    mesh.add(moonPivot);
    var moon = L3.sphere(0.75, 0xbfbfbf);
    moon.position.x = 5;
    moonPivot.add(moon);
    holder.userData.moonPivot = moonPivot;
  }
  // Saturn's rings
  if (i === 5) {
    var ring = new THREE.Mesh(
      new THREE.TorusGeometry(d[1] * 1.9, 0.55, 2, 90),
      new THREE.MeshStandardMaterial({ color: 0xd9c9a3, roughness: 0.9 })
    );
    ring.rotation.x = Math.PI / 2.4;
    mesh.add(ring);
  }

  var lb = L3.label(d[0], '#dbe6ff', 0.9);
  lb.position.y = d[1] + 3.2;
  holder.add(lb);

  // orbit ring
  var ringGeo = new THREE.RingGeometry(d[2] - 0.15, d[2] + 0.15, 128);
  var ringMesh = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({
    color: 0x6b7ba8, side: THREE.DoubleSide, transparent: true, opacity: 0.5
  }));
  ringMesh.rotation.x = -Math.PI / 2;
  scene.add(ringMesh);

  planets.push({ name: d[0], r: d[1], dist: d[2], days: d[4], facts: d[5],
                 pivot: pivot, holder: holder, mesh: mesh, label: lb, ring: ringMesh });
});

/* ---------- interaction: click a planet ---------- */
var ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
var canvas = document.getElementById('cv');
var selected = null;
canvas.addEventListener('pointerup', function (e) {
  var rect = canvas.getBoundingClientRect();
  ptr.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  ptr.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  ray.setFromCamera(ptr, st.camera);
  var meshes = planets.map(function (p) { return p.mesh; });
  var hit = ray.intersectObjects(meshes, true)[0];
  if (!hit) return;
  var pl = planets.filter(function (p) { return p.mesh === hit.object || p.mesh.children.indexOf(hit.object) >= 0; })[0];
  if (pl) select(pl);
});

function select(pl) {
  selected = pl;
  document.getElementById('info').innerHTML =
    '<div style="font-weight:800;font-size:16px;color:#dbe6ff;">' + pl.name + '</div>' +
    '<div class="lk-readout">Distance from Sun: <b>' + pl.dist + ' units</b></div>' +
    '<div class="lk-readout">One year: <b>' + pl.days + ' Earth days</b></div>' +
    pl.facts.map(function (f) { return '<div class="lk-readout">• ' + f + '</div>'; }).join('');
  planets.forEach(function (p) { p.mesh.material.emissive.setHex(0x000000); });
  pl.mesh.material.emissive.setHex(0x224466);
}

/* ---------- controls ---------- */
var DAYS_PER_SEC = 5, simDays = 0;
LK.slider('spd', function (v) {
  DAYS_PER_SEC = [0, 1, 5, 15, 40, 120, 365][v] || 5;
  document.getElementById('spdv').textContent = v === 0 ? 'paused' : '1 s = ' + DAYS_PER_SEC + ' d';
});
LK.check('labelsChk', function (on) { planets.forEach(function (p) { p.label.visible = on; }); });
LK.check('orbitsChk', function (on) { planets.forEach(function (p) { p.ring.visible = on; }); });
LK.segment('viewSeg', function (i) {
  var o = st.orbit;
  if (i === 0) { o.phi = 0.12; o.radius = 210; }
  if (i === 1) { o.phi = Math.PI / 2 - 0.1; o.radius = 180; }
  if (i === 2) { o.phi = 0.9; o.radius = 160; }
  o.dTheta = 0; o.dPhi = 0;
});

/* ---------- animate ---------- */
st.frame = function (t) {
  var dt = Math.min(0.05, t - (st.__t || t)); st.__t = t;
  simDays += DAYS_PER_SEC * dt;
  sun.rotation.y += dt * 0.15;
  planets.forEach(function (p) {
    var rev = simDays / p.days;                 // revolutions completed
    p.pivot.rotation.y = rev * Math.PI * 2;
    p.mesh.rotation.y += dt * 1.6;              // planet spin
    if (p.holder.userData.moonPivot) {
      p.holder.userData.moonPivot.rotation.y = (simDays / 27.3) * Math.PI * 2;
    }
  });
  var yr = (simDays / 365) % 1;
  var yrEl = document.getElementById('yr');
  if (yrEl && (simDays | 0) !== (yrEl.__d | 0)) {
    yrEl.__d = simDays | 0;
    yrEl.textContent = 'Mission clock: ' + (simDays | 0) + ' Earth days (' + (simDays / 365).toFixed(1) + ' yr)';
  }
};
