#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build and provenance verification for the restored 1990 dictionary edition."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data', type=Path, default=REPO_ROOT / 'dictionary' / 'data')
parser.add_argument('--out', type=Path, default=REPO_ROOT / 'dictionary')
parser.add_argument('--skip-determinism', action='store_true')
parser.add_argument('--skip-git-diff', action='store_true',
                    help='development only; clean-clone acceptance must not use this')
args = parser.parse_args()
DATA = args.data.resolve()
OUT = args.out.resolve()
PROV = TOOL_DIR / 'provenance'
ARCHIVE = TOOL_DIR / 'archive' / 'outside-edition'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


C = load(DATA / 'corpus.json')
D = load(DATA / 'dictionary.json')
OUTSIDE = load(ARCHIVE / 'slip-file-records.json')
CONTAINERS = load(ARCHIVE / 'working-containers.json')
CLASSIFICATION = load(PROV / 'source-classification.json')
COLLATION = load(DATA / 'correction-ledger.json')
V2 = load(PROV / 'v2-effective-diff.json')
FIN_MANIFEST = load(PROV / 'fin-source-manifest.json')
fails = []


def check(condition, message):
    if not condition:
        fails.append(message)


def declared_counts(dataset, label):
    stories = dataset['stories']
    check(dataset['story_count'] == len(stories), f'{label}: declared story count')
    check(dataset['line_count'] == sum(len(s['lines']) for s in stories),
          f'{label}: declared line count')
    for story in stories:
        check(story['line_count'] == len(story['lines']),
              f"{label}: declared line count for {story['story_id']}")


# 1. Edition boundary and declared counts.
declared_counts(C, 'public corpus')
declared_counts(OUTSIDE, 'outside-edition corpus')
declared_counts(CONTAINERS, 'working containers')
check(C['story_count'] == 108, 'public corpus must contain 108 verified UWPA texts')
check(C['line_count'] == 7149, 'public corpus must contain 7,149 verified UWPA lines')
check(OUTSIDE['story_count'] == 35 and OUTSIDE['line_count'] == 574,
      'outside-edition archive must preserve 35 slip records / 574 lines')
check(CONTAINERS['story_count'] == 8 and CONTAINERS['line_count'] == 0,
      'working-container archive must preserve eight empty containers')
check(D['entry_count'] == len(D['entries']) == 1111, 'dictionary entry count')
for story in C['stories']:
    check(story['lines'], f"empty public story: {story['story_id']}")
    check(story.get('source', {}).get('layer') == 'uwpa-published',
          f"non-UWPA source layer in public corpus: {story['story_id']}")
    check(story.get('source', {}).get('edition_included') is True,
          f"public story not explicitly edition-included: {story['story_id']}")
for story in OUTSIDE['stories']:
    check(story.get('source', {}).get('layer') == 'outside-edition-slip-file',
          f"outside record lacks slip-file classification: {story['story_id']}")

classified = {r['story_id']: r for r in CLASSIFICATION['records']}
all_stories = C['stories'] + OUTSIDE['stories'] + CONTAINERS['stories']
check(len(classified) == 151, 'source classification must cover all 151 working records')
check(set(classified) == {s['story_id'] for s in all_stories},
      'source classification identities must match preserved working records')
fin_root = TOOL_DIR / 'archive' / '1990-fin'
check(FIN_MANIFEST['file_count'] == len(FIN_MANIFEST['files']) == 684,
      '1990 FIN manifest must contain 684 sources')
for record in FIN_MANIFEST['files']:
    source = fin_root / record['path']
    check(source.exists(), f"archival FIN source missing: {record['path']}")
    if source.exists():
        check(source.stat().st_size == record['size'], f"archival FIN size mismatch: {record['path']}")
        check(hashlib.sha256(source.read_bytes()).hexdigest() == record['sha256'],
              f"archival FIN hash mismatch: {record['path']}")

