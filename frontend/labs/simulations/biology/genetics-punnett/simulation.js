'use strict';
var s = { p1: 'Pp', p2: 'Pp' };

function gametes(g) {
  if (g === 'PP') return ['P', 'P'];
  if (g === 'pp') return ['p', 'p'];
  return ['P', 'p'];
}

function draw() {
  var g1 = gametes(s.p1), g2 = gametes(s.p2);
  var cells = [];
  var html = '<table class="punnett"><tr><th></th>';
  g2.forEach(function (a) { html += '<th>' + a + '</th>'; });
  html += '</tr>';
  g1.forEach(function (a) {
    html += '<tr><th>' + a + '</th>';
    g2.forEach(function (b) {
      var gt = [a, b].sort().reverse().join('');   // capital first
      cells.push(gt);
      html += '<td class="' + gt + '">' + gt + '</td>';
    });
    html += '</tr>';
  });
  html += '</table>';
  document.getElementById('punnettBox').innerHTML = html;

  var counts = { PP: 0, Pp: 0, pp: 0 };
  cells.forEach(function (c) { counts[c]++; });
  var purple = counts.PP + counts.Pp, white = counts.pp;
  document.getElementById('genoR').innerHTML =
    'Genotype ratio: <b>' + counts.PP + ' PP : ' + counts.Pp + ' Pp : ' + counts.pp + ' pp</b>';
  document.getElementById('phenoR').innerHTML =
    'Phenotype ratio: <b>' + purple + ' purple : ' + white + ' white</b>';
  document.getElementById('phenoBar').innerHTML =
    '<div style="background:#7c3aed;width:' + (purple * 25) + '%">' + (purple * 25) + '%</div>' +
    '<div style="background:#cbd5e1;color:#334155;width:' + (white * 25) + '%">' + (white * 25) + '%</div>';
}

function breed(n) {
  var g1 = gametes(s.p1), g2 = gametes(s.p2);
  var purple = 0, geno = { PP: 0, Pp: 0, pp: 0 };
  for (var i = 0; i < n; i++) {
    var gt = [g1[Math.floor(Math.random() * 2)], g2[Math.floor(Math.random() * 2)]].sort().reverse().join('');
    geno[gt]++;
    if (gt !== 'pp') purple++;
  }
  document.getElementById('randomRes').innerHTML =
    'From ' + n + ' offspring: <b>' + purple + ' purple : ' + (n - purple) + ' white</b>' +
    ' (genotypes: ' + geno.PP + ' PP, ' + geno.Pp + ' Pp, ' + geno.pp + ' pp)';
}

function wireSeg(id, key) {
  var box = document.getElementById(id);
  var btns = [].slice.call(box.querySelectorAll('button'));
  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      btns.forEach(function (b2) { b2.classList.remove('active'); });
      b.classList.add('active');
      s[key] = b.getAttribute('data-g');
      draw();
    });
  });
}
wireSeg('p1Seg', 'p1'); wireSeg('p2Seg', 'p2');
LK.button('flipBtn', function () { breed(100); });

draw();
