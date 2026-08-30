#!/usr/bin/env python3
"""Classify the 151 recovered export records without claiming title completeness."""
import argparse
from pathlib import Path

from jsonio import read, write

CONTAINERS = {2, 10, 26, 67, 113, 114, 149, 151}
SLIP_RECORDS = set(range(115, 149)) | {150}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    corpus = read(args.corpus)
    records = []
    for story in corpus['stories']:
        number = int(story['story_id'][1:4])
        if number in CONTAINERS:
            layer = 'working-container'
            edition = False
            reason = 'empty Word Cruncher section container; not a text'
        elif number in SLIP_RECORDS:
            layer = 'outside-edition-slip-file'
            edition = False
            reason = 'record occurs in the explicit Jacobs Slip Files source section'
        else:
            layer = 'uwpa-recovered-record'
            edition = True
            reason = ('record occurs in the recovered export numerical sections '
                      'assigned to the two Jacobs UWPA volumes')
        records.append({'story_id': story['story_id'], 'source_layer': layer,
                        'edition_included': edition, 'reason': reason})
    write(args.output, {
        'schema': 'miluk-source-classification/2',
        'classification_scope': 'recovered Word Cruncher export records',
        'publication_inventory': 'publication-inventory.json',
        'completeness_limit': (
            'Numerical-section classification establishes the recovered-export '
            'boundary; publication completeness requires the separate 111-title '
            'publication inventory.'
        ),
        'records': records,
    })
    counts = {}
    for record in records:
        counts[record['source_layer']] = counts.get(record['source_layer'], 0) + 1
    print(counts)


if __name__ == '__main__':
    main()
