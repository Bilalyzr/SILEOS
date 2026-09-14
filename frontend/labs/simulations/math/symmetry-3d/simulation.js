'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { xr: true, bg: 0x0b1120, minR: 2, maxR: 14, camPos: [0, 1.6, 5] });
st.orbit.target.set(0, 1.5, 0);
var scene = st.scene;
scene.add(L3.stars(400, 30));
var EYE = 1.5;

var s = { shape: 0, rot: 0, flip: 0, spin: false };
var SHAPES = [
  { name: 'Equilateral triangle', sides: 3, order: 3, lines: 3 },
  { name: 'Square', sides: 4, order: 4, lines: 4 },
  { name: 'Regular hexagon', sides: 6, order: 6, lines: 6 },
  { name: 'Star (5-point)', sides: 10, order: 5, lines: 5, star: true },
  { name: 'Kite', sides: 4, order: 1, lines: 1, kite: true }
];

var root = new THREE.Group();
root.position.set(0, EYE, 0);
scene.add(root);

var shapeGroup = new THREE.Group();
root.add(shapeGroup);
var mirrorGroup = new THREE.Group();
mirrorGroup.visible = false;
root.add(mirrorGroup);

function polygonGeometry(shape) {
  var pts = [];
  var n = shape.sides;
  for (var i = 0; i < n; i++) {
    var a = i / n * Math.PI * 2 + Math.PI / 2;
    var r = 1;
    if (shape.star) r = i % 2 === 0 ? 1 : 0.45;
    if (shape.kite) {
      pts.length = 0;
      pts.push(new THREE.Vector2(0, 1.15));
      pts.push(new THREE.Vector2(0.55, 0.1));
      pts.push(new THREE.Vector2(0.28, -1.05));
      pts.push(new THREE.Vector2(-0.28, -1.05));
      pts.push(new THREE.Vector2(-0.55, 0.1));
      break;
    }
    pts.push(new THREE.Vector2(Math.cos(a) * r, Math.sin(a) * r));
  }
  return new THREE.ShapeGeometry(new THREE.Shape(pts));
}

var mainMesh = null, mirrorMesh = null, mirrorLine = null;
function build() {
  while (shapeGroup.children.length) shapeGroup.remove(shapeGroup.children[0]);
  while (mirrorGroup.children.length) mirrorGroup.remove(mirrorGroup.children[0]);
  var sh = SHAPES[s.shape];
  var geo = polygonGeometry(sh);
  mainMesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
    color: 0xf97316, side: THREE.DoubleSide, roughness: 0.45, metalness: 0.05
  }));
  shapeGroup.add(mainMesh);
  // outline
  var outline = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ color: 0xffffff }));
  shapeGroup.add(outline);
  // mirrored twin
  mirrorMesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
    color: 0x38bdf8, side: THREE.DoubleSide, roughness: 0.45, transparent: true, opacity: 0.55
  }));
  mirrorGroup.add(mirrorMesh);
  // mirror plane (line in 2D → plane in 3D)
  mirrorLine = new THREE.Mesh(
    new THREE.PlaneGeometry(0.02, 2.8),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8, side: THREE.DoubleSide })
  );
  mirrorGroup.add(mirrorLine);
  upd();
}

var lastMatch = -1;
function upd() {
  if (!mainMesh) return;                       // sliders wire before first build()
  var sh = SHAPES[s.shape];
  shapeGroup.rotation.z = -s.rot * Math.PI / 180;
  mirrorGroup.visible = s.flip > 0;
  mirrorGroup.rotation.z = -s.flip * Math.PI / 180;
  mirrorGroup.scale.x = -1;    // reflected copy across the vertical plane
  // glow when rotation lands on a symmetry multiple
  var step = 360 / sh.order;
  var near = Math.abs((s.rot % step) - 0) < 3 || Math.abs((s.rot % step) - step) < 3;
  mainMesh.material.emissive = new THREE.Color(near ? 0x9a3412 : 0x000000);
  mainMesh.material.emissiveIntensity = near ? 0.8 : 0;
  document.getElementById('report').innerHTML =
    '<b>' + sh.name + '</b><br>Rotational symmetry order: <b>' + sh.order + '</b>' +
    ' (matches itself every ' + step.toFixed(0) + '\u00B0)<br>Lines of symmetry: <b>' + sh.lines + '</b>' +
    (near ? '<br><b style="color:#059669;">✓ matched itself!</b>' : '');
}

XRK.button(document.getElementById('vrBtnHolder'), st.renderer, { mode: 'immersive-vr', label: '\uD83E\uDD73 Enter VR' });

st.frame = function (t) {
  if (s.spin) {
    s.rot = (s.rot + 0.6) % 360;
    document.getElementById('rot').value = s.rot;
    document.getElementById('rotv').textContent = Math.round(s.rot) + '\u00B0';
    upd();
  }
  root.rotation.y = Math.sin(t * 0.25) * 0.25;
};

LK.segment('shapeSeg', function (i) { s.shape = i; s.rot = 0; build(); });
LK.slider('rot', function (v) {
  s.rot = v; s.spin = false;
  document.getElementById('rotv').textContent = v + '\u00B0';
  upd();
});
LK.slider('flip', function (v) {
  s.flip = v;
  document.getElementById('flipv').textContent = v + '\u00B0';
  upd();
});
LK.button('spinBtn', function () {
  s.spin = !s.spin;
  this.textContent = s.spin ? '\u23F8 Stop' : '\u25B6 Spin & watch it match';
});
build();
