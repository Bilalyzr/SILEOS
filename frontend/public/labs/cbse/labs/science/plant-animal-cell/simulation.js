'use strict';
var ORG = {
  cellwall:   { name: 'Cell wall', fn: 'A rigid outer box of cellulose that protects the cell and gives it a fixed shape.', where: 'Plant cells only' },
  membrane:   { name: 'Cell membrane', fn: 'The thin, selectively-permeable boundary — it decides what enters and leaves the cell.', where: 'All cells' },
  cytoplasm:  { name: 'Cytoplasm', fn: 'The jelly-like fluid filling the cell where all the organelles float and chemical reactions happen.', where: 'All cells' },
  nucleus:    { name: 'Nucleus', fn: 'The control room of the cell — it stores DNA and directs all activities like growth and reproduction.', where: 'All eukaryotic cells' },
  nucleolus:  { name: 'Nucleolus', fn: 'A dense spot inside the nucleus where ribosomes are manufactured.', where: 'All eukaryotic cells' },
  vacuole:    { name: 'Vacuole', fn: 'A storage sac for water, food and waste. In plants one huge vacuole keeps the cell firm and upright.', where: 'All cells; huge in plants, tiny in animals' },
  chloroplast:{ name: 'Chloroplasts', fn: 'The green kitchens of the cell — chlorophyll here captures sunlight to make food by photosynthesis.', where: 'Plant cells (and algae) only' },
  mitochondria:{ name: 'Mitochondria', fn: 'The powerhouses — they release energy from food by aerobic respiration (as ATP).', where: 'All eukaryotic cells' },
  er:         { name: 'Endoplasmic reticulum (ER)', fn: 'A network of tubes that transports materials and makes proteins (rough ER) and fats (smooth ER).', where: 'All eukaryotic cells' },
  golgi:      { name: 'Golgi apparatus', fn: 'The packing &amp; dispatch department — it modifies, packages and ships proteins made by the ER.', where: 'All eukaryotic cells' },
  ribosome:   { name: 'Ribosomes', fn: 'Tiny factories that build proteins by reading the DNA\u2019s instructions.', where: 'All cells' },
  lysosome:   { name: 'Lysosomes', fn: 'Suicide bags — sacs of digestive enzymes that clean up waste and worn-out organelles.', where: 'Mainly animal cells' },
  centriole:  { name: 'Centrioles', fn: 'Barrel-shaped structures that help pull chromosomes apart when the cell divides.', where: 'Animal cells only' }
};

var current = { type: 'plant', org: null };

function wire(rootId) {
  document.querySelectorAll('#' + rootId + ' .org').forEach(function (el) {
    el.addEventListener('click', function () { select(el.getAttribute('data-org')); });
  });
}
wire('plantSvg'); wire('animalSvg');

function select(orgId) {
  current.org = orgId;
  document.querySelectorAll('.org').forEach(function (el) {
    el.classList.toggle('sel', el.getAttribute('data-org') === orgId);
  });
  var d = ORG[orgId];
  if (!d) return;
  document.getElementById('infoCard').innerHTML =
    '<div style="font-weight:800;font-size:16px;margin-bottom:4px;">' + d.name + '</div>' +
    '<p class="lk-hint">' + d.fn + '</p>' +
    '<div class="lk-readout">Found in: <b>' + d.where + '</b></div>';
  renderChips();
}

function orgsForMode() {
  var ids = Object.keys(ORG);
  if (current.type === 'plant') return ids.filter(function (i) { return i !== 'lysosome' && i !== 'centriole'; });
  return ids.filter(function (i) { return i !== 'chloroplast' && i !== 'cellwall'; });
}

function renderChips() {
  document.getElementById('chipBox').innerHTML = orgsForMode().map(function (id) {
    return '<span class="chip" data-org="' + id + '">' + ORG[id].name + '</span>';
  }).join('');
  document.querySelectorAll('#chipBox .chip').forEach(function (ch) {
    ch.addEventListener('click', function () { select(ch.getAttribute('data-org')); });
  });
}

LK.segment('modeSeg', function (i) {
  current.type = i === 0 ? 'plant' : 'animal';
  document.getElementById('plantSvg').classList.toggle('hidden', current.type !== 'plant');
  document.getElementById('animalSvg').classList.toggle('hidden', current.type !== 'animal');
  select(current.org && orgsForMode().indexOf(current.org) >= 0 ? current.org : null);
  if (!current.org) {
    document.getElementById('infoCard').innerHTML = '<p class="lk-hint">Click any part of the cell (or a chip below) to learn what it does.</p>';
    document.querySelectorAll('.org').forEach(function (el) { el.classList.remove('sel'); });
  }
});

renderChips();
