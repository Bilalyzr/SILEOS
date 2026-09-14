'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

var st = L3.init(document.getElementById('cv'), { xr: true, bg: 0x0b1120, minR: 2, maxR: 18, camPos: [0, 5, 9] });
st.orbit.target.set(0, 1.2, 0);
var scene = st.scene;
scene.add(L3.stars(1800, 160));
var EYE = 1.5;

var s = { tod: 10, season: 172 };
var LAT = 28.6 * Math.PI / 180;      // Delhi latitude

/* ---------- ground + dial plate ---------- */
var ground = new THREE.Mesh(
  new THREE.CircleGeometry(3.4, 64),
  new THREE.MeshStandardMaterial({ color: 0xf9fafb, roughness: 0.9 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = 0.02;
scene.add(ground);

// hour marks on the dial (positions are for the shadow tip; compute in frame)
var hourDots = new THREE.Group();
scene.add(hourDots);

/* gnomon: a triangular style pointing to the celestial pole (north, tilted by latitude) */
var gnomon = new THREE.Group();
scene.add(gnomon);
var gStyle = new THREE.Mesh(
  new THREE.ConeGeometry(0.05, 1.8, 4),
  new THREE.MeshStandardMaterial({ color: 0xf97316, roughness: 0.35 })
);
gStyle.rotation.x = Math.PI / 2 - LAT;      // tilted toward north pole
gStyle.rotation.z = 0;
gStyle.position.set(0, 0.9, 0.85 * Math.sin(LAT) * 0 + 0);
gnomon.add(gStyle);
var styleTip = new THREE.Vector3(0, 1.8 * Math.cos(Math.PI / 2 - LAT) , -1.8 * Math.sin(Math.PI / 2 - LAT));
// simpler: tip direction = polar axis
var polarAxis = new THREE.Vector3(0, Math.cos(LAT), -Math.sin(LAT)).multiplyScalar(1.8);
styleTip = polarAxis.clone();

/* shadow of the gnomon: a dark quad from base toward the anti-sun direction */
var shadow = new THREE.Mesh(
  new THREE.PlaneGeometry(1, 1),
  new THREE.MeshBasicMaterial({ color: 0x0f1b33, transparent: true, opacity: 0.45, side: THREE.DoubleSide })
);
shadow.rotation.x = -Math.PI / 2;
scene.add(shadow);

/* sun with seasonal declination arc */
var sun = L3.sphere(0.55, 0xf59e0b, { emissive: 0xff8c00, emissiveIntensity: 1.6 });
scene.add(sun);
scene.add(L3.glow('rgba(255,170,40,0.9)', 4));
var sunLight = new THREE.DirectionalLight(0xfff2d8, 2.6);
scene.add(sunLight);

/* sun position from time-of-day + season (declination −23.4°..+23.4°) */
function sunDir() {
  var dayOfYear = s.season;
  var decl = 23.44 * Math.PI / 180 * Math.sin((2 * Math.PI * (dayOfYear - 81)) / 365);
  var hourAngle = (s.tod - 12) * 15 * Math.PI / 180;               // 15°/h from local noon
  var el = Math.asin(Math.sin(LAT) * Math.sin(decl) + Math.cos(LAT) * Math.cos(decl) * Math.cos(hourAngle));
  var az = Math.atan2(-Math.sin(hourAngle), Math.tan(decl) * Math.cos(LAT) - Math.sin(LAT) * Math.cos(hourAngle));
  return { el: el, az: az, up: el > 0 };
}

function fmtTime(t) {
  var h = Math.floor(t), m = Math.round((t - h) * 60);
  if (m === 60) { h = (h + 1) % 24; m = 0; }
  return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
}

function upd() {
  var sd = sunDir();
  var R = 8;
  sun.position.set(Math.sin(sd.az) * Math.cos(sd.el) * R, Math.sin(sd.el) * R, -Math.cos(sd.az) * Math.cos(sd.el) * R);
  sunLight.position.copy(sun.position);
  if (!sd.up) sun.position.y = -Math.abs(sun.position.y) * 0.2 + 0.3;   // below horizon: dim at edge

  // shadow: direction opposite to horizontal sun bearing; length ∝ 1/tan(elevation)
  if (sd.up) {
    var len = LK.clamp(1.4 / Math.tan(sd.el), 0.2, 3.2);
    var dirAz = Math.atan2(-sun.position.x, sun.position.z);   // away from sun horizontally
    shadow.visible = true;
    shadow.scale.set(0.16, len, 1);
    shadow.position.set(Math.sin(dirAz) * len / 2, 0.04, Math.cos(dirAz) * len / 2);
    shadow.rotation.z = -dirAz;
    document.getElementById('sundialRead').textContent = fmtTime(s.tod);
    document.getElementById('shadowInfo').innerHTML =
      'Sun elevation: <b>' + (sd.el * 180 / Math.PI).toFixed(0) + '\u00B0</b> · shadow length: <b>' + len.toFixed(2) + ' m</b>' +
      '<br>' + (s.tod < 12 ? 'Morning — shadow points west' : s.tod > 12 ? 'Afternoon — shadow points east' : 'Local noon — shortest shadow, pointing due north');
  } else {
    shadow.visible = false;
    document.getElementById('sundialRead').textContent = 'night';
    document.getElementById('shadowInfo').innerHTML = 'Sun below the horizon — no shadow to read. (Stars were the night clock!)';
  }
  document.getElementById('todv').textContent = fmtTime(s.tod);
  var seasonName = s.season < 80 ? 'winter' : s.season < 172 ? 'spring/summer' : s.season < 265 ? 'monsoon' : 'winter';
  document.getElementById('seasonv').textContent = 'Day ' + s.season;
}

XRK.button(document.getElementById('vrBtnHolder'), st.renderer, { mode: 'immersive-vr', label: '\uD83E\uDD73 Enter VR' });

st.frame = function (t) {
  sun.rotation.y = t * 0.2;
};

LK.slider('tod', function (v) { s.tod = v; upd(); });
LK.slider('season', function (v) { s.season = v; upd(); });
upd();