# 2. Unique identities and bidirectional data references.
entry_ids = [entry['entry_id'] for entry in D['entries']]
story_ids = [story['story_id'] for story in all_stories]
check(len(entry_ids) == len(set(entry_ids)), 'duplicate entry identity')
check(len(story_ids) == len(set(story_ids)), 'duplicate story identity')
entry_id_set = set(entry_ids)
line_by = {}
for story in C['stories'] + OUTSIDE['stories']:
    numbers = [line['line'] for line in story['lines']]
    check(len(numbers) == len(set(numbers)), f"duplicate line identity in {story['story_id']}")
    for line in story['lines']:
        key = (story['story_id'], line['line'])
        check(key not in line_by, f'duplicate global story/line identity: {key}')
        line_by[key] = line
        for entry_id in line.get('entries', []):
            check(entry_id in entry_id_set,
                  f"unknown corpus entry reference {entry_id} at {key}")

public_ids = {s['story_id'] for s in C['stories']}
outside_ids = {s['story_id'] for s in OUTSIDE['stories']}
for entry in D['entries']:
    for attestation in entry['attestations']:
        story_id = attestation.get('story_id')
        if not story_id:
            continue
        key = (story_id, attestation.get('line'))
        check(key in line_by, f"attestation target missing for {entry['entry_id']}: {key}")
        if story_id in outside_ids:
            check(story_id not in public_ids,
                  f"outside-edition citation leaked into public corpus: {story_id}")

# 3. Correction and transformation ledgers resolve and reverse every changed field.
check(COLLATION['source_record_count'] == len(COLLATION['corrections']) == 922,
      'complete 922-item collation ledger')
working_story_ids = [story['story_id'] for story in all_stories]
for item in COLLATION['corrections']:
    target = item['target']
    matches = [story_id for story_id in working_story_ids
               if story_id == target['story_id'] or story_id.startswith(target['story_id'] + '-')]
    check(len(matches) == 1, f"collation target story does not resolve: {item['correction_id']}")
    if len(matches) == 1:
        check((matches[0], target['line']) in line_by,
              f"collation target line does not resolve: {item['correction_id']}")
    check(item['disposition'] in {'changed', 'retained', 'unresolved', 'excluded'},
          f"invalid collation disposition: {item['correction_id']}")

v2_by_id = {item['correction_id']: item for item in V2['corrections']}
check(len(v2_by_id) == len(V2['corrections']), 'duplicate v2 correction identity')
for story in C['stories'] + OUTSIDE['stories']:
    for line in story['lines']:
        originals = line.get('documentary_original_fields', {})
        transformation_ids = line.get('transformation_ids', [])
        check(bool(originals) == bool(transformation_ids),
              f"partial documentary/display separation at {story['story_id']}:{line['line']}")
        for correction_id in transformation_ids:
            item = v2_by_id.get(correction_id)
            check(item is not None, f'unknown transformation id {correction_id}')
            if item is None:
                continue
            target = item['target']
            field = target['field']
            check(target['story_id'] == story['story_id'] and target['line'] == line['line'],
                  f'transformation target mismatch: {correction_id}')
            check(originals.get(field) == item['original_value'],
                  f'original value mismatch: {correction_id}')
            check(line.get(field) == item['revised_value'],
                  f'revised value mismatch: {correction_id}')
        if 'english_original' in line:
            check('english' in originals, f"English original without ledger at {story['story_id']}:{line['line']}")

dictionary_by_id = {entry['entry_id']: entry for entry in D['entries']}
for item in V2['corrections']:
    target = item['target']
    if target['source'] == 'corpus':
        line = line_by.get((target['story_id'], target['line']))
        check(line is not None, f"v2 corpus target missing: {item['correction_id']}")
        if line is not None:
            check(item['correction_id'] in line.get('transformation_ids', []),
                  f"v2 corpus change not attached to documentary field: {item['correction_id']}")
    else:
        entry = dictionary_by_id.get(target['entry_id'])
        check(entry is not None, f"v2 dictionary target missing: {item['correction_id']}")
        if entry is not None:
            check(entry.get(target['field']) == item['revised_value'],
                  f"v2 dictionary revised value mismatch: {item['correction_id']}")

