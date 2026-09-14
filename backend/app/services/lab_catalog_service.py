"""Bundled lab catalog and curriculum editions, independent of authoring storage."""
import json
import re
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2] / 'seed_packs'

# Existing lessons/backups retain old identifiers. Resolve these to supplied
# simulations of the same concept without reintroducing retired catalog entries.
LEGACY_LAB_REPLACEMENTS = {
    'projectile-motion': 'cbse-projectile-motion',
    'cell-biology-identify': 'cbse-plant-animal-cell',
    'reaction-lab-basics': 'cbse-balance-equations',
    'neuron': 'cbse-neuron-reflex-lab',
}


def canonical_lab_slug(slug):
    return LEGACY_LAB_REPLACEMENTS.get(slug, slug)


def _read(name):
    return json.loads((PACK_ROOT / name).read_text(encoding='utf-8'))


CBSE_LABS = _read('cbse_labs.json')
LEGACY_CHAPTERS = _read('cbse_curriculum.json')
CURRENT_CHAPTERS = _read('cbse_curriculum_ncert_2024.json')
CONCEPT_EXTENSIONS = _read('cbse_concept_extensions.json')
CONCEPT_LABS = []
for chapter in LEGACY_CHAPTERS:
    chapter['edition'] = 'legacy'
legacy_by_id = {chapter['id']: chapter for chapter in LEGACY_CHAPTERS}
for entry in CONCEPT_EXTENSIONS:
    chapter_id = entry['config']['chapter_ids'][0]
    slug = 'concept-' + chapter_id
    chapter = legacy_by_id[chapter_id]
    CONCEPT_LABS.append(dict(entry, slug=slug, provider='native', native_template='concept_lab',
        embed_url=None, attribution='SashaInfinity · focused chapter investigation', spatial='panel',
        grades=[chapter['grade']], concepts=entry['config']['chapter_ids']))
    chapter.update(lab_slug=slug, activity_kind='classification')


def _chapter_key(chapter):
    title = re.sub(r'^\d+\.\s*', '', chapter['title']).casefold().strip()
    return chapter['grade'], chapter['subject'], title


# Only identical titles within the same class and subject inherit a previous activity.
# Position-based remapping would silently attach notebooks to different chapters.
legacy_by_title = {_chapter_key(c): c for c in LEGACY_CHAPTERS}
for chapter in CURRENT_CHAPTERS:
    previous = legacy_by_title.get(_chapter_key(chapter))
    if not chapter['lab_slug'] and previous and previous['lab_slug']:
        chapter['lab_slug'] = previous['lab_slug']
        chapter['alignment_source'] = 'matching-legacy-title'
        if previous.get('activity_kind'):
            chapter['activity_kind'] = previous['activity_kind']

CHAPTERS = CURRENT_CHAPTERS + LEGACY_CHAPTERS
# Never replace a chapter with an invented generic experiment. Chapters with
# no supplied activity remain explicitly unlinked until an author attaches one.
for chapter in CHAPTERS:
    if (chapter.get('lab_slug') or '').startswith('concept-'):
        chapter['lab_slug'] = None
        chapter.pop('activity_kind', None)
CHAPTER_IDS = frozenset(c['id'] for c in CHAPTERS)
EDITIONS = [{'id': 'ncert-2024', 'label': 'Updated curriculum · supplied NCERT 2024–25 map'},
            {'id': 'legacy', 'label': 'Earlier curriculum · saved activities'}]
