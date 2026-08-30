#!/usr/bin/env python3
"""Parse the 1990 Word Cruncher plain-text export into a working corpus stage."""
import argparse
import re
from pathlib import Path

from anderson import convert
from jsonio import read, write

WORDLIST = re.compile(r'^~S?\d?_?(Swadesh|Jacobs_Dictionary|Jacobs_Numbers|Frachtenberg)', re.I)
ENGLISH_WORD = re.compile(r"^[A-Za-z@',.\-]+$")
ANDERSON = re.compile(r"[<@#;%$&]|[a-z]:[<a-z]")


def deat(value):
    return value.replace('@', 'e') if ENGLISH_WORD.match(value) else value


def clean(value):
    value = value.split('+')[0].replace('_', ' ').strip(' .,+')
    value = ' '.join(convert(word) if re.search(r'[<#%;!$&]|:', word) else deat(word)
                     for word in value.split())
    return re.sub(r'\s+', ' ', value)


def orient(left, right):
    left_score = len(ANDERSON.findall(left))
    right_score = len(ANDERSON.findall(right))
    return (left.strip(), right.strip()) if right_score >= left_score else (right.strip(), left.strip())


def slug(title, number):
    value = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:44] or 'untitled'
    return f't{number:03d}-{value}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--corrections', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    lines = args.input.read_bytes().decode('latin-1').replace('\r\n', '\n').replace('\r', '\n').split('\n')
    stories = []
    wordlists = {}
    current = None
    mode = 'story'
    wordlist = None
    for line in lines:
        if not line.startswith('~'):
            continue
        body = line[1:]
        if WORDLIST.match(line):
            mode = 'wordlist'
            wordlist = clean(body.lstrip('S0123456789_'))
            wordlists.setdefault(wordlist, [])
            current = None
            continue
        if re.match(r'^~[A-Za-z0-9]{0,2}_', line) or re.match(r'^~f\d', line):
            title = clean(re.sub(r'^[A-Za-z0-9]{0,2}_', '', body))
            if title:
                raw_title = re.sub(r'^[A-Za-z0-9]{0,2}_', '', body).split('+')[0]
                raw_title = raw_title.replace('_', ' ').strip(' .,+')
                current = {'title': title, 'raw_title': re.sub(r'\s+', ' ', raw_title), 'lines': []}
                stories.append(current)
                mode = 'story'
            continue
        if '+' in body and current is not None and mode == 'story':
            left, right = body.split('+', 1)
            english, miluk = orient(left, right)
            current['lines'].append({'n': len(current['lines']) + 1,
                                     'english': english, 'miluk': miluk})
        elif mode == 'wordlist' and body.strip():
            parts = body.strip().split(None, 1)
            if len(parts) == 2:
                wordlists[wordlist].append(parts)

    # Recovered, conservative source repairs.
    token_inventory = {piece for story in stories for line in story['lines']
                       for token in line['miluk'].split()
                       for piece in token.strip('.,;').split('-') if piece}
    for story in stories:
        for line in story['lines']:
            parts = []
            for token in line['miluk'].split():
                repaired = []
                for piece in token.split('-'):
                    core = piece.strip('.,;')
                    candidate = core.replace('1', 'l')
                    if '1' in core and candidate in token_inventory:
                        piece = piece.replace(core, candidate)
                    repaired.append(piece)
                parts.append('-'.join(repaired))
            line['miluk'] = ' '.join(parts)
            tokens = line['miluk'].split()
            joined = []
            i = 0
            while i < len(tokens):
                if (i + 1 < len(tokens) and tokens[i].rstrip('.,;').endswith('dj')
                        and tokens[i + 1].startswith('e-')):
                    joined.append(tokens[i] + tokens[i + 1])
                    i += 2
                else:
                    joined.append(tokens[i])
                    i += 1
            line['miluk'] = ' '.join(joined)
            if ANDERSON.search(line['english']):
                original = line['english']
                converted = []
                for token in original.split():
                    lead = token[:len(token) - len(token.lstrip('("\''))]
                    trail_count = len(token) - len(token.rstrip(')"\'.,!?;'))
                    core = token[len(lead):len(token) - trail_count if trail_count else len(token)]
                    trail = token[len(token) - trail_count:] if trail_count else ''
                    converted.append(lead + (convert(core) if ANDERSON.search(core) else core) + trail)
                line['english'] = ' '.join(converted)
                if line['english'] != original:
                    line['english_original'] = original

    by_id = {slug(story['title'], number): story for number, story in enumerate(stories, 1)}
    for correction in read(args.corrections):
        story = by_id.get(correction.get('story_id_full') or correction['story_id'])
        if story is None:
            continue
        number = correction.get('line_no') or int(re.match(r'\s*(\d+)', correction['line']).group(1))
        if 1 <= number <= len(story['lines']):
            line = story['lines'][number - 1]
            if correction['old'] in line['miluk']:
                line['miluk'] = line['miluk'].replace(correction['old'], correction['new'], 1)
    write(args.output, {'schema': 'miluk-working-corpus-stage/1',
                        'stories': stories, 'wordlists': wordlists})
    print(f'parsed {len(stories)} records / {sum(len(s["lines"]) for s in stories)} lines')


if __name__ == '__main__':
    main()
