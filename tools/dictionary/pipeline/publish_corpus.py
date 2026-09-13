#!/usr/bin/env python3
"""Split the 151-record restoration checkpoint at the edition boundary."""
import argparse
from pathlib import Path

from jsonio import read, write


def collect_notebook_collation(path):
    """Group the notebook-collation corrections by (story_id, line)."""
    if path is None:
        return {}
    grouped = {}
    for item in read(path)['corrections']:
        target = item['target']
        if target.get('source') != 'corpus':
            continue
        grouped.setdefault((target['story_id'], target['line']), []).append(item)
    return grouped


def apply_notebook_collation(story, grouped):
    """Apply the notebook-collation stage to one story, in place.

    This runs after the v2 annotation, so a line corrected here keeps the v2
    record of what that stage did and gains the later correction beside it. Each
    field it changes is recorded in `documentary_original_fields` under the value
    it replaced, which for the reverted lines restores the documentary reading
    the v2 orientation repair had departed from.
    """
    if not grouped:
        return
    for line in story['lines']:
        items = grouped.get((story['story_id'], line['line']), [])
        for item in items:
            field = item['target']['field']
            if line.get(field) not in (item['original_value'], item['revised_value']):
                raise SystemExit('notebook collation %s: unexpected current value'
                                 % item['correction_id'])
            originals = line.setdefault('documentary_original_fields', {})
            originals.setdefault(field, item['original_value'])
            line[field] = item['revised_value']
            ids = line.setdefault('transformation_ids', [])
            if item['correction_id'] not in ids:
                ids.append(item['correction_id'])
            if field == 'english':
                line['english_original'] = originals[field]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--working-corpus', type=Path, required=True)
    parser.add_argument('--classification', type=Path, required=True)
    parser.add_argument('--v2-receipt', type=Path, required=True)
    parser.add_argument('--notebook-collation', type=Path, default=None,
                        help='later corrections evidenced by the Jacobs field '
                             'notebooks, applied after the v2 annotation')
    parser.add_argument('--public-output', type=Path, required=True)
    parser.add_argument('--outside-output', type=Path, required=True)
    parser.add_argument('--containers-output', type=Path, required=True)
    args = parser.parse_args()
    corpus = read(args.working_corpus)
    notebook = collect_notebook_collation(args.notebook_collation)
    classes = {r['story_id']: r for r in read(args.classification)['records']}
    transformations = {}
    for item in read(args.v2_receipt)['corrections']:
        target = item['target']
        if target.get('source') != 'corpus':
            continue
        key = (target['story_id'], target['line'])
        transformations.setdefault(key, []).append(item)

    public, outside, containers = [], [], []
    for story in corpus['stories']:
        classification = classes[story['story_id']]
        story['source'] = {
            'layer': classification['source_layer'],
            'edition_included': classification['edition_included'],
            'basis': classification['reason'],
        }
        for line in story['lines']:
            items = transformations.get((story['story_id'], line['line']), [])
            if not items:
                continue
            line['documentary_original_fields'] = {
                item['target']['field']: item['original_value'] for item in items
            }
            line['transformation_ids'] = [item['correction_id'] for item in items]
            english = next((item for item in items if item['target']['field'] == 'english'), None)
            if english:
                line['english_original'] = english['original_value']
        apply_notebook_collation(story, notebook)
        layer = classification['source_layer']
        if layer == 'uwpa-recovered-record':
            public.append(story)
        elif layer == 'outside-edition-slip-file':
            outside.append(story)
        else:
            containers.append(story)

    def package(schema, stories):
        return {'schema': schema, 'story_count': len(stories),
                'line_count': sum(len(s['lines']) for s in stories), 'stories': stories}
    write(args.public_output, package('miluk-corpus/2', public))
    write(args.outside_output, package('miluk-outside-edition-corpus/1', outside))
    write(args.containers_output, package('miluk-working-containers/1', containers))
    print('public', len(public), sum(len(s['lines']) for s in public))
    print('outside', len(outside), sum(len(s['lines']) for s in outside))
    print('containers', len(containers), sum(len(s['lines']) for s in containers))


if __name__ == '__main__':
    main()
