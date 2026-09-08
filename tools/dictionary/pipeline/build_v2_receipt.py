#!/usr/bin/env python3
"""Create a field-level receipt for commit dc186a2's effective JSON changes."""
import argparse
from pathlib import Path

from jsonio import read, write


def indexed_stories(corpus):
    return {story['story_id']: story for story in corpus['stories']}


def indexed_lines(story):
    return {line['line']: line for line in story['lines']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-corpus', type=Path, required=True)
    parser.add_argument('--after-corpus', type=Path, required=True)
    parser.add_argument('--before-dictionary', type=Path, required=True)
    parser.add_argument('--after-dictionary', type=Path, required=True)
    parser.add_argument('--classification', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = read(args.before_corpus)
    after = read(args.after_corpus)
    classes = {r['story_id']: r for r in read(args.classification)['records']}
    bstories = indexed_stories(before)
    astories = indexed_stories(after)
    corrections = []
    changed_records = 0
    changed_stories = set()
    unswaps = set()
    for story_id, before_story in bstories.items():
        before_lines = indexed_lines(before_story)
        after_lines = indexed_lines(astories[story_id])
        for line_number, old_line in before_lines.items():
            new_line = after_lines[line_number]
            fields = [field for field in sorted(set(old_line) | set(new_line))
                      if old_line.get(field) != new_line.get(field)]
            if not fields:
                continue
            changed_records += 1
            changed_stories.add(story_id)
            is_unswap = {'english', 'miluk', 'miluk_ascii'}.issubset(fields)
            if is_unswap:
                unswaps.add((story_id, line_number))
            for field in fields:
                correction_id = f"v2-corpus-{story_id[:4]}-l{line_number:04d}-{field.replace('_', '-')}"
                kind = 'field-unswap' if is_unswap else 'english-presentation-conversion'
                corrections.append({
                    'correction_id': correction_id,
                    'target': {'source': 'corpus', 'story_id': story_id,
                               'line': line_number, 'field': field},
                    'original_value': old_line.get(field),
                    'revised_value': new_line.get(field),
                    'disposition': 'changed',
                    'reason': ('repair Miluk/English field orientation' if is_unswap else
                               'convert embedded Miluk token in an English translation to display notation'),
                    'verification_source': 'structured diff of dc186a2 against its first parent',
                    'affects': 'generated-presentation' if not is_unswap else 'restoration-corpus',
                    'restoration_stage': 'dictionary-v2',
                    'change_kind': kind,
                    'source_layer': classes[story_id]['source_layer'],
                })

    before_dictionary = {e['entry_id']: e for e in read(args.before_dictionary)['entries']}
    after_dictionary = {e['entry_id']: e for e in read(args.after_dictionary)['entries']}
    dictionary_corrections = []
    for entry_id, old_entry in before_dictionary.items():
        new_entry = after_dictionary[entry_id]
        for field in sorted(set(old_entry) | set(new_entry)):
            if old_entry.get(field) == new_entry.get(field):
                continue
            kind = 'gloss-cleanup' if field == 'gloss' else 'derived-attestation-verification'
            dictionary_corrections.append({
                'correction_id': f'v2-dictionary-{entry_id[:5]}-{field}',
                'target': {'source': 'dictionary', 'entry_id': entry_id, 'field': field},
                'original_value': old_entry.get(field),
                'revised_value': new_entry.get(field),
                'disposition': 'changed',
                'reason': ('remove concordance filename debris from the restored gloss' if field == 'gloss'
                           else 'recompute a derived verification flag after corpus field repair'),
                'verification_source': 'structured diff of dc186a2 against its first parent',
                'affects': '1990-dictionary' if field == 'gloss' else 'generated-presentation',
                'restoration_stage': 'dictionary-v2',
                'change_kind': kind,
            })
    unswap_layers = {}
    for story_id, _ in unswaps:
        layer = classes[story_id]['source_layer']
        unswap_layers[layer] = unswap_layers.get(layer, 0) + 1
    receipt = {
        'schema': 'miluk-v2-effective-diff/1',
        'commit': 'dc186a2b8cea67a1a4c08b33549c1302951d99f7',
        'summary': {
            'changed_corpus_records': changed_records,
            'changed_corpus_stories': len(changed_stories),
            'english_field_changes': sum(c['target'].get('field') == 'english' for c in corrections),
            'field_unswap_records': len(unswaps),
            'field_unswap_records_by_source_layer': unswap_layers,
            'changed_dictionary_entries': len({c['target']['entry_id'] for c in dictionary_corrections}),
            'gloss_cleanups': sum(c['change_kind'] == 'gloss-cleanup' for c in dictionary_corrections),
            'derived_attestation_verification_changes': sum(
                c['change_kind'] == 'derived-attestation-verification' for c in dictionary_corrections),
        },
        'corrections': corrections + dictionary_corrections,
    }
    write(args.output, receipt)
    print(receipt['summary'])


if __name__ == '__main__':
    main()
