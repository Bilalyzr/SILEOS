'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { bg: 0x070a14, minR: 14, maxR: 120, camPos: [0, 18, 42] });
var scene = st.scene;
scene.add(L3.stars(900, 700));

var ELEMENTS = [
  ['Hydrogen', 'H', 1], ['Helium', 'He', 2], ['Lithium', 'Li', 1], ['Beryllium', 'Be', 2],
  ['Boron', 'B', 3], ['Carbon', 'C', 4], ['Nitrogen', 'N', 3], ['Oxygen', 'O', 2],
  ['Fluorine', 'F', 1], ['Neon', 'Ne', 0], ['Sodium', 'Na', 1], ['Magnesium', 'Mg', 2],
  ['Aluminium', 'Al', 3], ['Silicon', 'Si', 4], ['Phosphorus', 'P', 3, ], ['Sulphur', 'S', 2],
  ['Chlorine', 'Cl', 1], ['Argon', 'Ar', 0], ['Potassium', 'K', 1], ['Calcium', 'Ca', 2]
];
function shellsFor(z) {           // K=2, L=8, M=8 (simplified for ≤20), rest in N
  var s = [];
  var caps = [2, 8, 8, 18];
  for (var i = 0; z > 0 && i < 4; i++) {
    s.push(Math.min(z, caps[i]));
    z -= caps[i];
  }
  return s;
}

var nucleus = new THREE.Group(); scene.add(nucleus);
var shellGroup = new THREE.Group(); scene.add(shellGroup);
var s = { Z: 6, N: 6 };

function rebuild() {
  nucleus.clear(); shellGroup.clear();

  /* ----- nucleus: protons + neutrons packed ----- */
  var nucleons = s.Z + s.N;
  var nuclR = Math.max(1.6, 0.62 * Math.cbrt(nucleons) * 1.9);
  var protonG = new THREE.SphereGeometry(0.62, 20, 20);
  var neutronG = new THREE.SphereGeometry(0.62, 20, 20);
  var protonM = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.35 });
  var neutronM = new THREE.MeshStandardMaterial({ color: 0x9aa4b8, roughness: 0.35 });
  // fibonacci-ish packing
  var i;
  for (i = 0; i < nucleons; i++) {
    var isP = i < s.Z;
    var m = new THREE.Mesh(isP ? protonG : neutronG, isP ? protonM : neutronM);
    if (i === 0) m.position.set(0, 0, 0);
    else {
      var k = i - 1;
      var phi = Math.acos(1 - 2 * (k + 0.5) / nucleons);
      var theta = Math.PI * (1 + Math.sqrt(5)) * k;
      var rr = nuclR * Math.cbrt((k + 0.5) / nucleons) * 1.15;
      m.position.set(rr * Math.sin(phi) * Math.cos(theta), rr * Math.sin(phi) * Math.sin(theta), rr * Math.cos(phi));
    }
    nucleus.add(m);
  }

  /* ----- shells + electrons ----- */
  var shells = shellsFor(s.Z);
  var baseR = nuclR + 2.6;
  shells.forEach(function (count, si) {
    var R = baseR + si * 2.9;
    var ring = new THREE.Mesh(
      new THREE.TorusGeometry(R, 0.05, 8, 120),
      new THREE.MeshBasicMaterial({ color: 0x4466aa, transparent: true, opacity: 0.55 })
    );
    ring.rotation.x = Math.PI / 2 * (0.35 + si * 0.28);
    ring.rotation.y = si * 0.7;
    shellGroup.add(ring);

    var pivot = new THREE.Group();
    pivot.rotation.copy(ring.rotation);
    shellGroup.add(pivot);

    var eG = new THREE.SphereGeometry(0.42, 18, 18);
    var eM = new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x0c4a6e, roughness: 0.3 });
    for (var e = 0; e < count; e++) {
      var el = new THREE.Mesh(eG, eM);
      var a = e / count * Math.PI * 2;
      el.position.set(Math.cos(a) * R, 0, Math.sin(a) * R);
      pivot.add(el);
    }
    var shellNames = ['K', 'L', 'M', 'N'];
    var lb = L3.label(shellNames[si] + ' = ' + count, '#8fd0ff', 0.75);
    lb.position.set(0, R + 1.2, 0);
    shellGroup.add(lb);

    pivots.push({ pivot: pivot, speed: 0.9 / (si + 1), phase: si * 1.3 });
  });

  upd();
}
var pivots = [];

/* ----- rotation + gentle nucleus wobble ----- */
st.frame = function (t) {
  var dt = Math.min(0.05, t - (st.__t || t)); st.__t = t;
  pivots.forEach(function (p) { p.pivot.rotation.y += dt * p.speed * 2.2; });
  nucleus.rotation.y += dt * 0.35;
  nucleus.rotation.x = Math.sin(t * 0.4) * 0.12;
};

function upd() {
  var el = ELEMENTS[s.Z - 1];
  var shells = shellsFor(s.Z);
  var valence = [2, 10, 18].indexOf(s.Z) >= 0 ? 0 : el[2];
  var mass = s.Z + s.N;

  document.getElementById('elName').textContent = el[0] + ' (' + el[1] + ')';
  document.getElementById('elData').innerHTML =
    'Protons: <b>' + s.Z + '</b> · Electrons: <b>' + s.Z + '</b> · Neutrons: <b>' + s.N + '</b> · Mass no.: <b>' + mass + '</b>';
  document.getElementById('elShells').innerHTML =
    'Configuration: <b>' + shells.join(', ') + '</b> (K, L, M, N)';
  document.getElementById('elVal').innerHTML =
    'Valence electrons: <b>' + shells[shells.length - 1] + '</b> · Typical valency (school model): <b>' + valence + '</b>' +
    '<br>Changing neutrons gives an isotope of the same element. Not every selected neutron count represents a stable isotope.';

}

LK.slider('z', function (v) {
  s.Z = v;
  document.getElementById('zv').textContent = v;
  // sensible default neutron count
  var typicalN = [0, 2, 4, 5, 6, 6, 7, 8, 10, 10, 12, 12, 14, 14, 16, 16, 20, 22, 20, 20][v - 1] || v;
  document.getElementById('n').value = typicalN;
  s.N = typicalN;
  document.getElementById('nv').textContent = typicalN;
  pivots = []; rebuild();
});
LK.slider('n', function (v) {
  s.N = v;
  document.getElementById('nv').textContent = v;
  pivots = []; rebuild();
});

rebuild();
