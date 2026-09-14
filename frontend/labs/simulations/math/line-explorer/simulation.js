'use strict';

/* ================= state ================= */
const DEFAULTS = { m: 2, b: 3 };
const state = {
  m: DEFAULTS.m,
  b: DEFAULTS.b,
  mode: 'explore',          // 'explore' | 'challenge'
  showTriangle: true,
  showTable: false,
  snap: true,
  hint: false,
  solved: false,
  target: { m: 0, b: 0 },   // challenge target line
  drag: null,               // {type:'b'|'m'|'line', gx, gy}
  mouse: null,              // css-px position over canvas
  hover: null,              // 'b' | 'm' | 'line' | null
  confetti: [],
};

/* ================= dom ================= */
const $ = id => document.getElementById(id);
const canvas = $('graph'), ctx = canvas.getContext('2d');
const stage = $('stage'), banner = $('banner'), coords = $('coords');
const eqDisplay = $('eqDisplay'), targetEq = $('targetEq');
const sliders = { m: $('mSlider'), b: $('bSlider') };
const slidersC = { m: $('mSliderC'), b: $('bSliderC') };
const valEls = { m: $('mVal'), b: $('bVal') };
const valElsC = { m: $('mValC'), b: $('bValC') };
const chkTriangle = $('chkTriangle'), chkTable = $('chkTable'), chkSnap = $('chkSnap'), chkHint = $('chkHint');

/* ================= view / coords ================= */
const view = { scale: 30, cx: 0, cy: 0, w: 0, h: 0, dpr: 1 };

function resizeCanvas(){
  const w = stage.clientWidth, h = stage.clientHeight;
  const dpr = window.devicePixelRatio || 1;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)){
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  view.w = w; view.h = h; view.dpr = dpr;
  view.scale = Math.min(w, h) / 22;      // at least ±11 units visible on both axes
  view.cx = w / 2;
  view.cy = h / 2;
}

const px = x => view.cx + x * view.scale;           // math x -> css px
const py = y => view.cy - y * view.scale;           // math y -> css px
const mx = X => (X - view.cx) / view.scale;         // css px -> math x
const my = Y => (view.cy - Y) / view.scale;         // css px -> math y

/* ================= helpers ================= */
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
function snapVal(v){
  return state.snap ? Math.round(v * 2) / 2 : Math.round(v * 20) / 20;
}

// v is a multiple of 0.5 -> pretty string with real minus sign
function fmtCoef(v){
  const neg = v < 0, a = Math.abs(v);
  const s = Number.isInteger(a) ? String(a) : a.toFixed(1);
  return (neg ? '\u2212' : '') + s;
}

// builds "y = ..." HTML; tokens colored via cls ('tok-m' style classes handled by caller pairs)
function eqHTML(m, b, clsM, clsB){
  const M = c => clsM ? '<span class="' + clsM + '">' + c + '</span>' : c;
  const B = c => clsB ? '<span class="' + clsB + '">' + c + '</span>' : c;
  if (m === 0 && b === 0) return 'y = 0';
  if (m === 0) return 'y = ' + B(fmtCoef(b));
  let s = 'y = ';
  if (m === 1)       s += M('x');
  else if (m === -1) s += M('\u2212x');
  else               s += M(fmtCoef(m)) + M('x');
  if (b !== 0){
    s += B(' ' + (b > 0 ? '+' : '\u2212') + ' ') + B(fmtCoef(Math.abs(b)));
  }
  return s;
}

/* ================= challenge ================= */
function genTarget(){
  const cur = { m: Math.round(state.m * 2), b: Math.round(state.b * 2) };
  let tm, tb;
  do {
    tm = Math.floor(Math.random() * 17) - 8;   // -4 .. 4 in halves
    tb = Math.floor(Math.random() * 25) - 12;  // -6 .. 6 in halves
  } while (tm === cur.m && tb === cur.b);
  state.target = { m: tm / 2, b: tb / 2 };
  state.solved = false;
}

