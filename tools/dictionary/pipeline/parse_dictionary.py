#!/usr/bin/env python3
"""Parse converted 1990 entry text into structured, documentary records."""
import argparse
import re
from pathlib import Path

from jsonio import write

CITE = re.compile(r':\s*\d')
XREF = re.compile(r'^\(?\s*see\s+ref(?:erence)?\.?\s*(?:for|under|to)?\s*(.*)$', re.I)
LEAK = re.compile(r'(Computer\s*Book|Reference\s*List)\s*:', re.I)
EXAMPLE = re.compile(r'^\|p(\d+)\s*(.*)$')
ANDERSON = re.compile(r'[<@#!;%$&]|:')


def classify(line):
    value = line.strip().strip('()')
    if not value or LEAK.search(value):
        return None, None
    if re.fullmatch(r'[\d,;.\s]+', value) or (value.startswith(',') and re.search(r'\d', value)):
        return 'cite', value
    match = XREF.search(line.strip())
    if match:
        return 'xref', match.group(1).strip()
    if CITE.search(value):
        return 'cite', value
    return 'gloss', value


def is_miluk(value):
    return bool(ANDERSON.search(value)) or (
        len(value.split()) <= 6 and not re.search(
            r'\b(the|a|he|she|it|was|were|that|there|not|and|his|her|they)\b', value, re.I))


def parse_file(path):
    raw = path.read_text(encoding='utf-8-sig')
    lines = raw.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    top = ''
    if i < len(lines) and not lines[i].lstrip().startswith(('Computer Book:', 'Reference List:')):
        kind, value = classify(lines[i])
        if kind == 'gloss':
            top = value
            i += 1
    groups = []
    current = None
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith('Computer Book:'):
            if current:
                groups.append(current)
            current = {'book': stripped.split(':', 1)[1].strip(), 'forms': [],
                       'gloss': '', 'xrefs': [], 'cites': []}
        elif stripped.startswith('Reference List:'):
            buffer = stripped.split(':', 1)[1].strip()
            j = i + 1
            while j < len(lines) and lines[j].startswith('                '):
                buffer += lines[j].strip()
                j += 1
            i = j - 1
            if current is not None:
                current['forms'] = [v for v in re.split(r'[,\s]+', buffer) if v]
        elif line.strip() and current is not None:
            kind, value = classify(line)
            if kind == 'cite':
                current['cites'].append(value)
            elif kind == 'xref':
                current['xrefs'].append(value)
            elif kind == 'gloss':
                current['gloss'] = (current['gloss'] + '; ' + value).strip('; ')
        i += 1
    if current:
        groups.append(current)

    examples = []
    if '|p' in raw:
        blocks = re.split(r'\n(?=\|p\d)', raw)
        for block in blocks[1:]:
            parts = [v.strip() for v in block.splitlines()]
            match = EXAMPLE.match(parts[0])
            first = match.group(2).strip() if match else ''
            line_number = match.group(1) if match else ''
            cite = ''
            texts = [first]
            for part in (v for v in parts[1:] if v):
                if re.match(r'^\(.*\)$', part) or CITE.search(part):
                    cite = part.strip('() ')
                else:
                    texts.append(part)
            miluk = [v for v in texts if v and is_miluk(v)]
            english = [v for v in texts if v and not is_miluk(v)]
            examples.append({'line': line_number, 'miluk': ' '.join(miluk),
                             'english': ' '.join(english), 'cite': cite})
        if '|p' in top:
            top = top.split('|p', 1)[0].strip()
        for group in groups:
            if '|p' in group['gloss']:
                group['gloss'] = ''
    return {'headword': path.stem, 'gloss': top, 'groups': groups, 'examples': examples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = [parse_file(path) for path in sorted(args.input.glob('*.txt'), key=lambda p: p.name.encode())]
    write(args.output, records)
    print(f'parsed {len(records)} source files into {args.output}')


if __name__ == '__main__':
    main()
