#!/usr/bin/env python3
"""Tag converted forms only against explicitly included UWPA corpus records."""
import argparse
import re
from pathlib import Path

from anderson import convert, normalize_target
from jsonio import read, write
from normalize_dictionary import searchkey


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dictionary', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--unverified-output', type=Path, required=True)
    args = parser.parse_args()
    corpus = read(args.corpus)
    stories = [story for story in corpus['stories']
               if story.get('source', {}).get('layer') == 'uwpa-recovered-record']
    keys = set()
    for story in stories:
        for line in story['lines']:
            for token in re.split(r'\s+', line['miluk_ascii']):
                token = token.strip('.,;()[]"')
                for piece in token.split('-'):
                    if piece:
                        keys.add(searchkey(convert(piece)))
                keys.add(searchkey(convert(token.replace('-', ''))))
    keys.discard('')
    records = read(args.dictionary)
    unverified = []
    for record in records:
        for group in record['groups']:
            for entry in group['entries']:
                if entry['src'] == 'corpus':
                    entry['display'] = normalize_target(entry['display'])
                    entry['search'] = searchkey(entry['display'])
                    continue
                key = entry['search']
                if key in keys or any(key in candidate for candidate in keys if len(candidate) > len(key)):
                    entry['src'] = 'corroborated'
                else:
                    entry['src'] = 'unverified'
                    unverified.append({'headword': record['headword'], 'ascii': entry['ascii'],
                                       'display': entry['display'], 'gloss': record['gloss']})
    write(args.output, records)
    write(args.unverified_output, unverified)
    print(f'verified against {len(stories)} UWPA records; {len(unverified)} forms unresolved')


if __name__ == '__main__':
    main()