/* ================= state -> ui ================= */
function update(){
  for (const k of ['m', 'b']){
    sliders[k].value = state[k];
    slidersC[k].value = state[k];
    valEls[k].textContent = fmtCoef(state[k]);
    valElsC[k].textContent = fmtCoef(state[k]);
  }
  eqDisplay.innerHTML = eqHTML(state.m, state.b, 'tok-m', 'tok-b');

  if (state.mode === 'challenge'){
    const hit = state.m === state.target.m && state.b === state.target.b;
    if (hit && !state.solved){
      state.solved = true;
      spawnConfetti(view.w / 2, 46);
    }
    if (!hit) state.solved = false;
    banner.classList.toggle('hidden', !state.solved);
    targetEq.classList.toggle('hidden', !state.hint);
    targetEq.innerHTML = eqHTML(state.target.m, state.target.b, 'tok-t', 'tok-t');
  } else {
    banner.classList.add('hidden');
  }

  $('tableCard').classList.toggle('hidden', !state.showTable);
  if (state.showTable){
    const rows = [];
    for (let x = -2; x <= 2; x++){
      const y = (Math.round(state.m * 2) * x + Math.round(state.b * 2)) / 2;
      rows.push('<tr><td>' + x + '</td><td>' + fmtCoef(y) + '</td></tr>');
    }
    $('valTable').innerHTML = rows.join('');
  }
}

