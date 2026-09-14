"""Rebuild the reviewed chapter activities and downloadable, importable starter packs.

Run from backend: python scripts/build_concept_extensions.py
No expressions or code from the source data are executed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    definitions = {}
    for line in (ROOT / 'seed_packs/concept_investigations.psv').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        ids, rule, group_a, examples_a, group_b, examples_b = line.split('|')
        cards = []
        for group, examples in ((group_a, examples_a), (group_b, examples_b)):
            label, explanation = group.split('~')
            cards.extend({'label': example.strip(), 'group': label, 'explanation': explanation} for example in examples.split(';'))
        for chapter_id in ids.split(','):
            if chapter_id in definitions:
                raise ValueError(f'Duplicate chapter: {chapter_id}')
            definitions[chapter_id] = (rule, cards)
    chapters = json.loads((ROOT / 'seed_packs/cbse_curriculum.json').read_text(encoding='utf-8'))
    activities = []
    for chapter in chapters:
        if chapter['lab_slug']:
            continue
        rule, cards = definitions[chapter['id']]
        activities.append({'title': chapter['title'] + ' — concept investigation', 'subject': chapter['subject'], 'description': rule,
            'config': {'engine': 'classification', 'objective': rule,
                'prediction': 'Predict the group for each example before checking. Which feature determines your choice?',
                'investigation': ['Read the grouping rule and compare the examples.', 'Assign each example to a group, then check your classification.', 'Explain one corrected decision and propose a new example for each group.'],
                'explanation': 'This focused classification activity explores one distinction in the chapter. It does not replace the complete chapter or a physical experiment. ' + rule,
                'chapter_ids': [chapter['id']], 'cards': cards}})
    (ROOT / 'seed_packs/cbse_concept_extensions.json').write_text(json.dumps(activities, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    destination = ROOT.parent / 'frontend/public/labs/packs'
    destination.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(activities), 30):
        pack = {'format': 'sasha-concept-labs', 'version': 1, 'labs': activities[start:start+30]}
        (destination / f'cbse-concepts-{start//30+1}.sasha-labs.json').write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Built {len(activities)} chapter investigations and {(len(activities)+29)//30} starter packs.')


if __name__ == '__main__':
    build()
