'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { bg: 0x060913, minR: 20, maxR: 160, camPos: [0, 8, 62] });
var scene = st.scene;
scene.add(L3.stars(700, 500));

/* ---------- parameters ---------- */
var RUNGS = 22;                 // base pairs along the helix
var RISE = 2.6;                 // vertical distance per rung
var HELIX_R = 10;
var TURN = 4;                   // rungs per full turn (B-DNA ≈ 10 bases/turn → artistic license)
var twistK = 1, unzip = 0, showLetters = true;

var BASES = [
  { L: 'A', color: 0xf59e0b }, { L: 'T', color: 0x38bdf8 },
  { L: 'G', color: 0xef4444 }, { L: 'C', color: 0x22c55e }
];
// fixed sequence so complementary pairing is always correct
var seqL = 'ATGCCGATTACGGCATTCAGGT'.split('');
function complement(b) { return { A: 'T', T: 'A', G: 'C', C: 'G' }[b]; }

var root = new THREE.Group();
scene.add(root);

var strandMatA = new THREE.MeshStandardMaterial({ color: 0xc7d2fe, roughness: 0.35, metalness: 0.25 });
var strandMatB = new THREE.MeshStandardMaterial({ color: 0xa5f3fc, roughness: 0.35, metalness: 0.25 });
var bondGeoCache = {};

function baseByLetter(l) { return BASES.filter(function (b) { return b.L === l; })[0]; }

/* pre-build the helix as meshes we can re-position each frame */
var pairNodes = [];
var i, j;
for (i = 0; i < RUNGS; i++) {
  var y = (i - RUNGS / 2) * RISE;
  var frac = i / RUNGS;

  var nL = { side: 0, i: i, letter: seqL[i] };
  var nR = { side: 1, i: i, letter: complement(seqL[i]) };

  // backbone spheres
  var bA = L3.sphere(0.9, 0xc7d2fe, { roughness: 0.3 });
  var bB = L3.sphere(0.9, 0xa5f3fc, { roughness: 0.3 });
  root.add(bA); root.add(bB);
  nL.bb = bA; nR.bb = bB;

  // base half-rods: colored by base, length scales with unzip gap
  var colL = baseByLetter(seqL[i]).color;
  var colR = baseByLetter(complement(seqL[i])).color;
  var rodL = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 1, 14), new THREE.MeshStandardMaterial({ color: colL, roughness: 0.45 }));
  var rodR = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 1, 14), new THREE.MeshStandardMaterial({ color: colR, roughness: 0.45 }));
  root.add(rodL); root.add(rodR);
  nL.rod = rodL; nR.rod = rodR;

  // letters
  var labL = L3.label(seqL[i], '#' + new THREE.Color(colL).getHexString(), 0.8);
  var labR = L3.label(complement(seqL[i]), '#' + new THREE.Color(colR).getHexString(), 0.8);
  root.add(labL); root.add(labR);
  nL.lab = labL; nR.lab = labR;

  // hydrogen-bond dots (hidden when unzipped)
  var hbond = L3.sphere(0.22, 0xffffff, { emissive: 0x666666 });
  root.add(hbond);
  pairNodes.push({ i: i, y: y, frac: frac, nL: nL, nR: nR, hbond: hbond });
}

function v(x, y2, z) { return new THREE.Vector3(x, y2, z); }

st.frame = function (t) {
  var dt = Math.min(0.05, t - (st.__t || t)); st.__t = t;
  if (spinOn) root.rotation.y += dt * 0.35;

  var prevA = null, prevB = null;
  pairNodes.forEach(function (p) {
    // unzip opens from the top (replication fork moves down)
    var openFrac = LK.clamp((0.92 - p.frac) / 0.35, 0, 1);   // top pairs open first
    var openness = unzip * openFrac;
    var angle = p.i / TURN * Math.PI * 2 * twistK;
    var gap = openness * 6.5;
    var spread = openness * 0.55;

    var ax = Math.cos(angle) * (HELIX_R + gap), az = Math.sin(angle) * (HELIX_R + gap);
    var bx = Math.cos(angle + Math.PI) * (HELIX_R + gap), bz = Math.sin(angle + Math.PI) * (HELIX_R + gap);

    // tilt backbone positions outward as it opens
    p.nL.bb.position.set(ax, p.y + openness * 1.5, az);
    p.nR.bb.position.set(bx, p.y + openness * 1.5, bz);

    // base rods: from backbone toward center (or dangling when open)
    var rodLen = HELIX_R * (1 - spread) - 0.8;
    var centerT = 0.5;   // parameter where the two halves would meet
    function placeRod(rod, from, ang) {
      rod.scale.y = Math.max(0.5, rodLen / 2);
      var midR = (HELIX_R + gap - rodLen / 2) ;
      rod.position.set(Math.cos(ang) * midR, p.y + openness * 1.5, Math.sin(ang) * midR);
      rod.rotation.z = Math.PI / 2;
      rod.rotation.y = -ang;
    }
    placeRod(p.nL.rod, 0, angle);
    placeRod(p.nR.rod, 0, angle + Math.PI);

    // hydrogen bond dot at meeting point
    var meetR = (HELIX_R + gap) - rodLen - 0.4;
    p.hbond.position.set(Math.cos(angle) * meetR, p.y + openness * 1.5, Math.sin(angle) * meetR);
    p.hbond.visible = openness < 0.4;

    // letters float near the outer ends
    p.nL.lab.position.set(Math.cos(angle) * (HELIX_R + gap + 2.4), p.y + openness * 1.5, Math.sin(angle) * (HELIX_R + gap + 2.4));
    p.nR.lab.position.set(Math.cos(angle + Math.PI) * (HELIX_R + gap + 2.4), p.y + openness * 1.5, Math.sin(angle + Math.PI) * (HELIX_R + gap + 2.4));
    p.nL.lab.visible = showLetters;
    p.nR.lab.visible = showLetters;
  });
};

/* backbone connecting tubes — rebuilt each frame is costly; use two tube meshes with static curve, rotate group only */
var strandA = new THREE.Mesh(
  new THREE.TubeGeometry(helixCurve(0), 200, 0.42, 10, false), strandMatA);
var strandB = new THREE.Mesh(
  new THREE.TubeGeometry(helixCurve(Math.PI), 200, 0.42, 10, false), strandMatB);
root.add(strandA); root.add(strandB);

function helixCurve(phase) {
  var pts = [];
  for (var k = -1; k <= RUNGS; k++) {
    var y = (k - RUNGS / 2) * RISE;
    var a = k / TURN * Math.PI * 2 * twistK + phase;
    pts.push(v(Math.cos(a) * HELIX_R, y, Math.sin(a) * HELIX_R));
  }
  return new THREE.CatmullRomCurve3(pts);
}

/* controls */
var spinOn = true;
LK.slider('twist', function (v) {
  twistK = v;
  document.getElementById('twistv').textContent = v.toFixed(1) + '\u00D7';
  strandA.geometry.dispose(); strandB.geometry.dispose();
  strandA.geometry = new THREE.TubeGeometry(helixCurve(0), 200, 0.42, 10, false);
  strandB.geometry = new THREE.TubeGeometry(helixCurve(Math.PI), 200, 0.42, 10, false);
});
LK.slider('unzip', function (v) {
  unzip = v;
  document.getElementById('unzipv').textContent = Math.round(v * 100) + '%';
  if (v > 0.05) spinOn = false;
});
LK.check('spinChk', function (on) { spinOn = on; });
LK.check('pairsChk', function (on) { showLetters = on; });
