/* ============================================================
   LabKit-3D — shared Three.js scaffolding for the 3D labs.
   Custom orbit controls (drag=rotate, wheel=zoom) — no addons.
   Requires assets/three.min.js (MIT) loaded first.
   ============================================================ */
(function () {
  'use strict';
  if (!window.THREE) throw new Error('three.min.js must load before lab3d.js');

  var L3 = {};

  /* ---------- renderer + scene + camera + custom orbit ---------- */
  // opts: {bg: 0x000000, fog: [color, near, far], camPos:[x,y,z], minR, maxR}
  L3.init = function (canvas, opts) {
    opts = opts || {};
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    var scene = new THREE.Scene();
    scene.background = new THREE.Color(opts.bg !== undefined ? opts.bg : 0x05070f);
    if (opts.fog) scene.fog = new THREE.Fog(opts.fog[0], opts.fog[1], opts.fog[2]);

    var camera = new THREE.PerspectiveCamera(55, 1, 0.1, 5000);
    var camPos = opts.camPos || [0, 22, 55];
    camera.position.set(camPos[0], camPos[1], camPos[2]);

    scene.add(new THREE.AmbientLight(0xffffff, 0.55));
    var key = new THREE.DirectionalLight(0xffffff, 1.15);
    key.position.set(30, 50, 25);
    scene.add(key);
    var rim = new THREE.DirectionalLight(0x8fb7ff, 0.5);
    rim.position.set(-40, -20, -30);
    scene.add(rim);

    /* ----- orbit: spherical coords + damping ----- */
    var orbit = {
      theta: Math.atan2(camera.position.x, camera.position.z),
      phi: Math.acos(camera.position.y / camera.position.length()),
      radius: camera.position.length(),
      target: new THREE.Vector3(0, 0, 0),
      dTheta: 0, dPhi: 0, dR: 0,
      autoSpin: opts.autoSpin !== undefined ? opts.autoSpin : true
    };
    var dragging = false, lastX = 0, lastY = 0;
    canvas.style.touchAction = 'none';
    canvas.addEventListener('pointerdown', function (e) {
      dragging = true; lastX = e.clientX; lastY = e.clientY;
      orbit.autoSpin = false;
      try { canvas.setPointerCapture(e.pointerId); } catch (err) { }
      e.preventDefault();
    });
    canvas.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      orbit.dTheta = -(e.clientX - lastX) * 0.005;
      orbit.dPhi = -(e.clientY - lastY) * 0.005;
      lastX = e.clientX; lastY = e.clientY;
    });
    var stop = function () { dragging = false; };
    canvas.addEventListener('pointerup', stop);
    canvas.addEventListener('pointercancel', stop);
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      orbit.dR += e.deltaY * 0.02;
    }, { passive: false });

    function applyOrbit() {
      if (orbit.autoSpin) orbit.theta += 0.0018;
      orbit.theta += orbit.dTheta; orbit.phi += orbit.dPhi;
      orbit.dTheta *= 0.88; orbit.dPhi *= 0.88;
      orbit.radius += orbit.dR; orbit.dR *= 0.82;
      orbit.radius = THREE.MathUtils.clamp(orbit.radius, opts.minR || 8, opts.maxR || 500);
      orbit.phi = THREE.MathUtils.clamp(orbit.phi, 0.15, Math.PI - 0.15);
      var sp = Math.sin(orbit.phi), cp = Math.cos(orbit.phi);
      camera.position.set(
        orbit.target.x + orbit.radius * sp * Math.sin(orbit.theta),
        orbit.target.y + orbit.radius * cp,
        orbit.target.z + orbit.radius * sp * Math.cos(orbit.theta)
      );
      camera.lookAt(orbit.target);
    }

    /* ----- resize + loop ----- */
    function resize() {
      var r = canvas.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) return;
      renderer.setSize(r.width, r.height, false);
      camera.aspect = r.width / r.height;
      camera.updateProjectionMatrix();
    }
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(resize).observe(canvas);
    window.addEventListener('resize', resize);
    resize();

    var st3 = window.__sashaScene = { renderer: renderer, scene: scene, camera: camera, orbit: orbit, frame: null, ready: false };
    function loop(t, xrFrame) {
      if (!renderer.xr.isPresenting) applyOrbit();
      if (st3.frame) st3.frame(t / 1000);
      if (st3.xrFrame) st3.xrFrame(t / 1000, xrFrame);
      renderer.render(scene, camera);
      st3.ready = true;
    }
    renderer.xr.enabled = true;
    renderer.setAnimationLoop(loop);
    return st3;
  };

  /* ---------- helpers ---------- */
  L3.sphere = function (r, color, opts) {
    opts = opts || {};
    var mat = new THREE.MeshStandardMaterial({
      color: color,
      roughness: opts.roughness !== undefined ? opts.roughness : 0.65,
      metalness: opts.metalness || 0.05,
      emissive: opts.emissive || 0x000000,
      emissiveIntensity: opts.emissiveIntensity || 1
    });
    var seg = opts.seg || 48;
    return new THREE.Mesh(new THREE.SphereGeometry(r, seg, seg), mat);
  };

  L3.cylinder = function (r1, r2, len, color, opts) {
    opts = opts || {};
    return new THREE.Mesh(
      new THREE.CylinderGeometry(r1, r2, len, opts.seg || 24),
      new THREE.MeshStandardMaterial({ color: color, roughness: 0.4, metalness: 0.3 })
    );
  };

  // text label as a canvas sprite (always faces camera)
  L3.label = function (text, color, scale) {
    scale = scale || 1;
    var pad = 12, font = 42;
    var c = document.createElement('canvas');
    var ctx = c.getContext('2d');
    ctx.font = 'bold ' + font + 'px system-ui, sans-serif';
    var w = ctx.measureText(text).width;
    c.width = w + pad * 2; c.height = font + pad * 1.6;
    ctx = c.getContext('2d');
    ctx.font = 'bold ' + font + 'px system-ui, sans-serif';
    ctx.fillStyle = 'rgba(8,12,24,0.72)';
    ctx.beginPath();
    var rr = 14, x = 0, y = 0, ww = c.width, hh = c.height;
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + ww, y, x + ww, y + hh, rr);
    ctx.arcTo(x + ww, y + hh, x, y + hh, rr);
    ctx.arcTo(x, y + hh, x, y, rr);
    ctx.arcTo(x, y, x + ww, y, rr);
    ctx.fill();
    ctx.fillStyle = color || '#ffffff';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(text, c.width / 2, c.height / 2 + 2);
    var tex = new THREE.CanvasTexture(c);
    tex.minFilter = THREE.LinearFilter;
    var mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
    var sp = new THREE.Sprite(mat);
    sp.scale.set(c.width / 46 * scale, c.height / 46 * scale, 1);
    return sp;
  };

  // starfield Points
  L3.stars = function (count, spread) {
    count = count || 2200; spread = spread || 1400;
    var pos = new Float32Array(count * 3);
    for (var i = 0; i < count; i++) {
      var v = new THREE.Vector3().randomDirection().multiplyScalar(spread * (0.35 + Math.random() * 0.65));
      pos[i * 3] = v.x; pos[i * 3 + 1] = v.y; pos[i * 3 + 2] = v.z;
    }
    var g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    var m = new THREE.PointsMaterial({ color: 0xbfd4ff, size: 2.2, sizeAttenuation: false, transparent: true, opacity: 0.9 });
    return new THREE.Points(g, m);
  };

  // glowing sprite (sun / bloom-ish)
  L3.glow = function (color, size) {
    var c = document.createElement('canvas'); c.width = c.height = 128;
    var ctx = c.getContext('2d');
    var g = ctx.createRadialGradient(64, 64, 4, 64, 64, 64);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.25, color);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, 128, 128);
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(c), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false
    }));
    sp.scale.set(size, size, 1);
    return sp;
  };

  window.L3 = L3;
})();