# 4. Every entry and public story has exactly one generated page; excluded stories have none.
expected_entry_pages = {entry['entry_id'] + '.html' for entry in D['entries']}
actual_entry_pages = {path.name for path in (OUT / 'words').glob('e*.html')}
check(actual_entry_pages == expected_entry_pages, 'generated entry page set does not match public data')
expected_story_pages = {story['story_id'] + '.html' for story in C['stories']}
actual_story_pages = {path.name for path in (OUT / 'stories').glob('t*.html')}
check(actual_story_pages == expected_story_pages, 'generated story page set does not match public data')
for story_id in outside_ids:
    check(not (OUT / 'stories' / (story_id + '.html')).exists(),
          f'outside-edition story page generated: {story_id}')

# 5. Retained link, anchor, page-content, search-index, and attestation checks.
pages = sorted(OUT.rglob('*.html'))
href = re.compile(r'(?:href|src)="([^"#]*)(#[^"]*)?"')
anchor_cache = {}


def anchors_of(path):
    if path not in anchor_cache:
        anchor_cache[path] = set(re.findall(r'id="([^"]+)"', path.read_text(encoding='utf-8')))
    return anchor_cache[path]


nlinks = 0
for page in pages:
    text = page.read_text(encoding='utf-8')
    for match in href.finditer(text):
        url, fragment = match.group(1), match.group(2)
        if url.startswith(('http', 'mailto:', 'data:')):
            continue
        nlinks += 1
        target = page if url == '' else Path(os.path.normpath(page.parent / url))
        if url.endswith('/'):
            target /= 'index.html'
        if not str(target).startswith(str(OUT)):
            continue
        check(target.exists(), f"broken link in {page.relative_to(OUT)} -> {url}")
        if fragment and fragment != '#' and target.exists() and target.suffix == '.html':
            check(fragment[1:] in anchors_of(target),
                  f"broken anchor in {page.relative_to(OUT)} -> {url}{fragment}")

for entry in D['entries']:
    text = (OUT / 'words' / (entry['entry_id'] + '.html')).read_text(encoding='utf-8')
    check(html.escape(entry['headword']) in text, f"headword missing on page: {entry['entry_id']}")
    for block in re.findall(r'<div class="att">(.*?)</div>', text, re.S):
        if 'stories/' in block:
            check('<b>' in block, f"attestation without bolded form: {entry['entry_id']}")
for story in C['stories']:
    text = (OUT / 'stories' / (story['story_id'] + '.html')).read_text(encoding='utf-8')
    count = len(re.findall(r'<div class="line" id="l\d+">', text))
    check(count == story['line_count'], f"generated line count: {story['story_id']}")

index = load(OUT / 'search-index.json')
check(len(index['entries']) == len(D['entries']), 'search index entry count')
check(len(index['stories']) == len(C['stories']), 'search index story count')
check({item['i'] for item in index['entries']} == entry_id_set, 'search index entry identities')
check({item['i'] for item in index['stories']} == public_ids, 'search index story identities')
spot = (OUT / 'stories' / 't003-a-deserted-poor-woman-was-given-food-by-shag.html').read_text(encoding='utf-8')
check('hú·mis' in spot, 'Jacobs correction hú·mis not present')

# 6. No machine-specific runtime paths, later-source provenance, or changed 1990 introduction.
runtime_patterns = re.compile('|'.join((
    re.escape('/' + 'home/'),
    re.escape('/' + 'Users/'),
    'Drop' + 'box',
    'expand' + r'user\s*\(\s*["\']~',
)))
for path in sorted(TOOL_DIR.rglob('*.py')):
    check(not runtime_patterns.search(path.read_text(encoding='utf-8')),
          f'machine-specific runtime path in {path.relative_to(REPO_ROOT)}')
public_serialized = json.dumps(C, ensure_ascii=False).lower()
for later_source in ('anthony p. grant', 'john milhau', 'milhau 1856', 'harrington', 'frachtenberg'):
    check(later_source not in public_serialized,
          f'later/non-UWPA source material in public corpus: {later_source}')
