#!/usr/bin/env python3
"""Normalize display forms while preserving every 1990 ASCII documentary value."""
import argparse
import re
import unicodedata
from pathlib import Path

from anderson import convert
from jsonio import read, write

SUPERSCRIPT_FLAT = str.maketrans('ⁱᵘʷᵃᵉⁿʸʰ', 'iuwaenyh')
FOLD = str.maketrans({'ɛ': 'e', 'ə': 'e', 'ɢ': 'g', 'ƚ': 'l', 'ł': 'l', 'ɣ': 'g',
                      'ʒ': 'z', 'ʃ': 's', 'š': 's', 'ǯ': 'j', 'ŋ': 'n', 'ɪ': 'i',
                      'ʊ': 'u', 'ð': 'd', 'ɴ': 'n', 'ʟ': 'l', 'ᴍ': 'm', 'ʻ': ''})


def searchkey(value):
    value = unicodedata.normalize('NFC', value.translate(SUPERSCRIPT_FLAT))
    value = ''.join(ch for ch in unicodedata.normalize('NFD', value)
                    if not unicodedata.combining(ch))
    value = value.replace('ƛ', 'tl').translate(FOLD)
    return re.sub(r'[·‿ʼʰ]', '', value).lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--lexicon', type=Path, required=True,
                        help='recovered exact ASCII-to-corpus-display map (not found in the archive)')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repair-log', type=Path, required=True)
    args = parser.parse_args()
    records = read(args.input)
    lexicon = read(args.lexicon)
    repairs = []
    for record in records:
        record['headword_modern'] = convert(record['headword'].lower())
        for group in record['groups']:
            normalized = []
            for form in group['forms']:
                source = 'corpus' if form in lexicon else 'converted'
                display = lexicon.get(form)
                if display is None:
                    for index, char in enumerate(form):
                        candidate = form[:index] + ':' + form[index + 1:] if char == '-' else None
                        if candidate in lexicon:
                            display = lexicon[candidate]
                            source = 'repaired'
                            repairs.append({'headword': record['headword'], 'form': form,
                                            'correction': "'-' to ':'", 'position': index,
                                            'result': display})
                            break
                display = unicodedata.normalize('NFC', display if display is not None else convert(form))
                normalized.append({'ascii': form, 'display': display,
                                   'search': searchkey(display), 'src': source})
            group['entries'] = normalized
        for example in record.get('examples', []):
            example['miluk_modern'] = ' '.join(convert(token) for token in example['miluk'].split())
    write(args.output, records)
    write(args.repair_log, repairs)
    print(f'normalized {len(records)} source records; {len(repairs)} logged repairs')


if __name__ == '__main__':
    main()
