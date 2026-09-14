/* ============================================================
   XRKit — WebXR integration layer for the CBSE Virtual Labs.
   Hand-written (no three.js addons): session button, VR/AR
   session management, controller rigs with ray pointers.
   Requires three.min.js + lab3d.js (init with {xr:true}).
   ============================================================ */
(function () {
  'use strict';
  if (!window.THREE) throw new Error('three.min.js must load before xrkit.js');

  var XRK = {};

  /* ---------- capability probe ---------- */
  // returns {available, vr, ar, reason}
  XRK.probe = function () {
    if (!('xr' in navigator)) {
      return Promise.resolve({
        available: false, vr: false, ar: false,
        reason: navigator.userAgent.indexOf('Quest') >= 0
          ? 'XR blocked — enable WebXR in the browser settings'
          : 'WebXR not available in this browser. Use Meta Quest Browser, Chrome with a headset, or a WebXR phone.'
      });
    }
    return Promise.all([
      navigator.xr.isSessionSupported('immersive-vr').catch(function () { return false; }),
      navigator.xr.isSessionSupported('immersive-ar').catch(function () { return false; })
    ]).then(function (r) {
      return {
        available: true, vr: r[0], ar: r[1],
        reason: (r[0] || r[1]) ? '' : 'No XR device detected. Connect a headset (or try in Meta Quest Browser) — flat 3D mode still works fully.'
      };
    });
  };

  /* ---------- session button ---------- */
  // container: DOM element; renderer: THREE.WebGLRenderer; opts: {mode:'immersive-vr'|'immersive-ar', label, onStart(session), onEnd}
  XRK.button = function (container, renderer, opts) {
    var btn = document.createElement('button');
    btn.className = 'lk-btn';
    btn.textContent = opts.label || 'Enter VR';
    btn.disabled = true;
    btn.style.opacity = '.55';
    var note = document.createElement('div');
    note.className = 'lk-hint';
    note.style.marginTop = '6px';
    container.appendChild(btn);
    container.appendChild(note);

    function setNote(t) { note.textContent = t; }

    XRK.probe().then(function (cap) {
      var ok = opts.mode === 'immersive-ar' ? cap.ar : cap.vr;
      if (!cap.available || !ok) {
        setNote((cap.reason || 'This device does not report ' + (opts.mode === 'immersive-ar' ? 'AR' : 'VR') + ' support.') +
                ' You can still explore in 3D with mouse/touch.');
        return;
      }
      btn.disabled = false;
      btn.style.opacity = '1';
      setNote('Ready — put on the headset and tap ' + btn.textContent + '.');
    });

    btn.addEventListener('click', function () {
      btn.disabled = true;
      navigator.xr.requestSession(opts.mode, {
        optionalFeatures: ['local-floor', 'bounded-floor', 'hand-tracking', 'layers']
      }).then(function (session) {
        if (opts.mode === 'immersive-ar' && opts.onAR) opts.onAR();
        renderer.xr.setSession(session).then(function () {
          btn.textContent = '\u2713 In ' + (opts.mode === 'immersive-ar' ? 'AR' : 'VR');
          if (opts.onStart) opts.onStart(session);
        });
        session.addEventListener('end', function () {
          btn.textContent = opts.label || 'Enter VR';
          btn.disabled = false;
          if (opts.onAR && opts.mode === 'immersive-ar' && opts.onExitAR) opts.onExitAR();
          if (opts.onEnd) opts.onEnd();
        });
      }).catch(function (err) {
        btn.disabled = false;
        setNote('Could not start the session: ' + (err && err.message ? err.message : err) + '. Retry, or use flat 3D.');
      });
    });
    return { btn: btn, note: note };
  };

  /* ---------- controller rigs ---------- */
  // adds two controllers with visible laser pointers; wires select + squeeze.
  // handlers: {onSelect(controller, worldPos, direction), onSelectEnd, onSqueeze}
  XRK.controllers = function (renderer, scene, handlers) {
    var rigs = [];
    [0, 1].forEach(function (i) {
      var c = renderer.xr.getController(i);
      var geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -1)
      ]);
      var line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0x38bdf8 }));
      line.scale.z = 3.2;
      c.add(line);
      var tip = new THREE.Mesh(
        new THREE.SphereGeometry(0.012, 12, 12),
        new THREE.MeshBasicMaterial({ color: 0x38bdf8 })
      );
      c.add(tip);
      c.addEventListener('selectstart', function () {
        line.material.color.setHex(0xf59e0b);
        if (handlers && handlers.onSelect) handlers.onSelect(c);
      });
      c.addEventListener('selectend', function () {
        line.material.color.setHex(0x38bdf8);
        if (handlers && handlers.onSelectEnd) handlers.onSelectEnd(c);
      });
      c.addEventListener('squeezestart', function () {
        if (handlers && handlers.onSqueeze) handlers.onSqueeze(c);
      });
      scene.add(c);
      rigs.push(c);
    });
    return rigs;
  };

  // raycaster from a controller (pointing along -Z of the controller)
  var _m = new THREE.Matrix4();
  XRK.rayFromController = function (controller, raycaster) {
    _m.identity().extractRotation(controller.matrixWorld);
    raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
    raycaster.ray.direction.set(0, 0, -1).applyMatrix4(_m);
    return raycaster;
  };

  // floating HUD panel (sprite) for showing info inside VR
  XRK.panel = function (lines, opts) {
    opts = opts || {};
    var w = opts.w || 640, lh = opts.lh || 46, pad = 26;
    var c = document.createElement('canvas');
    c.width = w; c.height = pad * 2 + lines.length * lh + 16;
    var ctx = c.getContext('2d');
    ctx.fillStyle = 'rgba(6,10,24,0.86)';
    var r = 26, x = 0, y = 0, ww = c.width, hh = c.height;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + ww, y, x + ww, y + hh, r);
    ctx.arcTo(x + ww, y + hh, x, y + hh, r);
    ctx.arcTo(x, y + hh, x, y, r);
    ctx.arcTo(x, y, x + ww, y, r);
    ctx.fill();
    ctx.strokeStyle = 'rgba(56,189,248,.7)'; ctx.lineWidth = 3; ctx.stroke();
    ctx.textBaseline = 'middle';
    lines.forEach(function (ln, i) {
      ctx.font = (i === 0 ? 'bold 40px' : '34px') + ' system-ui, sans-serif';
      ctx.fillStyle = i === 0 ? '#7dd3fc' : '#e2e8f0';
      ctx.fillText(ln.text || ln, pad, pad + lh / 2 + i * lh + 8);
    });
    var tex = new THREE.CanvasTexture(c);
    tex.minFilter = THREE.LinearFilter;
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
    sp.scale.set((opts.scale || 1.1) * (c.width / 300), (opts.scale || 1.1) * (c.height / 300), 1);
    return sp;
  };

  window.XRK = XRK;
})();
