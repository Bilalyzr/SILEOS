'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { bg: 0x080b16, minR: 10, maxR: 90, camPos: [0, 12, 34] });
var scene = st.scene;
scene.add(L3.stars(800, 500));

var CPK = { H: 0xf3f4f6, C: 0x334155, O: 0xef4444, N: 0x3b82f6 };
var RADII = { H: 1.05, C: 1.7, O: 1.5, N: 1.55 };

/* atoms: [symbol, x, y, z] — coordinates in "bond units"
   bonds: [i, j, order(1|2)] */
var MOLECULES = [
  {
    name: 'Water — H₂O',
    shape: 'Bent (V-shape), bond angle 104.5°',
    bonds: '2 O–H single bonds · polar molecule',
    fun: 'The bent polar shape → hydrogen bonding → ice floats, water dissolves salts, life exists!',
    atoms: [['O', 0, 0, 0], ['H', 0.76, 0.59, 0], ['H', -0.76, 0.59, 0]],
    links: [[0, 1, 1], [0, 2, 1]]
  },
  {
    name: 'Carbon dioxide — CO₂',
    shape: 'Linear, bond angle 180°',
    bonds: '2 C=O double bonds · non-polar overall',
    fun: 'Symmetric double bonds cancel out → non-polar gas. Greenhouse gas that traps Earth\u2019s heat.',
    atoms: [['O', -1.16, 0, 0], ['C', 0, 0, 0], ['O', 1.16, 0, 0]],
    links: [[0, 1, 2], [1, 2, 2]]
  },
  {
    name: 'Methane — CH₄',
    shape: 'Tetrahedral, bond angles 109.5°',
    bonds: '4 C–H single bonds',
    fun: 'The simplest hydrocarbon — natural gas. One carbon + four hydrogens, perfectly symmetric.',
    atoms: [['C', 0, 0, 0],
            ['H', 0.63, 0.63, 0.63], ['H', -0.63, -0.63, 0.63],
            ['H', -0.63, 0.63, -0.63], ['H', 0.63, -0.63, -0.63]],
    links: [[0, 1, 1], [0, 2, 1], [0, 3, 1], [0, 4, 1]]
  },
  {
    name: 'Ammonia — NH₃',
    shape: 'Trigonal pyramid, H–N–H ≈ 107°',
    bonds: '3 N–H single bonds + one lone pair',
    fun: 'The lone pair squeezes the angle below 109.5°. Smell of old toilets & cleaning liquids!',
    atoms: [['N', 0, 0.25, 0],
            ['H', 0.94, -0.15, 0], ['H', -0.47, -0.15, 0.81], ['H', -0.47, -0.15, -0.81]],
    links: [[0, 1, 1], [0, 2, 1], [0, 3, 1]]
  },
  {
    name: 'Ethanol — C₂H₅OH',
    shape: 'Chain with a bent –OH group',
    bonds: 'C–C, C–H and one C–O + O–H',
    fun: 'Alcohol in hand sanitiser! The –OH end loves water, the C–H end does not — a molecular split personality.',
    atoms: [['C', -1.25, 0, 0], ['C', 0, 0.5, 0], ['O', 1.25, -0.25, 0], ['H', 2.0, 0.35, 0],
            ['H', -1.3, -0.6, 0.87], ['H', -1.3, -0.6, -0.87], ['H', -1.85, 0.9, 0],
            ['H', 0.1, 1.1, 0.87], ['H', 0.1, 1.1, -0.87]],
    links: [[0, 1, 1], [1, 2, 1], [2, 3, 1],
            [0, 4, 1], [0, 5, 1], [0, 6, 1], [1, 7, 1], [1, 8, 1]]
  }
];

var SCALE = 6.2;
var root = new THREE.Group();
scene.add(root);
var selectedIdx = 0;

function build(idx) {
  selectedIdx = idx;
  var m = MOLECULES[idx];
  while (root.children.length) root.remove(root.children[0]);

  m.atoms.forEach(function (a) {
    var el = L3.sphere(RADII[a[0]], CPK[a[0]], { roughness: 0.3, metalness: 0.1 });
    el.position.set(a[1] * SCALE, a[2] * SCALE, a[3] * SCALE);
    root.add(el);
    var lb = L3.label(a[0] === 'H' ? 'H' : a[0], '#e2e8f0', 0.62);
    lb.position.set(a[1] * SCALE, a[2] * SCALE + RADII[a[0]] + 0.8, a[3] * SCALE);
    root.add(lb);
  });

  m.links.forEach(function (L) {
    var a = m.atoms[L[0]], b = m.atoms[L[1]], order = L[2];
    var pa = new THREE.Vector3(a[1] * SCALE, a[2] * SCALE, a[3] * SCALE);
    var pb = new THREE.Vector3(b[1] * SCALE, b[2] * SCALE, b[3] * SCALE);
    var dir = pb.clone().sub(pa);
    var len = dir.length();
    var mid = pa.clone().add(pb).multiplyScalar(0.5);

    function bond(offset) {
      var rod = new THREE.Mesh(
        new THREE.CylinderGeometry(0.28, 0.28, len * 0.72, 14),
        new THREE.MeshStandardMaterial({ color: 0xd4dae8, roughness: 0.4, metalness: 0.3 })
      );
      rod.position.copy(mid);
      if (offset) rod.position.add(offset);
      rod.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
      root.add(rod);
    }
    if (order === 2) {
      var perp = new THREE.Vector3(0, 0, 1).cross(dir).normalize().multiplyScalar(0.5);
      if (perp.length() < 0.01) perp = new THREE.Vector3(1, 0, 0).multiplyScalar(0.5);
      bond(perp); bond(perp.clone().negate());
    } else {
      bond(null);
    }
  });

  document.getElementById('mName').innerHTML = '<b style="font-size:15px;">' + m.name + '</b>';
  document.getElementById('mShape').innerHTML = 'Shape: <b>' + m.shape + '</b>';
  document.getElementById('mBonds').innerHTML = 'Bonds: <b>' + m.bonds + '</b>';
  document.getElementById('mFun').innerHTML = '💡 ' + m.fun;
}

LK.segment('molSeg', function (i) { build(i); });
st.orbit.autoSpin = true;
build(0);
