'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { bg: 0x0a0e1a, minR: 8, maxR: 60, camPos: [14, 12, 26] });
var scene = st.scene;
scene.add(L3.stars(500, 300));

var s = { shape: 0, d: [4, 3, 2] };
var group = new THREE.Group();
scene.add(group);
var wire = null, solidMesh = null;

var SHAPES = [
  { name: 'Cube', dims: [['Edge a', 0]], color: 0x818cf8,
    SA: function (d) { return 6 * d[0] * d[0]; },
    V: function (d) { return d[0] * d[0] * d[0]; },
    fun: '6 equal square faces — the box with perfect symmetry.',
    build: buildCube },
  { name: 'Cuboid', dims: [['Length l', 0], ['Breadth b', 1], ['Height h', 2]], color: 0x60a5fa,
    SA: function (d) { return 2 * (d[0] * d[1] + d[1] * d[2] + d[0] * d[2]); },
    V: function (d) { return d[0] * d[1] * d[2]; },
    fun: 'A stretched cube — bricks, books, rooms, your phone.',
    build: buildBox },
  { name: 'Cylinder', dims: [['Radius r', 0], ['Height h', 1]], color: 0x34d399,
    SA: function (d) { return 2 * Math.PI * d[0] * (d[0] + d[1]); },
    V: function (d) { return Math.PI * d[0] * d[0] * d[1]; },
    fun: 'Curved area = 2πrh — unroll it and you get a rectangle!',
    build: buildCylinder },
  { name: 'Cone', dims: [['Radius r', 0], ['Height h', 1]], color: 0xfbbf24,
    SA: function (d) { var l = Math.hypot(d[0], d[1]); return Math.PI * d[0] * (d[0] + l); },
    V: function (d) { return Math.PI * d[0] * d[0] * d[1] / 3; },
    fun: 'Exactly ⅓ of the cylinder that contains it. Ice-cream approved.',
    build: buildCone },
  { name: 'Sphere', dims: [['Radius r', 0]], color: 0xf472b6,
    SA: function (d) { return 4 * Math.PI * d[0] * d[0]; },
    V: function (d) { return 4 / 3 * Math.PI * d[0] * d[0] * d[0]; },
    fun: 'One measurement rules them all: everything from r.',
    build: buildSphere }
];

function clearGroup() {
  while (group.children.length) group.remove(group.children[0]);
  if (wire) { wire.geometry.dispose(); wire = null; }
}

function addMesh(geo, color) {
  var mat = new THREE.MeshStandardMaterial({ color: color, roughness: 0.35, metalness: 0.15, transparent: true, opacity: 0.92 });
  solidMesh = new THREE.Mesh(geo, mat);
  group.add(solidMesh);
  wire = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 20),
    new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5 }));
  group.add(wire);
}

function buildCube(d) { addMesh(new THREE.BoxGeometry(d[0], d[0], d[0]), SHAPES[0].color); }
function buildBox(d) { addMesh(new THREE.BoxGeometry(d[0], d[1], d[2]), SHAPES[1].color); }
function buildCylinder(d) { addMesh(new THREE.CylinderGeometry(d[0], d[0], d[1], 64), SHAPES[2].color); }
function buildCone(d) { addMesh(new THREE.ConeGeometry(d[0], d[1], 64), SHAPES[3].color); }
function buildSphere(d) { addMesh(new THREE.SphereGeometry(d[0], 48, 48), SHAPES[4].color); }

function rebuild() {
  clearGroup();
  var sh = SHAPES[s.shape];
  sh.build(s.d);
  document.getElementById('rSA').innerHTML = 'Surface area: <b>' + sh.SA(s.d).toFixed(1) + ' cm²</b>';
  document.getElementById('rV').innerHTML = 'Volume: <b>' + sh.V(s.d).toFixed(1) + ' cm³</b>';
  document.getElementById('rFun').innerHTML = '💡 ' + sh.fun;
}

function configDims() {
  var sh = SHAPES[s.shape];
  for (var i = 0; i < 3; i++) {
    var row = document.getElementById('dim' + (i + 1) + 'Row');
    var used = i < sh.dims.length;
    row.style.display = used ? '' : 'none';
    if (used) document.getElementById('dim' + (i + 1) + 'Name').textContent = sh.dims[i][0];
  }
}

LK.segment('shapeSeg', function (i) { s.shape = i; configDims(); rebuild(); });
['d1', 'd2', 'd3'].forEach(function (id, idx) {
  LK.slider(id, function (v) {
    s.d[idx] = v;
    document.getElementById(id + 'v').textContent = v.toFixed(1);
    rebuild();
  });
});

configDims();
rebuild();
