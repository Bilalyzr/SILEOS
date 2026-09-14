'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

/* Each reaction: sides = [[formula...] left, [formula...] right]; solution = coefficient array */
var REACTIONS = [
  { name: 'Water', chem: ['2H₂ + O₂ → 2H₂O'],
    sides: [['H₂', 'O₂'], ['H₂O']], sol: [2, 1, 2],
    hint: 'Start with oxygen: O₂ gives 2 atoms, but H₂O has only 1. So H₂O needs coefficient 2.' },
  { name: 'Iron + steam', chem: ['3Fe + 4H₂O → Fe₃O₄ + 4H₂'],
    sides: [['Fe', 'H₂O'], ['Fe₃O₄', 'H₂']], sol: [3, 4, 1, 4],
    hint: 'Fe₃O₄ has 4 oxygens → H₂O must be 4. Then count hydrogens.' },
  { name: 'Magnesium oxide', chem: ['2Mg + O₂ → 2MgO'],
    sides: [['Mg', 'O₂'], ['MgO']], sol: [2, 1, 2],
    hint: 'O₂ is a pair; MgO has one O each. Make MgO = 2.' },
  { name: 'Zinc + HCl', chem: ['Zn + 2HCl → ZnCl₂ + H₂'],
    sides: [['Zn', 'HCl'], ['ZnCl₂', 'H₂']], sol: [1, 2, 1, 1],
    hint: 'ZnCl₂ needs 2 chlorines → HCl needs coefficient 2.' },
  { name: 'Methane burn', chem: ['CH₄ + 2O₂ → CO₂ + 2H₂O'],
    sides: [['CH₄', 'O₂'], ['CO₂', 'H₂O']], sol: [1, 2, 1, 2],
    hint: '4 hydrogens in CH₄ → water must be 2.' },
  { name: 'Photosynthesis', chem: ['6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂'],
    sides: [['CO₂', 'H₂O'], ['C₆H₁₂O₆', 'O₂']], sol: [6, 6, 1, 6],
    hint: 'Glucose has 6 carbons → CO₂ must be 6. Then hydrogens force water = 6.' },
  { name: 'Aluminium + HCl', chem: ['2Al + 6HCl → 2AlCl₃ + 3H₂'],
    sides: [['Al', 'HCl'], ['AlCl₃', 'H₂']], sol: [2, 6, 2, 3],
    hint: 'AlCl₃ has 3 Cl — the LCM with HCl is 6.' },
  { name: 'Barium chloride', chem: ['BaCl₂ + Na₂SO₄ → BaSO₄ + 2NaCl'],
    sides: [['BaCl₂', 'Na₂SO₄'], ['BaSO₄', 'NaCl']], sol: [1, 1, 1, 2],
    hint: 'Na comes in pairs on the left → NaCl must be 2.' }
];

var s = { rx: 0, coefs: [], done: 0, streak: 0 };

function parseFormula(f) {
  // convert unicode subscripts (₂ etc.) to ASCII digits before counting atoms
  f = f.replace(/[₀-₉]/g, function (ch) {
    return String.fromCharCode(ch.charCodeAt(0) - 0x2080 + 48);
  });
  // returns {element: count}
  var counts = {};
  var m = f.match(/([A-Z][a-z]?)(\d*)/g).filter(Boolean);
  m.forEach(function (tok) {
    var mm = tok.match(/^([A-Z][a-z]?)(\d*)$/);
    if (!mm) return;
    counts[mm[1]] = (counts[mm[1]] || 0) + (mm[2] ? parseInt(mm[2]) : 1);
  });
  return counts;
}
function sub(f) { return f.replace(/(\d+)/g, '<sub>$1</sub>'); }

