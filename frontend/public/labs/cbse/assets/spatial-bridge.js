/* Sasha spatial adapter: original scenes stay 3D; 2D experiments become interactive panels.
   Only reviewed local labs load this adapter. Uploaded packs contain data, never scripts. */
(function () {
  'use strict';
  var T = window.THREE, originalCanvas = document.querySelector('.lk-stage canvas, #stage canvas');
  var stage = document.querySelector('.lk-stage, #stage'), mirror = !originalCanvas, capturing = false, lastCapture = 0;
  if (!T || !stage) return;
  if(mirror){stage=document.querySelector('main');originalCanvas=document.createElement('canvas');originalCanvas.width=900;originalCanvas.height=650;}
  var native = window.__sashaScene, state = null, session = null, hitSource = null, placed = false;
  var buttons = [], controls = [], page = 0, panel, panelTexture, panelCanvas, world, reticle, raycaster;
  var snapshot, panelMesh, flatMesh, savedFrame, note, activeMode, lastPaint = 0, spatialScale = 1;
  var bar = document.createElement('section'); bar.className = 'sasha-spatial-bar';
  var label = document.createElement('strong'); label.textContent = native ? 'Explore this 3D scene' : 'Explore on a spatial experiment panel'; bar.appendChild(label);
  note = document.createElement('p'); note.setAttribute('role', 'status');
  note.textContent = 'Checking AR and VR support. Mouse, touch and keyboard work in screen mode.';
  bar.appendChild(note); document.querySelector('.lk-main, main').before(bar);
  document.querySelectorAll('a[href="../../index.html"]').forEach(function (a) { a.href = '/labs'; a.target = '_top'; });
  document.querySelectorAll('button').forEach(function (b) {
    if (/^(Enter VR|Enter AR)/.test(b.textContent.trim())) b.hidden = true;
  });
  function status(text) { note.textContent = text; }
  function textLabel(el) {
    var row = el.closest('.lk-row'), linked = el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
    if(el.hasAttribute('data-org'))return 'Inspect '+el.getAttribute('data-org');
    if(el.classList.contains('coef'))return 'Coefficient '+(Number(el.getAttribute('data-i'))+1)+' · '+el.textContent;
    return (linked || row && row.querySelector('label'))?.textContent.trim() || el.getAttribute('aria-label') || el.textContent.trim() || el.id || 'Control';
  }
  function refreshControls() {
    controls = Array.from(document.querySelectorAll('main input[type=range], main input[type=number], main input[type=checkbox], main select, main button, main [data-org], main .coef'))
      .filter(function (el) { return !el.hidden && !el.disabled && el.getClientRects().length > 0 && !/Enter [AV]R/.test(el.textContent); });
  }
  function paint() {
    refreshControls();
    var ctx = panelCanvas.getContext('2d'), start = page * 7;
    ctx.fillStyle = '#10283e'; ctx.fillRect(0, 0, 640, 760);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 27px sans-serif'; ctx.fillText('Experiment controls', 26, 43);
    ctx.font = '18px sans-serif'; ctx.fillStyle = '#a8bacb'; ctx.fillText('Point + trigger · sliders: left − / right +', 26, 74);
    controls.slice(start, start + 7).forEach(function (el, i) {
      var y = 100 + i * 75; ctx.fillStyle = '#203f59'; ctx.fillRect(18, y, 604, 65);
      ctx.fillStyle = '#fff'; ctx.font = '21px sans-serif'; ctx.fillText(textLabel(el).slice(0, 40), 30, y + 26);
      ctx.fillStyle = '#fdba74'; ctx.font = '19px sans-serif';
      var value = el.tagName === 'SELECT' ? el.options[el.selectedIndex]?.text : el.type === 'checkbox' ? (el.checked ? 'On' : 'Off') : el.tagName === 'BUTTON' ? 'Activate' : '−     ' + el.value + '     +';
      ctx.fillText(String(value || '').slice(0, 46), 30, y + 53);
    });
    ctx.fillStyle = '#fff'; ctx.font = '20px sans-serif';
    ctx.fillText('← Previous       ' + (page + 1) + '/' + Math.max(1, Math.ceil(controls.length / 7)) + '       Next →', 30, 680);
    ctx.fillStyle = '#fdba74'; ctx.fillText('Exit immersive mode', 185, 727); panelTexture.needsUpdate = true;
  }
  function activate(uv) {
    var x = uv.x * 640, y = (1 - uv.y) * 760;
    if (y > 699) { session?.end(); return; }
    if (y > 645) { page = Math.max(0, Math.min(Math.ceil(controls.length / 7) - 1, page + (x < 320 ? -1 : 1))); paint(); return; }
    var index = Math.floor((y - 100) / 75), el = controls[page * 7 + index];
    if (index < 0 || index > 6 || !el || el.disabled) return;
    if (el.tagName === 'BUTTON' || el.hasAttribute('data-org') || el.classList.contains('coef')) el.dispatchEvent(new MouseEvent(el.classList.contains('coef') && x < 320 ? 'contextmenu' : 'click',{bubbles:true,cancelable:true}));
    else if (el.tagName === 'SELECT') { el.selectedIndex = (el.selectedIndex + 1) % el.options.length; el.dispatchEvent(new Event('change', { bubbles: true })); }
    else {
      if (el.type === 'checkbox') el.checked = !el.checked;
      else { var step = Number(el.step) || 1; el.value = String(Math.max(el.min === '' ? -10000 : Number(el.min), Math.min(el.max === '' ? 10000 : Number(el.max), Number(el.value) + (x < 320 ? -step : step)))); }
      el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true }));
    }
    paint();
  }
  function select(controller) {
    var m = new T.Matrix4().extractRotation(controller.matrixWorld);
    raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
    raycaster.ray.direction.set(0, 0, -1).applyMatrix4(m);
    var hit = raycaster.intersectObject(panelMesh)[0];
    if (hit && panelMesh.visible) { activate(hit.uv); return; }
    if (activeMode === 'immersive-ar' && reticle.visible) {
      world.position.setFromMatrixPosition(reticle.matrix); placed = true; world.visible = true; reticle.visible = false;
      status('Placed. Use the experiment controls; exit AR to return to the page.'); return;
    }
    if (flatMesh) {
      hit = raycaster.intersectObject(flatMesh)[0];
      if (hit) {
        var rect = (mirror?stage:originalCanvas).getBoundingClientRect();
        var opts = {bubbles:true, clientX:rect.left+hit.uv.x*rect.width, clientY:rect.top+(1-hit.uv.y)*rect.height, pointerId:1};
        var target=mirror?document.elementFromPoint(opts.clientX,opts.clientY):originalCanvas;
        if(target){target.dispatchEvent(new PointerEvent('pointerdown',opts)); target.dispatchEvent(new PointerEvent('pointerup',opts)); target.dispatchEvent(new MouseEvent('click',opts));}
      }
    }
  }
  function setup() {
    if (state) return;
    if (native) state = native;
    else {
      var canvas = document.createElement('canvas'); canvas.hidden = true; document.body.appendChild(canvas);
      state = { renderer: new T.WebGLRenderer({canvas:canvas,alpha:true,antialias:true}), scene:new T.Scene(), camera:new T.PerspectiveCamera(60,1,.01,100) };
    }
    state.renderer.xr.enabled = true; state.renderer.xr.setReferenceSpaceType('local');
    world = new T.Group();
    if (native) {
      state.scene.children.slice().forEach(function (c) { if (!c.isLight && !c.isCamera && c.type !== 'Group') world.add(c); });
      // Model groups are part of the experiment as well; XR controllers are not.
      state.scene.children.slice().forEach(function(c) { if (c.type === 'Group' && !c.userData?.isController) world.add(c); });
      var bounds = new T.Box3(); world.updateMatrixWorld(true);
      world.traverse(function(obj){if(obj.isMesh)bounds.expandByObject(obj);});
      var size = bounds.getSize(new T.Vector3());
      var extent = Math.max(size.x, size.y, size.z);
      if (Number.isFinite(extent) && extent > 0) spatialScale = 1.7 / extent;
    } else {
      snapshot = new T.CanvasTexture(originalCanvas);
      flatMesh = new T.Mesh(new T.PlaneGeometry(2.3,2.3*originalCanvas.height/originalCanvas.width),new T.MeshBasicMaterial({map:snapshot,side:T.DoubleSide})); world.add(flatMesh);
    }
    state.scene.add(world);
    panelCanvas = document.createElement('canvas'); panelCanvas.width=640; panelCanvas.height=760;
    panelTexture = new T.CanvasTexture(panelCanvas);
    panelMesh = new T.Mesh(new T.PlaneGeometry(.85,1.01),new T.MeshBasicMaterial({map:panelTexture,side:T.DoubleSide}));
    panelMesh.position.set(1.35,1.25,-2); state.scene.add(panelMesh);
    reticle = new T.Mesh(new T.RingGeometry(.07,.09,32).rotateX(-Math.PI/2),new T.MeshBasicMaterial({color:0xfb923c,side:T.DoubleSide}));
    reticle.matrixAutoUpdate=false; reticle.visible=false; state.scene.add(reticle);
    raycaster = new T.Raycaster();
    [0,1].forEach(function(i) {
      var c=state.renderer.xr.getController(i); c.userData.isController=true;
      var line=new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(),new T.Vector3(0,0,-3)]),new T.LineBasicMaterial({color:0xfb923c})); c.add(line);
      c.addEventListener('select',function(){select(c);});state.scene.add(c);
    });
    if(native){
      // Experiment rebuilds continue to target this group in both screen and XR modes.
      state.scene.add=function(){world.add.apply(world,arguments);return state.scene;};
      state.scene.remove=function(){world.remove.apply(world,arguments);return state.scene;};
    }
    paint();
  }
  function frame(time, xrFrame) {
    if (!session) return;
    if (!native) {
      if(window.__sashaRender)window.__sashaRender();
      (window.__sashaCanvases || []).forEach(function(s){if(s.draw)s.draw(s);}); snapshot.needsUpdate=true;
      if(mirror && !capturing && time-lastCapture>.5 && window.html2canvas){
        capturing=true;lastCapture=time;
        window.html2canvas(stage,{backgroundColor:'#fff',logging:false,scale:1,onclone:function(doc){doc.body.classList.remove('sasha-in-ar');}}).then(function(canvas){
          var ctx=originalCanvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,900,650);ctx.drawImage(canvas,0,0,900,650);snapshot.needsUpdate=true;
        }).catch(function(){status('The spatial panel could not refresh. Exit XR to continue in screen mode.');}).finally(function(){capturing=false;});
      }
    }
    if (time-lastPaint>.25) {paint();lastPaint=time;}
    if (xrFrame && hitSource && !placed) {
      var hits=xrFrame.getHitTestResults(hitSource); reticle.visible=hits.length>0;
      if(hits.length) {var pose=hits[0].getPose(state.renderer.xr.getReferenceSpace());if(pose)reticle.matrix.fromArray(pose.transform.matrix);}
    }
    if(!native) state.renderer.render(state.scene,state.camera);
  }
  async function start(mode) {
    buttons.forEach(function(b){b.disabled=true;}); activeMode=mode;
    try {
      setup();
      var opts={optionalFeatures:['local-floor']};
      if(mode==='immersive-ar') {opts.requiredFeatures=['hit-test'];opts.optionalFeatures.push('dom-overlay');opts.domOverlay={root:document.body};}
      var next=await navigator.xr.requestSession(mode,opts); session=next;exit.disabled=false;
      panel={background:state.scene.background,fog:state.scene.fog,position:state.camera.position.clone(),quaternion:state.camera.quaternion.clone()};
      state.scene.background=mode==='immersive-ar'?null:new T.Color('#071b2b'); state.scene.fog=null;
      world.scale.setScalar(spatialScale);
      world.position.set(0,mode==='immersive-ar'?0:1.35,-2); world.visible=mode!=='immersive-ar';placed=false;
      panelMesh.visible=mode==='immersive-vr' || !next.domOverlayState;state.camera.position.set(0,0,0);state.camera.quaternion.identity();
      next.addEventListener('end',end,{once:true});
      await state.renderer.xr.setSession(next);
      if(mode==='immersive-ar') {
        document.body.classList.add('sasha-in-ar');
        var viewer=await next.requestReferenceSpace('viewer');hitSource=await next.requestHitTestSource({space:viewer});
        status('Move your device until the orange ring appears, then tap to place the experiment. Page controls remain available on browsers with DOM overlay.');
      } else status('Point a controller at the control panel and press the trigger. Use the panel exit button when finished.');
      if(native){savedFrame=state.xrFrame;state.xrFrame=frame;}else state.renderer.setAnimationLoop(function(t,f){frame(t/1000,f);});
    } catch(err) { if(session)await session.end().catch(function(){}); status('Could not enter '+(mode==='immersive-ar'?'AR':'VR')+': '+err.message+'. Screen mode remains available.'); buttons.forEach(function(b){b.disabled=b.dataset.supported!=='true';}); }
  }
  function end() {
    document.body.classList.remove('sasha-in-ar');
    exit.disabled=true;hitSource?.cancel();hitSource=null;session=null;reticle.visible=false;world.visible=true;world.position.set(0,0,0);
    if(panel){state.scene.background=panel.background;state.scene.fog=panel.fog;state.camera.position.copy(panel.position);state.camera.quaternion.copy(panel.quaternion);}
    panelMesh.visible=false;if(native){state.xrFrame=savedFrame;world.scale.setScalar(1);}else state.renderer.setAnimationLoop(null);
    buttons.forEach(function(b){b.disabled=b.dataset.supported!=='true';});status('Back in screen mode. Your experiment settings have been preserved.');
  }
  ['immersive-ar','immersive-vr'].forEach(function(mode){
    var b=document.createElement('button');b.className='lk-btn';b.textContent=mode==='immersive-ar'?'Enter AR':'Enter VR';b.disabled=true;
    b.addEventListener('click',function(){start(mode);});bar.insertBefore(b,note);buttons.push(b);
    if(!window.isSecureContext || !navigator.xr){status('AR/VR needs HTTPS (or localhost) and a compatible browser/device. Screen mode is ready.');return;}
    navigator.xr.isSessionSupported(mode).then(function(ok){b.dataset.supported=String(ok);b.disabled=!ok;status(buttons.some(function(x){return x.dataset.supported==='true';})?'Available modes are enabled. Entry starts only when you choose it.':'No compatible XR device detected. Screen mode is ready.');}).catch(function(){status('XR permission is unavailable. Screen mode is ready.');});
  });
  var exit=document.createElement('button');exit.className='lk-btn ghost';exit.textContent='Exit AR / VR';exit.disabled=true;exit.addEventListener('click',function(){session?.end();});bar.insertBefore(exit,note);
  window.addEventListener('pagehide',function(){session?.end();});
})();
