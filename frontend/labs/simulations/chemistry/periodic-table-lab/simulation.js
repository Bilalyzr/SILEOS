'use strict';
window.__lkErrors = [];
window.addEventListener('error', function (e) { window.__lkErrors.push(String(e.message)); });

/* z, symbol, name, group-class, period, group, fact */
var E = [
[1,'H','Hydrogen','g-nonmetal',1,1,'Lightest element; fuel of the Sun'],
[2,'He','Helium','g-noble',1,18,'Balloons; never reacts'],
[3,'Li','Lithium','g-alkali',2,1,'Powers your phone battery'],
[4,'Be','Beryllium','g-alkaline',2,2,'Used in X-ray windows'],
[5,'B','Boron','g-metalloid',2,13,'In borosilicate glass'],
[6,'C','Carbon','g-nonmetal',2,14,'Backbone of ALL life'],
[7,'N','Nitrogen','g-nonmetal',2,15,'78% of air you breathe'],
[8,'O','Oxygen','g-nonmetal',2,16,'We breathe it; iron rusts with it'],
[9,'F','Fluorine','g-halogen',2,17,'Most reactive element'],
[10,'Ne','Neon','g-noble',2,18,'Glows orange-red in signs'],
[11,'Na','Sodium','g-alkali',3,1,'Fizzes violently in water'],
[12,'Mg','Magnesium','g-alkaline',3,2,'Burns blinding white'],
[13,'Al','Aluminium','g-postt',3,13,'Foil, cans, aircraft'],
[14,'Si','Silicon','g-metalloid',3,14,'Every computer chip'],
[15,'P','Phosphorus','g-nonmetal',3,15,'Match heads; DNA backbone'],
[16,'S','Sulphur','g-nonmetal',3,16,'Yellow powder; vulcanises rubber'],
[17,'Cl','Chlorine','g-halogen',3,17,'Keeps pools clean'],
[18,'Ar','Argon','g-noble',3,18,'Fills light bulbs'],
[19,'K','Potassium','g-alkali',4,1,'Bananas; fires on water'],
[20,'Ca','Calcium','g-alkaline',4,2,'Bones and teeth'],
[26,'Fe','Iron','g-trans',4,8,'Haemoglobin; most-used metal'],
[29,'Cu','Copper','g-trans',4,11,'Wires; great conductor'],
[30,'Zn','Zinc','g-trans',4,12,'Galvanises iron against rust'],
[35,'Br','Bromine','g-halogen',4,17,'Only liquid non-metal'],
[47,'Ag','Silver','g-trans',5,11,'Best conductor; mirrors'],
[53,'I','Iodine','g-halogen',5,17,'Thyroid health; purple vapour'],
[56,'Ba','Barium','g-alkaline',6,2,'Green fireworks'],
[78,'Pt','Platinum','g-trans',6,10,'Catalytic converters'],
[79,'Au','Gold','g-trans',6,11,'Never tarnishes'],
[80,'Hg','Mercury','g-trans',6,12,'Only liquid metal'],
[82,'Pb','Lead','g-postt',6,14,'Dense; blocks radiation'],
[88,'Ra','Radium','g-alkaline',7,2,'Marie Curie\u2019s element'],
[92,'U','Uranium','g-act',7,3,'Nuclear fuel']
];

var LEGEND = [['g-alkali','Alkali'],['g-alkaline','Alkaline earth'],['g-trans','Transition'],['g-postt','Post-transition'],
  ['g-metalloid','Metalloid'],['g-nonmetal','Non-metal'],['g-halogen','Halogen'],['g-noble','Noble gas'],['g-act','Actinide']];
document.getElementById('legend').innerHTML = LEGEND.map(function (L) {
  return '<span style="margin-right:12px;font:500 11.5px Inter,sans-serif;color:#3d4a63;"><span class="chip ' + L[0] + '"></span>' + L[1] + '</span>';
}).join('');

var colorMode = 0;
var selected = 11;

function cellStyle(el) {
  if (colorMode === 1) {
    // radius trend: decreases across period, increases down group
    var rad = LK.clamp(1 - (el[4] - 1) * 0.08 - (el[5] / 18) * 0.6, 0.12, 1);
    return 'background:hsl(' + Math.round(210 - rad * 190) + ',72%,' + (38 + rad * 18) + '%)';
  }
  if (colorMode === 2) {
    // reactivity: strong for group1, halogens; noble = off
    var react = (el[5] === 1 || el[5] === 17) ? 1 : el[6] === 'g-noble' ? 0 : (el[5] <= 2 ? 0.1 : 0.4);
    return 'background:hsl(' + Math.round(140 - react * 140) + ',75%,' + (42) + '%)';
  }
  return 'class="' + el[3] + '"';
}

function render() {
  var html = '';
  var placed = {};
  E.forEach(function (el) { placed[el[4] + '-' + el[5]] = el; });
  for (var per = 1; per <= 7; per++) {
    html += '<tr>';
    for (var grp = 1; grp <= 18; grp++) {
      var el = placed[per + '-' + grp];
      if (el) {
        html += '<td ' + cellStyle(el) + (el[0] === selected ? ' class="sel ' + el[3] + '"' : '') +
          ' data-z="' + el[0] + '"><span class="z">' + el[0] + '</span>' + el[1] + '</td>';
      } else if (per === 1 && grp === 1 || per === 2 && grp <= 2 || per === 3 && grp <= 2 ||
                 per >= 4 && grp >= 3 && grp <= 12 && !(per === 4 && grp === 8) && !(per === 4 && grp === 11) &&
                 !(per === 4 && grp === 12) && !(per === 5 && grp === 11) && !(per === 6 && grp === 10) &&
                 !(per === 6 && grp === 11) && !(per === 6 && grp === 12) && !(per === 7 && grp === 3)) {
        html += '<td class="blank"></td>';
      } else if (!(per === 6 && grp === 3) && !(per === 7 && grp === 3) && !(per === 7 && grp === 4)) {
        html += '<td class="blank"></td>';
      } else {
        html += '<td class="blank"></td>';
      }
    }
    html += '</tr>';
  }
  document.getElementById('pt').innerHTML = html;
  document.querySelectorAll('#pt td[data-z]').forEach(function (td) {
    td.addEventListener('click', function () { select(+td.getAttribute('data-z')); });
  });
  // lanthanide/actinide note
}

function select(z) {
  selected = z;
  var el = E.filter(function (e2) { return e2[0] === z; })[0];
  if (!el) return;
  var groupName = LEGEND.filter(function (L) { return L[0] === el[3]; })[0];
  document.getElementById('eName').textContent = el[2] + ' (' + el[1] + ')';
  document.getElementById('eData').innerHTML =
    'Atomic number: <b>' + el[0] + '</b> · Period ' + el[4] + ', Group ' + el[5] + '<br>Family: <b>' + (groupName ? groupName[1] : '—') + '</b>';
  document.getElementById('eFact').innerHTML = '💡 ' + el[6];
  render();
}

LK.segment('modeSeg', function (i) { colorMode = i; render(); });
render();
select(11);