function render() {
  var rx = REACTIONS[s.rx];
  var html = '';
  var idx = 0;
  [0, 1].forEach(function (side) {
    rx.sides[side].forEach(function (f, i2) {
      if (side === 1 && i2 === 0) html += ' <span class="arrow">→</span> ';
      else if (!(side === 0 && i2 === 0)) html += '<span class="op">+</span> ';
      var c = s.coefs[idx];
      html += '<span class="grp"><span class="coef' + (c === 1 ? '' : '') + '" data-i="' + idx + '" title="click to increase, right-click to decrease">' +
              (c === 1 ? '1' : c) + '</span>' + sub(f) + '</span>';
      idx++;
    });
  });
  document.getElementById('eqBox').innerHTML = html;
  document.querySelectorAll('.coef').forEach(function (el) {
    el.addEventListener('click', function () { bump(+el.getAttribute('data-i'), +1); });
    el.addEventListener('contextmenu', function (e) {
      e.preventDefault();
      bump(+el.getAttribute('data-i'), -1);
    });
  });
  renderBalance();
}

function renderBalance() {
  var rx = REACTIONS[s.rx];
  var totals = [{}, {}];
  var idx = 0;
  [0, 1].forEach(function (side) {
    rx.sides[side].forEach(function (f) {
      var counts = parseFormula(f);
      Object.keys(counts).forEach(function (el) {
        totals[side][el] = (totals[side][el] || 0) + counts[el] * s.coefs[idx];
      });
      idx++;
    });
  });
  var elements = [];
  Object.keys(totals[0]).concat(Object.keys(totals[1])).forEach(function (e) {
    if (elements.indexOf(e) < 0 && (totals[0][e] || totals[1][e])) elements.push(e);
  });
  var allOk = true;
  var rows = '<tr><th>Element</th><th>Left</th><th>Right</th><th></th></tr>';
  elements.forEach(function (el) {
    var L = totals[0][el] || 0, R = totals[1][el] || 0;
    var ok = L === R;
    if (!ok) allOk = false;
    rows += '<tr><td><b>' + el + '</b></td><td>' + L + '</td><td>' + R + '</td>' +
            '<td class="' + (ok ? 'okTick' : 'badX') + '">' + (ok ? '✓' : '✗') + '</td></tr>';
  });
  document.getElementById('balTable').innerHTML = rows;
  var msg = document.getElementById('msg');
  if (allOk) {
    // verify against standard solution (any valid multiple also fine; require smallest form)
    var isSol = s.coefs.every(function (c, i) { return c === rx.sol[i]; });
    var reduced = s.coefs.every(function (c) { return c % s.coefs[0] === 0; }) && s.coefs[0] > 1;
    if (isSol) {
      msg.innerHTML = '<b style="color:var(--ok);">Balanced! 🎉 Law of conservation of mass satisfied.</b>';
      s.done++; s.streak++;
      updateScore();
      setTimeout(nextRx, 1400);
    } else {
      msg.innerHTML = 'Balanced — but not in <b>simplest whole-number form</b>. Divide all coefficients by a common factor.';
    }
  } else {
    msg.innerHTML = 'Not yet — keep matching atoms. <b>' + elements.length + '</b> element(s) to satisfy.';
    s.streak = 0;
    updateScore();
  }
}

function bump(i, dir) {
  s.coefs[i] = LK.clamp(s.coefs[i] + dir, 1, 12);
  render();
}
function nextRx() {
  s.rx = (s.rx + 1) % REACTIONS.length;
  start();
}
function start() {
  s.coefs = REACTIONS[s.rx].sides[0].concat(REACTIONS[s.rx].sides[1]).map(function () { return 1; });
  document.querySelectorAll('#rxSeg button').forEach(function (b, i) {
    b.classList.toggle('active', i === s.rx);
  });
  render();
}
function updateScore() {
  document.getElementById('score').innerHTML = 'Reactions balanced: <b>' + s.done + '</b>';
  document.getElementById('streak').innerHTML = 'Streak: <b>' + s.streak + '</b> 🔥';
}

document.getElementById('rxSeg').innerHTML = REACTIONS.map(function (r, i) {
  return '<button data-r="' + i + '">' + r.name + '</button>';
}).join('');
document.querySelectorAll('#rxSeg button').forEach(function (b) {
  b.addEventListener('click', function () {
    s.rx = +b.getAttribute('data-r');
    start();
  });
});
LK.button('hintBtn', function () {
  document.getElementById('msg').innerHTML = '💡 ' + REACTIONS[s.rx].hint;
});
LK.button('resetBtn', start);

start();
updateScore();