intro_hash = hashlib.sha256((TOOL_DIR / 'intro1990.html').read_bytes()).hexdigest()
check(intro_hash == 'e70fe33a1a25824897bbce08d138d4bc713f36b1d4e6ab7ca883effd795386de',
      'the historical 1990 introduction changed')

# 7. The committed public/archival split reproduces from the preserved checkpoint.
subprocess_env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
with tempfile.TemporaryDirectory(prefix='miluk-corpus-repro-') as temporary:
    temporary = Path(temporary)
    generated_classification = temporary / 'source-classification.json'
    result = subprocess.run([
        sys.executable, str(TOOL_DIR / 'pipeline' / 'classify_sources.py'),
        '--corpus', str(TOOL_DIR / 'archive' / 'restoration-checkpoint' / 'corpus-v2-working.json'),
        '--output', str(generated_classification),
    ], cwd=REPO_ROOT, env=subprocess_env, text=True, capture_output=True)
    check(result.returncode == 0, 'source classification regeneration failed')
    if result.returncode == 0:
        check(generated_classification.read_bytes() == (PROV / 'source-classification.json').read_bytes(),
              'source classification does not reproduce')
    generated_public = temporary / 'corpus.json'
    generated_outside = temporary / 'slip-file-records.json'
    generated_containers = temporary / 'working-containers.json'
    result = subprocess.run([
        sys.executable, str(TOOL_DIR / 'pipeline' / 'publish_corpus.py'),
        '--working-corpus', str(TOOL_DIR / 'archive' / 'restoration-checkpoint' / 'corpus-v2-working.json'),
        '--classification', str(PROV / 'source-classification.json'),
        '--v2-receipt', str(PROV / 'v2-effective-diff.json'),
        '--public-output', str(generated_public),
        '--outside-output', str(generated_outside),
        '--containers-output', str(generated_containers),
    ], cwd=REPO_ROOT, env=subprocess_env, text=True, capture_output=True)
    check(result.returncode == 0, 'public corpus regeneration failed')
    if result.returncode == 0:
        check(generated_public.read_bytes() == (DATA / 'corpus.json').read_bytes(),
              'public corpus does not reproduce from the checkpoint')
        check(generated_outside.read_bytes() == (ARCHIVE / 'slip-file-records.json').read_bytes(),
              'outside-edition corpus does not reproduce from the checkpoint')
        check(generated_containers.read_bytes() == (ARCHIVE / 'working-containers.json').read_bytes(),
              'working containers do not reproduce from the checkpoint')

# 8. A second generation is byte-for-byte deterministic.
def generated_hashes():
    excluded = {OUT / 'data' / 'corpus.json', OUT / 'data' / 'dictionary.json'}
    return {path.relative_to(OUT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(OUT.rglob('*')) if path.is_file() and path not in excluded}


if not args.skip_determinism:
    before = generated_hashes()
    result = subprocess.run([sys.executable, str(TOOL_DIR / 'gen.py'),
                             '--data', str(DATA), '--out', str(OUT)],
                            cwd=REPO_ROOT, env=subprocess_env, text=True, capture_output=True)
    check(result.returncode == 0, 'second deterministic generator run failed')
    check(before == generated_hashes(), 'second generator run changed generated bytes')

if not args.skip_git_diff:
    result = subprocess.run(['git', 'diff', '--exit-code', '--', 'dictionary'],
                            cwd=REPO_ROOT, text=True, capture_output=True)
    check(result.returncode == 0, 'generator leaves an unexpected tracked dictionary diff')

print('links checked :', nlinks)
print('pages checked :', len(pages))
print('entries       :', len(D['entries']))
print('public stories:', C['story_count'])
print('public lines  :', C['line_count'])
print('collation rows:', len(COLLATION['corrections']))
if fails:
    print(f'\nFAILURES: {len(fails)}')
    for failure in fails[:50]:
        print('  -', failure)
    sys.exit(1)
print('ALL CHECKS PASS')
