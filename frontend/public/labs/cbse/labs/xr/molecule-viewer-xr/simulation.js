'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), {
  xr: true, minR: 1.5, maxR: 14, camPos: [0, 1.5, 4.5], autoSpin: true
});
var scene = st.scene;
var EYE = 1.5;
st.orbit.target.set(0, EYE, 0);
scene.add(L3.stars(700, 30));

var CPK = { H: 0xf3f4f6, C: 0x334155, O: 0xef4444, N: 0x3b82f6 };
var RADII = { H: 0.14, C: 0.24, O: 0.20, N: 0.21 };

var MOLECULES = [
  { name: 'Water — H₂O', shape: 'Bent, 104.5°', scale: 1.15,
    fun: 'The bent shape makes water polar — hydrogen bonding, ice floating, life!',
    atoms: [['O', 0, 0, 0], ['H', 0.76, 0.59, 0], ['H', -0.76, 0.59, 0]],
    links: [[0, 1, 1], [0, 2, 1]] },
  { name: 'Carbon dioxide — CO₂', shape: 'Linear, 180°', scale: 1.0,
    fun: 'Symmetric double bonds cancel — a non-polar greenhouse gas.',
    atoms: [['O', -1.16, 0, 0], ['C', 0, 0, 0], ['O', 1.16, 0, 0]],
    links: [[0, 1, 2], [1, 2, 2]] },
  { name: 'Methane — CH₄', shape: 'Tetrahedral, 109.5°', scale: 1.0,
    fun: 'Simplest hydrocarbon — natural gas.',
    atoms: [['C', 0, 0, 0], ['H', 0.63, 0.63, 0.63], ['H', -0.63, -0.63, 0.63],
            ['H', -0.63, 0.63, -0.63], ['H', 0.63, -0.63, -0.63]],
    links: [[0, 1, 1], [0, 2, 1], [0, 3, 1], [0, 4, 1]] },
  { name: 'Ammonia — NH₃', shape: 'Pyramid, ~107°', scale: 1.05,
    fun: 'A lone pair on nitrogen squeezes the shape below 109.5°.',
    atoms: [['N', 0, 0.25, 0], ['H', 0.94, -0.15, 0], ['H', -0.47, -0.15, 0.81], ['H', -0.47, -0.15, -0.81]],
    links: [[0, 1, 1], [0, 2, 1], [0, 3, 1]] },
  { name: 'Ethanol — C₂H₅OH', shape: 'Chain + OH group', scale: 0.85,
    fun: 'The –OH end loves water, the C–H end refuses it.',
    atoms: [['C', -1.25, 0, 0], ['C', 0, 0.5, 0], ['O', 1.25, -0.25, 0], ['H', 2.0, 0.35, 0],
            ['H', -1.3, -0.6, 0.87], ['H', -1.3, -0.6, -0.87], ['H', -1.85, 0.9, 0],
            ['H', 0.1, 1.1, 0.87], ['H', 0.1, 1.1, -0.87]],
    links: [[0, 1, 1], [1, 2, 1], [2, 3, 1], [0, 4, 1], [0, 5, 1], [0, 6, 1], [1, 7, 1], [1, 8, 1]] }
];

var molGroup = new THREE.Group();
molGroup.position.set(0, EYE, -1.2);
scene.add(molGroup);
var idx = 0;
var hud = null;

function build(i) {
  idx = ((i % MOLECULES.length) + MOLECULES.length) % MOLECULES.length;
  var m = MOLECULES[idx];
  while (molGroup.children.length) molGroup.remove(molGroup.children[0]);
  var S = m.scale;

  m.atoms.forEach(function (a) {
    var el = L3.sphere(RADII[a[0]], CPK[a[0]], { roughness: 0.3 });
    el.position.set(a[1] * S, a[2] * S + 0.4, a[3] * S);
    molGroup.add(el);
  });
  m.links.forEach(function (L) {
    var a = m.atoms[L[0]], b = m.atoms[L[1]], order = L[2];
    var pa = new THREE.Vector3(a[1] * S, a[2] * S + 0.4, a[3] * S);
    var pb = new THREE.Vector3(b[1] * S, b[2] * S + 0.4, b[3] * S);
    var dir = pb.clone().sub(pa), len = dir.length(), mid = pa.clone().add(pb).multiplyScalar(0.5);
    function bond(offset) {
      var rod = new THREE.Mesh(
        new THREE.CylinderGeometry(0.035, 0.035, len * 0.72, 12),
        new THREE.MeshStandardMaterial({ color: 0xd4dae8, roughness: 0.4, metalness: 0.3 })
      );
      rod.position.copy(mid);
      if (offset) rod.position.add(offset);
      rod.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
      molGroup.add(rod);
    }
    if (order === 2) {
      var perp = new THREE.Vector3(0, 0, 1).cross(dir).normalize().multiplyScalar(0.06);
      if (perp.length() < 0.005) perp = new THREE.Vector3(0.06, 0, 0);
      bond(perp); bond(perp.clone().negate());
    } else bond(null);
  });

  // HUD title (visible in VR/AR too)
  if (hud) scene.remove(hud);
  hud = XRK.panel([
    { text: m.name },
    { text: 'Shape: ' + m.shape },
    { text: 'Trigger / click → next molecule' }
  ], { scale: 0.32 });
  hud.position.set(0, EYE + 0.95, -1.4);
  scene.add(hud);

  document.getElementById('mName').innerHTML = '<b style="font-size:15px;">' + m.name + '</b>';
  document.getElementById('mShape').innerHTML = 'Shape: <b>' + m.shape + '</b>';
  document.getElementById('mFun').innerHTML = '💡 ' + m.fun;
  // sync flat-mode segment
  document.querySelectorAll('#molSeg button').forEach(function (b2, i2) {
    b2.classList.toggle('active', i2 === idx);
  });
}

/* ---------- XR wiring ---------- */
XRK.controllers(st.renderer, scene, {
  onSelect: function () { build(idx + 1); },
  onSqueeze: function () { build(idx - 1); }
});
XRK.button(document.getElementById('vrBtnHolder'), st.renderer, {
  mode: 'immersive-vr', label: '\uD83E\uDD73 Enter VR'
});
var AR_BG = null;
XRK.button(document.getElementById('arBtnHolder'), st.renderer, {
  mode: 'immersive-ar', label: '\uD83D\uDCF7 Enter AR (place on desk)',
  onAR: function () { AR_BG = scene.background; scene.background = null; },   // transparent for camera passthrough
  onExitAR: function () { if (AR_BG) scene.background = AR_BG; }
});

/* ---------- flat mode ---------- */
LK.segment('molSeg', function (i) { build(i); });
document.getElementById('cv').addEventListener('pointerup', function (e) {
  if (st.renderer.xr.isPresenting) return;
  var r = this.getBoundingClientRect();
  var ray = new THREE.Raycaster();
  var m = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(m, st.camera);
  if (ray.intersectObjects(molGroup.children, true).length) build(idx + 1);
});

st.frame = function (t) {
  molGroup.rotation.y = Math.sin(t * 0.22) * 0.55;   // gentle sway so VR users see all sides
};

build(0);
