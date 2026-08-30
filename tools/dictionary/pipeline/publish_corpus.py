#!/usr/bin/env python3
"""Split the 151-record restoration checkpoint at the edition boundary."""
import argparse
from pathlib import Path

from jsonio import read, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--working-corpus', type=Path, required=True)
    parser.add_argument('--classification', type=Path, required=True)
    parser.add_argument('--v2-receipt', type=Path, required=True)
    parser.add_argument('--public-output', type=Path, required=True)
    parser.add_argument('--outside-output', type=Path, required=True)
    parser.add_argument('--containers-output', type=Path, required=True)
    args = parser.parse_args()
    corpus = read(args.working_corpus)
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
        layer = classification['source_layer']
        if layer == 'uwpa-published':
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