/* ================= drawing ================= */
function drawGrid(){
  const { scale, cx, cy, w, h } = view;
  const xMin = mx(0), xMax = mx(w), yMin = my(h), yMax = my(0);

  ctx.lineWidth = 1;
  for (let x = Math.ceil(xMin); x <= Math.floor(xMax); x++){
    ctx.strokeStyle = (x % 5 === 0) ? '#e2e8f0' : '#f1f5f9';
    ctx.beginPath(); ctx.moveTo(px(x), 0); ctx.lineTo(px(x), h); ctx.stroke();
  }
  for (let y = Math.ceil(yMin); y <= Math.floor(yMax); y++){
    ctx.strokeStyle = (y % 5 === 0) ? '#e2e8f0' : '#f1f5f9';
    ctx.beginPath(); ctx.moveTo(0, py(y)); ctx.lineTo(w, py(y)); ctx.stroke();
  }

  // axes
  ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(0, py(0)); ctx.lineTo(w, py(0)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(px(0), 0); ctx.lineTo(px(0), h); ctx.stroke();

  // axis labels + arrowheads
  ctx.fillStyle = '#94a3b8';
  ctx.font = 'italic 15px Georgia, serif';
  ctx.fillText('x', w - 14, py(0) - 8);
  ctx.fillText('y', px(0) + 10, 16);
  arrow(w - 4, py(0), 0); arrow(px(0), 4, -Math.PI / 2);

  // tick numbers
  const step = scale >= 26 ? 2 : (scale >= 13 ? 4 : 5);
  ctx.font = '12px system-ui, sans-serif';
  ctx.fillStyle = '#94a3b8';
  for (let x = Math.ceil(xMin / step) * step; x <= xMax; x += step){
    if (x === 0) continue;
    ctx.fillText(String(x), px(x) - (String(x).length * 3.6), py(0) + 15);
  }
  for (let y = Math.ceil(yMin / step) * step; y <= yMax; y += step){
    if (y === 0) continue;
    ctx.fillText(String(y), px(0) + 6, py(y) + 4);
  }
  ctx.fillText('0', px(0) - 12, py(0) + 15);
}

function arrow(tipX, tipY, angle){
  ctx.save();
  ctx.translate(tipX, tipY); ctx.rotate(angle);
  ctx.fillStyle = '#94a3b8';
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(-9, -4.5); ctx.lineTo(-9, 4.5); ctx.closePath(); ctx.fill();
  ctx.restore();
}

function strokeLine(m, b, color, width, dash){
  ctx.save();
  ctx.strokeStyle = color; ctx.lineWidth = width;
  if (dash) ctx.setLineDash(dash);
  const T = 20000;
  ctx.beginPath();
  ctx.moveTo(view.cx - T, view.cy - b * view.scale + m * T);
  ctx.lineTo(view.cx + T, view.cy - b * view.scale - m * T);
  ctx.stroke();
  ctx.restore();
}

function drawTriangle(){
  const m = state.m, b = state.b;
  if (m === 0) return;
  const x0 = 0, x1 = 2, y0 = b, y1 = 2 * m + b;

  // run (horizontal, amber)
  ctx.strokeStyle = '#d97706'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.moveTo(px(x0), py(y0)); ctx.lineTo(px(x1), py(y0)); ctx.stroke();
  // rise (vertical, teal)
  ctx.strokeStyle = '#0d9488';
  ctx.beginPath(); ctx.moveTo(px(x1), py(y0)); ctx.lineTo(px(x1), py(y1)); ctx.stroke();
  // right-angle marker
  ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 1;
  const s = 8, ax = px(x1), ay = py(y0), dir = y1 > y0 ? -1 : 1;
  ctx.strokeRect(Math.min(ax, ax - s), Math.min(ay, ay + dir * s), s, s);

  ctx.font = 'italic 13px Georgia, serif';
  ctx.fillStyle = '#b45309';
  ctx.textAlign = 'center';
  ctx.fillText('run = 2', (px(x0) + px(x1)) / 2, py(y0) + (m > 0 ? 18 : -10));
  ctx.textAlign = 'left';
  ctx.fillStyle = '#0f766e';
  ctx.fillText('rise = ' + fmtCoef(2 * m), px(x1) + 7, (py(y0) + py(y1)) / 2 + 4);
  ctx.textAlign = 'start';
}

function chip(cx0, cy0, text, bg){
  ctx.font = 'bold 12px system-ui, sans-serif';
  const w = ctx.measureText(text).width + 16;
  const x = clamp(cx0 - w / 2, 6, view.w - w - 6);
  const y = clamp(cy0, 6, view.h - 26);
  ctx.fillStyle = bg;
  roundRect(x, y, w, 21, 7);
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.textAlign = 'center';
  ctx.fillText(text, x + w / 2, y + 15);
  ctx.textAlign = 'start';
}

function roundRect(x, y, w, h, r){
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawHandle(X, Y, letter, color, active){
  const r = active === state.drag ? 13 : (state.hover === letter ? 12.5 : 11);
  // halo
  if (state.hover === letter || state.drag && state.drag.type === letter){
    ctx.fillStyle = color === '#d97706' ? 'rgba(217,119,6,.16)' : 'rgba(13,148,136,.16)';
    ctx.beginPath(); ctx.arc(X, Y, r + 6, 0, Math.PI * 2); ctx.fill();
  }
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.arc(X, Y, r + 2.5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(X, Y, r, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.font = 'italic bold 13px Georgia, serif';
  ctx.textAlign = 'center';
  ctx.fillText(letter, X, Y + 4.5);
  ctx.textAlign = 'start';
}

function distToLine(X, Y, m, b){
  // distance from css-px point to line y = m*x + b, in css px
  return Math.abs(m * mx(X) - my(Y) + b) / Math.sqrt(m * m + 1) * view.scale;
}

function hitTest(X, Y){
  const bx = px(0), by = py(state.b);
  const mXp = px(1), mYp = py(state.b + state.m);
  if (Math.hypot(X - bx, Y - by) < 20) return 'b';
  if (Math.hypot(X - mXp, Y - mYp) < 20) return 'm';
  if (distToLine(X, Y, state.m, state.b) < 12) return 'line';
  return null;
}

function drawCoordsChip(){
  if (!state.mouse){ coords.style.display = 'none'; return; }
  const x = mx(state.mouse.x), y = my(state.mouse.y);
  coords.textContent = '(' + x.toFixed(1) + ', ' + y.toFixed(1) + ')';
  coords.style.display = 'block';
  coords.style.left = state.mouse.x + 'px';
  coords.style.top = state.mouse.y + 'px';
}

/* ================= confetti ================= */
const CONFETTI_COLORS = ['#4f46e5', '#0d9488', '#d97706', '#f43f5e', '#16a34a', '#8b5cf6'];
function spawnConfetti(x, y){
  for (let i = 0; i < 90; i++){
    state.confetti.push({
      x, y,
      vx: (Math.random() - 0.5) * 9,
      vy: -Math.random() * 8 - 2,
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.35,
      life: 1,
      color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
    });
  }
}
function stepConfetti(){
  ctx.save();
  for (let i = state.confetti.length - 1; i >= 0; i--){
    const p = state.confetti[i];
    p.vy += 0.22; p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life -= 0.011;
    if (p.life <= 0){ state.confetti.splice(i, 1); continue; }
    ctx.save();
    ctx.globalAlpha = Math.max(0, p.life);
    ctx.translate(p.x, p.y); ctx.rotate(p.rot);
    ctx.fillStyle = p.color;
    ctx.fillRect(-3, -5, 6, 10);
    ctx.restore();
  }
  ctx.restore();
}

/* ================= render loop ================= */
function render(external){
  resizeCanvas();
  ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
  ctx.clearRect(0, 0, view.w, view.h);

  drawGrid();

  if (state.mode === 'challenge'){
    strokeLine(state.target.m, state.target.b, '#f43f5e', 3.5, [11, 9]);
  }
  if (state.showTriangle && state.mode === 'explore') drawTriangle();

  strokeLine(state.m, state.b, '#4f46e5', 4);

  // handles + value chips
  const bx = px(0), by = py(state.b);
  const mXp = px(1), mYp = py(state.b + state.m);
  drawHandle(bx, by, 'b', '#d97706', 'b');
  drawHandle(mXp, mYp, 'm', '#0d9488', 'm');
  chip(bx, by - 34, 'b = ' + fmtCoef(state.b), '#d97706');
  chip(mXp, mYp - 34, 'm = ' + fmtCoef(state.m), '#0d9488');

  stepConfetti();
  drawCoordsChip();
  if (external !== true) requestAnimationFrame(render);
}

/* ================= pointer interaction ================= */
function canvasPos(e){
  const r = canvas.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}

canvas.addEventListener('pointerdown', e => {
  const p = canvasPos(e);
  const hit = hitTest(p.x, p.y);
  if (!hit) return;
  canvas.setPointerCapture(e.pointerId);
  state.drag = hit === 'line'
    ? { type: 'line', gx: mx(p.x), gy: my(p.y) }
    : { type: hit };
  e.preventDefault();
});

canvas.addEventListener('pointermove', e => {
  const p = canvasPos(e);
  state.mouse = p;
  if (state.drag){
    const Y = my(p.y);
    if (state.drag.type === 'b'){
      state.b = clamp(snapVal(Y), -10, 10);
    } else if (state.drag.type === 'm'){
      state.m = clamp(snapVal(Y - state.b), -5, 5);
    } else { // 'line' — keep slope, translate intercept
      state.b = clamp(snapVal(my(p.y) - state.m * state.drag.gx), -10, 10);
    }
    update();
  } else {
    state.hover = hitTest(p.x, p.y);
  }
  canvas.style.cursor = (state.drag || state.hover) ? 'grab' : 'crosshair';
});

canvas.addEventListener('pointerup', () => { state.drag = null; });
canvas.addEventListener('pointerleave', () => {
  state.mouse = null; state.hover = null; state.drag = null;
  canvas.style.cursor = 'crosshair';
});

/* ================= ui wiring ================= */
function onSlider(k){
  return e => { state[k] = parseFloat(e.target.value); update(); };
}
sliders.m.addEventListener('input', onSlider('m'));
sliders.b.addEventListener('input', onSlider('b'));
slidersC.m.addEventListener('input', onSlider('m'));
slidersC.b.addEventListener('input', onSlider('b'));

chkTriangle.addEventListener('change', () => { state.showTriangle = chkTriangle.checked; });
chkTable.addEventListener('change', () => { state.showTable = chkTable.checked; update(); });
chkSnap.addEventListener('change', () => { state.snap = chkSnap.checked; });
chkHint.addEventListener('change', () => { state.hint = chkHint.checked; update(); });

$('newChallengeBtn').addEventListener('click', () => { genTarget(); update(); });
$('resetBtn').addEventListener('click', () => {
  state.m = DEFAULTS.m; state.b = DEFAULTS.b;
  state.showTriangle = true; state.showTable = false; state.snap = true; state.hint = false;
  chkTriangle.checked = true; chkTable.checked = false; chkSnap.checked = true; chkHint.checked = false;
  genTarget();
  update();
});

function setMode(mode){
  state.mode = mode;
  $('tabExplore').classList.toggle('active', mode === 'explore');
  $('tabChallenge').classList.toggle('active', mode === 'challenge');
  $('exploreSec').classList.toggle('hidden', mode !== 'explore');
  $('challengeSec').classList.toggle('hidden', mode !== 'challenge');
  if (mode === 'challenge') genTarget();
  state.solved = false;
  update();
}
$('tabExplore').addEventListener('click', () => setMode('explore'));
$('tabChallenge').addEventListener('click', () => setMode('challenge'));

/* ================= go ================= */
window.addEventListener('resize', resizeCanvas);
genTarget();
update();
window.__sashaRender = function () { render(true); };
render(); // draw immediately; render() re-queues itself via requestAnimationFrame
