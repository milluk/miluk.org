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
from collections import Counter

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
PUBLICATION = load(PROV / 'publication-inventory.json')
AUTHORITY = load(PROV / 'authoritative-directory-inventory.json')
RECOVERED_MANIFEST = load(PROV / 'recovered-source-manifest.json')
RECOVERED_RECORDS = load(PROV / 'recovered-records.json')
JACOBS = load(PROV / 'jacobs-alphabet.json')
ATTESTED_INDEX = load(PROV / 'attested-index-inventory.json')
SURROGATE_AUDIT = load(PROV / 'filename-surrogate-inventory.json')
DZ_CHECKPOINT = load(TOOL_DIR / 'archive' / 'restoration-checkpoint' / 'dictionary-dz-1111.json')
sys.path.insert(0, str(TOOL_DIR / 'pipeline'))
from jacobs_alphabet import (DOCUMENTARY_EXCEPTIONS, JACOBS_ALPHABET,
                             ORDER as JACOBS_ORDER, PRESENTATION_HEADWORD_FORMS,
                             american_english_order, initial_for_entry, initial_key,
                             presentation_headword, presentation_headword_ascii)
from build_filename_surrogate_inventory import audit as audit_filename_surrogates
from parse_byn import parse_byn
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
check(C['story_count'] == 108, 'public corpus must contain 108 recovered UWPA-section records')
check(C['line_count'] == 7149, 'public corpus must contain 7,149 recovered UWPA-section lines')
check(OUTSIDE['story_count'] == 35 and OUTSIDE['line_count'] == 574,
      'outside-edition archive must preserve 35 slip records / 574 lines')
check(CONTAINERS['story_count'] == 8 and CONTAINERS['line_count'] == 0,
      'working-container archive must preserve eight empty containers')
check(D['entry_count'] == len(D['entries']) == 1275, 'complete dictionary entry count')
check(D['entries'][:1111] == DZ_CHECKPOINT['entries'],
      'existing D-Z entry content and identifiers must remain unchanged')
check(D['entries'][1110] == DZ_CHECKPOINT['entries'][1110] and
      D['entries'][1110]['entry_id'] == 'e1111-z',
      'documentary Z source entry must remain exactly unchanged')
check(D.get('recovery', {}).get('baseline_entry_count') == 1111 and
      D.get('recovery', {}).get('recovered_source_record_count') == 165 and
      D.get('recovery', {}).get('recovered_entry_count') == 164 and
      D.get('recovery', {}).get('documented_exclusion_count') == 1,
      'dictionary recovery counts')
for story in C['stories']:
    check(story['lines'], f"empty public story: {story['story_id']}")
    check(story.get('source', {}).get('layer') == 'uwpa-recovered-record',
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
check(CLASSIFICATION.get('classification_scope') == 'recovered Word Cruncher export records',
      'source classification scope must describe recovered records')
check('does not' in CLASSIFICATION.get('completeness_limit', '') or
      'requires' in CLASSIFICATION.get('completeness_limit', ''),
      'source classification must not claim publication completeness')
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

# 1b. Exhaustive authority inventory and byte-preserved A-C sources/support.
check(AUTHORITY['totals']['regular_files'] == len(AUTHORITY['files']) == 2118,
      'authority inventory must cover all 2,118 regular files')
check(all(item.get('pipeline_disposition') for item in AUTHORITY['files']),
      'every authoritative file must have an explicit pipeline disposition')
check(AUTHORITY['totals']['admitted_existing_fin_sources'] == 684 and
      AUTHORITY['totals']['admitted_recovered_sources'] == 5 and
      AUTHORITY['totals']['recovered_records'] == 165,
      'authority admitted source counts')
check(AUTHORITY['comparison']['old_archive_matches_authoritative_root_fin'] is True,
      'old 684-file archive must match the authoritative root FIN set')
check(set(AUTHORITY['comparison']['omitted_admitted_sources']) ==
      {'ABC/DICT#.BYN', 'ABC/DICT%.BYN', 'ABC/DICTA.BYN', 'ABC/DICTB.BYN', 'ABC/DICTC.BYN'},
      'exact old-discovery omissions')
check(RECOVERED_MANIFEST['file_count'] == len(RECOVERED_MANIFEST['files']) == 91,
      'recovered archive manifest count')
for item in RECOVERED_MANIFEST['files']:
    source = TOOL_DIR / item['archive_path']
    check(source.exists(), f"recovered archive file missing: {item['archive_path']}")
    if source.exists():
        check(source.stat().st_size == item['byte_length'],
              f"recovered archive size mismatch: {item['archive_path']}")
        check(hashlib.sha256(source.read_bytes()).hexdigest() == item['sha256'],
              f"recovered archive hash mismatch: {item['archive_path']}")
expected_byn_counts = {'DICT#.BYN': 58, 'DICT%.BYN': 8, 'DICTA.BYN': 35,
                       'DICTB.BYN': 40, 'DICTC.BYN': 24}
for name, count in expected_byn_counts.items():
    parsed = parse_byn(TOOL_DIR / 'archive' / '1990-abc' / name)
    check(parsed['record_count'] == count, f'{name}: admitted record count')
check(RECOVERED_RECORDS['record_count'] == len(RECOVERED_RECORDS['records']) == 165,
      'recovered record receipt count')
source_record_ids = [item['source_record'] for item in RECOVERED_RECORDS['records']]
check(len(source_record_ids) == len(set(source_record_ids)), 'duplicate recovered source record')
recovered_entries = D['entries'][1111:]
admitted_record_ids = {item['source_record'] for item in RECOVERED_RECORDS['records']
                       if item['disposition'] == 'admitted'}
excluded_records = [item for item in RECOVERED_RECORDS['records']
                    if item['disposition'] != 'admitted']
check({e.get('source_record') for e in recovered_entries} == admitted_record_ids,
      'every admitted recovered source record must reach exactly one dictionary entry')
check(len(excluded_records) == 1 and excluded_records[0]['source_record'] == 'DICT#.BYN:27' and
      excluded_records[0]['duplicate_of'] == 'DICT#.BYN:28',
      'the strict-superset source duplicate must be the sole documented exclusion')
duplicate = D['recovery']['duplicate_relationships'][0]
check(duplicate['relationship'] == 'strict-documentary-superset' and
      duplicate['excluded_source_record'] == 'DICT#.BYN:27' and
      duplicate['retained_source_record'] == 'DICT#.BYN:28' and
      duplicate['retained_additions']['extensions'] == ['-t'] and
      duplicate['retained_additions']['alternate_forms_ascii'] == ["#dje`"],
      'DICT#.BYN row 28 strict-superset relationship changed')
retained_duplicate = next(e for e in recovered_entries if e.get('source_record') == 'DICT#.BYN:28')
check(retained_duplicate.get('source_records') == ['DICT#.BYN:28', 'DICT#.BYN:27'],
      'retained #dja entry must trace to both source rows')
for entry in recovered_entries:
    page = (OUT / 'words' / (entry['entry_id'] + '.html')).read_text(encoding='utf-8')
    for source_line in entry.get('raw_source_lines', []):
        if source_line:
            check(html.escape(source_line, quote=True) in page,
                  f"complete 1990 source line not rendered: {entry['source_record']}")
check({e['entry_id'] for e in recovered_entries} ==
      {item['entry_id'] for item in RECOVERED_RECORDS['records'] if item['entry_id']},
      'recovered record-to-entry trace is not bijective')
fin_names = {item['path'] for item in FIN_MANIFEST['files']}
for entry in D['entries'][:1111]:
    check((entry['source_file'] + '.FIN') in fin_names,
          f"baseline entry lacks archived source trace: {entry['entry_id']}")

# Jacobs inventory and exact-one, longest-match initial classification.
check(JACOBS['authority']['sha256'] ==
      'de8f1cd6abfb4a19088cc87e2fab564ac081b87d6de34f3596283a6ec9ab050f',
      'Jacobs phonetic authority hash')
check(JACOBS['historical_mapping']['sha256'] ==
      'bdc74baa66c467d731f8ab9c9a44f93ca4e2bd4704d3cb45bc2605c718d31ba2',
      'historical Anderson-to-Jacobs mapping hash')
check(JACOBS['phonetic_unit_count'] == len(JACOBS['phonetic_inventory']) == 68 and
      JACOBS['documentary_exception_count'] == 1,
      'complete Jacobs inventory/documentary exception counts')
classified_initials = [initial_for_entry(e) for e in D['entries']]
check(len(classified_initials) == len(D['entries']), 'every headword receives one Jacobs-aware category')
attested_initials = sorted(set(classified_initials), key=JACOBS_ORDER.__getitem__)
check({'#', '%', 'c', 'tc', "t'c", 'z-exception'} <= set(attested_initials),
      'focused Jacobs initial categories are missing')
check(initial_key("t'ca") == "t'c" and initial_key('tca') == 'tc' and
      initial_key("t'#a") == "t'#" and initial_key('t#a') == 't#',
      'longest valid initial must precede its prefix')
longest_cases = {"dja": "dj", "dza": "dz", "tsa": "ts", "t'sa": "t's",
                 "gwa": "gw", "kwa": "kw", "k!wa": "k!w", "xwa": "xw",
                 "g;wa": "g;w", "qwa": "qw", "q!wa": "q!w",
                 "%;wa": "%;w", "x;wa": "x;w", "dla": "dl"}
for sample, expected in longest_cases.items():
    check(initial_key(sample) == expected, f'longest-match failure: {sample} -> {expected}')
check(all(row['key'] != 'z' and row['display'] != 'Z' for row in JACOBS_ALPHABET),
      'independent z must not enter the Jacobs phonetic inventory')
check(DOCUMENTARY_EXCEPTIONS == [JACOBS['documentary_index_exceptions'][0]] and
      DOCUMENTARY_EXCEPTIONS[0]['display'] == 'z' and
      DOCUMENTARY_EXCEPTIONS[0]['entry_id'] == 'e1111-z' and
      DOCUMENTARY_EXCEPTIONS[0]['source_file'] == 'Z',
      'documentary Z exception scope changed')
try:
    initial_key('Z')
except ValueError:
    pass
else:
    check(False, 'independent z classified without documentary authorization')
check(initial_key('Z', entry_id='e1111-z', source_file='Z') == 'z-exception',
      'authorized documentary Z entry did not classify')
check([e['entry_id'] for e in D['entries'] if
       (e.get('headword_ascii') or '').lower().startswith('z')] == ['e1111-z'],
      'additional independent-z initial requires separate authorization')
length_bearing_barred_l = [e for e in D['entries'] if
                           (e.get('headword_ascii') or '').lower().startswith('#:')]
check([e['entry_id'] for e in length_bearing_barred_l] ==
      ['e1114-l-e-nwi', 'e1115-l-a', 'e1116-l-g-e-n', 'e1117-l-u'] and
      all(e['headword'].startswith('ł·') for e in length_bearing_barred_l),
      'exact recovered barred-L-plus-length record set')
check(all(initial_for_entry(e) == '#' for e in length_bearing_barred_l),
      'barred-L-plus-length records must index beneath barred L')
check(any(row['key'] == '#:' for row in JACOBS['phonetic_inventory']) and
      '#:' not in attested_initials,
      'Jacobs barred-L glottalized unit must remain in the 68 but be unattested initially')
check(SURROGATE_AUDIT['schema'] == 'miluk-1990-filename-surrogate-audit/1' and
      SURROGATE_AUDIT['entry_count'] == len(D['entries']) == 1275,
      'filename-surrogate audit must account for every entry')
check(SURROGATE_AUDIT['disposition_counts'] == {
      'accepted-filename-surrogate': 224,
      'filename-reference-fold-mismatch': 247,
      'not-fin-source': 164,
      'not-single-reference-list': 178,
      'shared-fin-source': 462,
      }, 'filename-surrogate audit disposition counts')
check(SURROGATE_AUDIT['accepted_alias_count'] == len(PRESENTATION_HEADWORD_FORMS) == 224 and
      SURROGATE_AUDIT['initial_repair_count'] == 71,
      'complete filename-surrogate alias and initial-repair counts')
check(audit_filename_surrogates(D, TOOL_DIR / 'archive' / '1990-fin') == SURROGATE_AUDIT,
      'filename-surrogate audit must reproduce from protected FIN sources')
entries_by_id = {entry['entry_id']: entry for entry in D['entries']}
for rule in SURROGATE_AUDIT['accepted_aliases']:
    entry = entries_by_id[rule['entry_id']]
    check(presentation_headword_ascii(entry) == rule['first_reference_ascii'] and
          presentation_headword(entry) == rule['first_reference_display'] and
          initial_for_entry(entry) == rule['initial_key'],
          f"audited filename surrogate not used for public presentation: {entry['entry_id']}")
ka_entry = next(e for e in D['entries'] if e['entry_id'] == 'e0511-ka')
check((ka_entry['headword'], ka_entry['headword_ascii'], ka_entry['source_file']) ==
      ('ka', 'KA', 'KA'),
      'KA.FIN filename-derived protected fields changed')
check([form for form in ka_entry['forms']
       if form.get('ascii') == "k!&a'" and form.get('form') == "k̯̓a'"] ==
      [ka_entry['forms'][0]],
      'KA.FIN first Reference List form no longer uniquely supports the public headword')
check(presentation_headword(ka_entry) == "k̯̓a'" and
      initial_for_entry(ka_entry) == 'k!&' and
      initial_key("k!&a'") == initial_key("k&!a'") == initial_key("k̯̓a'") == 'k!&',
      'people headword must present and classify as initial anterior-palatal ejective k')
check('e0511-ka' in [e['entry_id'] for e in D['entries'] if initial_for_entry(e) == 'k!&'] and
      len([e for e in D['entries'] if initial_for_entry(e) == 'k!&']) == 10,
      'all provenanced anterior-palatal ejective-k forms must share one category')
ka_fin = TOOL_DIR / 'archive' / '1990-fin' / 'KA.FIN'
check(hashlib.sha256(ka_fin.read_bytes()).hexdigest() ==
      '2687f8b29f5aa114b3a55b4456fbf86d187aa0b2fb94638a5b96ff07f3004b0d',
      'protected KA.FIN bytes changed')
length_bearing_x = [e for e in D['entries'] if e['headword'].startswith('x·')]
check([e['entry_id'] for e in length_bearing_x] == ['e1021-xinxinu'] and
      initial_for_entry(length_bearing_x[0]) == 'x',
      'length-bearing x record must index beneath x')
check(any(row['key'] == 'x:' for row in JACOBS['phonetic_inventory']) and
      'x:' not in attested_initials,
      "Jacobs x' unit must remain in the 68 but be unattested initially")
attested_counts = Counter(classified_initials)
check([row['key'] for row in ATTESTED_INDEX['categories']] == attested_initials,
      'attested index receipt category order')
check({row['key']: row['count'] for row in ATTESTED_INDEX['categories']} == dict(attested_counts),
      'attested index receipt counts')
check(all(row['count'] > 0 for row in ATTESTED_INDEX['categories']),
      'attested index receipt contains an empty category')

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

# Publication titles are a separate level from recovered export records.
publication_texts = PUBLICATION['texts']
publication_ids = [item['publication_id'] for item in publication_texts]
check(PUBLICATION['schema'] == 'miluk-uwpa-publication-inventory/2',
      'publication inventory schema')
check({'contents_title', 'heading_title', 'printed_start_page',
       'printed_page_span', 'status', 'corpus_mapping'} <=
      set(PUBLICATION.get('field_definitions', {})),
      'publication inventory field semantics are documented')
check(PUBLICATION['counts']['published_titles'] == len(publication_texts) == 111,
      'publication inventory must contain 111 Miluk-bearing titles')
check(len(publication_ids) == len(set(publication_ids)), 'duplicate publication identity')
check(sum(item['volume'] == '1939' for item in publication_texts) == 77,
      '1939 publication inventory must contain 77 titles')
check(sum(item['volume'] == '1940' for item in publication_texts) == 34,
      '1940 publication inventory must contain 34 titles')
status_counts = {status: sum(item['status'] == status for item in publication_texts)
                 for status in ('separate', 'absorbed_into_another_record', 'absent')}
check(status_counts == {'separate': 108, 'absorbed_into_another_record': 2, 'absent': 1},
      'publication inventory disposition counts')
check(sum(item['status'] != 'absent' for item in publication_texts) == 110,
      '108 recovered records must represent 110 published texts')
check(PUBLICATION['counts']['recovered_corpus_records'] == 108 and
      PUBLICATION['counts']['represented_titles'] == 110 and
      PUBLICATION['counts']['jacobs_1939_titles'] == 77 and
      PUBLICATION['counts']['jacobs_1940_titles'] == 34,
      'declared publication inventory counts')
separate_story_ids = {item['corpus_mapping']['story_id'] for item in publication_texts
                      if item['status'] == 'separate'}
check(separate_story_ids == public_ids and len(separate_story_ids) == 108,
      'every public record must map to one separate publication title')
publication_lines_by_story = {story_id: [] for story_id in public_ids}
for item in publication_texts:
    check({'publication_id', 'volume', 'contents_title', 'printed_start_page',
           'status', 'corpus_mapping'} <= set(item),
          f"incomplete publication inventory item: {item.get('publication_id')}")
    check('printed_title' not in item and 'printed_pages' not in item,
          f"ambiguous legacy publication fields: {item.get('publication_id')}")
    check(isinstance(item['printed_start_page'], int) and item['printed_start_page'] > 0,
          f"invalid publication start page: {item.get('publication_id')}")
    page_span = item.get('printed_page_span')
    if page_span is not None:
        check(set(page_span) == {'start', 'end'} and
              isinstance(page_span['start'], int) and
              isinstance(page_span['end'], int) and
              page_span['start'] == item['printed_start_page'] and
              page_span['end'] >= page_span['start'],
              f"invalid verified publication page span: {item.get('publication_id')}")
    mapping = item['corpus_mapping']
    if mapping is None:
        continue
    check(mapping['story_id'] in public_ids,
          f"publication mapping outside public corpus: {item['publication_id']}")
    for line_number in range(mapping['line_start'], mapping['line_end'] + 1):
        check((mapping['story_id'], line_number) in line_by,
              f"publication mapping line missing: {item['publication_id']}:{line_number}")
        publication_lines_by_story[mapping['story_id']].append(line_number)
story_by_id = {story['story_id']: story for story in C['stories']}
for story_id, mapped_lines in publication_lines_by_story.items():
    check(sorted(mapped_lines) == list(range(1, story_by_id[story_id]['line_count'] + 1)),
          f'publication mappings must cover each recovered line exactly once: {story_id}')
known_publication_mappings = {
    'A man obtains fir power': {
        'contents_title': 'A man obtained fir power',
        'pages': (28, 29),
        'mapping': ('t006-hadj-yasa-t-i-l-and-others', 69, 90,
                    'absorbed_into_another_record'),
    },
    'The water got high': {
        'contents_title': 'The water got high',
        'pages': (58, 59),
        'mapping': ('t023-he-eats-human-children', 92, 118,
                    'absorbed_into_another_record'),
    },
}
for heading_title, expected in known_publication_mappings.items():
    matches = [item for item in publication_texts
               if item.get('heading_title') == heading_title]
    check(len(matches) == 1, f'unique publication heading title: {heading_title}')
    if len(matches) == 1:
        item = matches[0]
        mapping = item['corpus_mapping']
        actual = (mapping['story_id'], mapping['line_start'], mapping['line_end'],
                  item['status'])
        check(item['contents_title'] == expected['contents_title'],
              f'documentary title forms remain separate: {heading_title}')
        check((item['printed_start_page'], item['printed_page_span']['end']) ==
              expected['pages'], f'verified printed page span: {heading_title}')
        check(actual == expected['mapping'],
              f'absorbed publication mapping: {heading_title}')
absent = [item for item in publication_texts if item['status'] == 'absent']
check(len(absent) == 1 and
      absent[0]['contents_title'] == 'The rock point person lost his good luck thing' and
      absent[0]['printed_start_page'] == 133 and
      absent[0]['printed_page_span'] == {'start': 133, 'end': 135} and
      absent[0]['corpus_mapping'] is None,
      'missing 1940 text must remain explicitly absent')
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
    check(html.escape(presentation_headword(entry)) in text,
          f"presentation headword missing on page: {entry['entry_id']}")
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
words_index = (OUT / 'words' / 'index.html').read_text(encoding='utf-8')
tab_labels = [html.unescape(value) for value in
              re.findall(r'<a href="#s-\d+">([^<]+)</a>', words_index)]
expected_labels = [next(row['display'] for row in
                        JACOBS['phonetic_inventory'] + JACOBS['documentary_index_exceptions']
                        if row['key'] == key)
                   for key in sorted(attested_initials, key=american_english_order)]
check(tab_labels == expected_labels,
      'emitted index tabs must equal attested initial categories in American English order')
search_by_id = {item['i']: item for item in index['entries']}
check(search_by_id['e1111-z']['k'] == 'z', 'documentary Z entry literal search key changed')
check('>z</a>' in words_index and '>Z</a>' not in words_index,
      'documentary index heading must be lowercase z')
check('ł′' not in tab_labels and 'ł' in tab_labels,
      'unattested barred-L glottalized tab must not be emitted')
check("x'" not in tab_labels and 'x' in tab_labels,
      "unattested x glottalized tab must not be emitted")
for entry in length_bearing_barred_l:
    page = (OUT / 'words' / (entry['entry_id'] + '.html')).read_text(encoding='utf-8')
    check('<a href="../words/index.html">Words</a> · ł</p>' in page,
          f"barred-L-plus-length breadcrumb: {entry['entry_id']}")
ka_page = (OUT / 'words' / 'e0511-ka.html').read_text(encoding='utf-8')
check('<h1 class="hw">k̯̓a&#x27;</h1>' in ka_page and
      '<a href="../words/index.html">Words</a> · k̯&#x27;</p>' in ka_page and
      '1990 source file: KA · id: e0511-ka' in ka_page,
      'KA.FIN public headword, lawful category, or provenance missing')
check('href="e0511-ka.html" class="mk">k̯̓a&#x27;</a>' in words_index and
      search_by_id['e0511-ka']['h'] == "k̯̓a'" and
      search_by_id['e0511-ka']['k'] == 'ka',
      'people presentation headword missing from index/search surfaces')
x_length_page = (OUT / 'words' / 'e1021-xinxinu.html').read_text(encoding='utf-8')
check('<a href="../words/index.html">Words</a> · x</p>' in x_length_page,
      'length-bearing x breadcrumb must use x rather than unattested x glottalized')

# Linguistic alphabet labels inherit Charis; interface chrome remains on the
# system stack. This directly guards the selector path identified in Chrome.
style = (OUT / 'style.css').read_text(encoding='utf-8')
check(re.search(r'h2\[id\^="s-"\]\s*\{[^}]*var\(--font-serif\)', style, re.S),
      'linguistic index headings must use the Charis serif stack')
check(re.search(r'\.alpha\s*\{[^}]*var\(--font-serif\)', style, re.S),
      'linguistic alphabet navigation must use the Charis serif stack')
check(re.search(r'\.crumb\s*\{[^}]*var\(--font-serif\)', style, re.S) and
      re.search(r'\.crumb a\s*\{[^}]*var\(--font-sans\)', style, re.S),
      'linguistic breadcrumb label must use Charis while its interface link remains sans')
check('>x̣</a>' in words_index and re.search(r'<h2 id="s-\d+">x̣</h2>', words_index) and
      '<a href="../words/index.html">Words</a> · x̣</p>' in
      (OUT / 'words' / 'e1022-xlgwat.html').read_text(encoding='utf-8'),
      'x-dot-below linguistic tab, heading, and breadcrumb selector paths changed')

# Public reference presentation: raw data remains archival ASCII; exactly four
# pre-fix fields required deterministic conversion, and only unique targets link.
see_glosses = [e for e in D['entries'] if re.search(r'\bsee\b', e.get('gloss') or '', re.I)]
check(len(see_glosses) == 7, 'exhaustive see-gloss audit count changed')
check(sum(len(e.get('cross_references', [])) for e in D['entries']) == 12,
      'exhaustive structured cross-reference audit count changed')
expected_reference_rendering = {
    'e0032-den': ('dá·tsan', 'e0039-datsan.html'),
    'e0193-e-le-ma': ("lə́'ma", 'e0578-lama.html'),
    'e0295-gendji': ('g̣ɛ́wi', 'e0300-gewi.html'),
}
raw_reference_targets = {
    'e0032-den': 'da:<tsan',
    'e0193-e-le-ma': "l@<'ma",
    'e0295-gendji': 'g;e<wi',
}
for entry_id, (label, target) in expected_reference_rendering.items():
    page = (OUT / 'words' / (entry_id + '.html')).read_text(encoding='utf-8')
    check(html.escape(label, quote=True) in page and ('href="' + target + '"') in page,
          f'deterministic public see-reference conversion/link: {entry_id}')
    raw_target = raw_reference_targets[entry_id]
    check(html.escape(raw_target, quote=True) not in page and
          html.escape(raw_target, quote=True) not in words_index and
          raw_target not in search_by_id[entry_id]['g'] and
          label in search_by_id[entry_id]['g'],
          f'archival see-target leaked through a public surface: {entry_id}')
demedes = (OUT / 'words' / 'e0011-demedes.html').read_text(encoding='utf-8')
check('də́m·ɛ·dɛ' in demedes and 'd@&lt;m:e:de' not in demedes,
      'unresolved structured reference must be converted but not linked')
ambiguous = (OUT / 'words' / 'e0008-delagawiyatas.html').read_text(encoding='utf-8')
check('łag̣áwiyát̓as' in ambiguous and '<p class="xref">See <a ' not in ambiguous,
      'ambiguous structured reference must not retain a guessed link')
gendji_source = (TOOL_DIR / 'archive' / '1990-fin' / 'GENDJI.FIN').read_text(
    encoding='ascii', errors='ignore')
check('see g;e<wi' in gendji_source and dictionary_by_id['e0295-gendji']['gloss'] == 'see g;e<wi',
      'e0295 archival ASCII cross-reference changed')
for key, alias in (('c', 'sh'), ('tc', 'ch'), ("t'c", "ch'")):
    example = next(e for e in D['entries'] if initial_for_entry(e) == key)
    check(any(value.startswith(re.sub(r'[^a-z0-9]', '', alias))
              for value in search_by_id[example['entry_id']]['kk']),
          f'search alias missing for {key}: {alias}')
    check(initial_for_entry(example) == key,
          f'search alias changed canonical category: {key}')
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
check(hashlib.sha256((DATA / 'corpus.json').read_bytes()).hexdigest() ==
      '0183a6305d0dc0a9737cad10eebaf47cd881ba12575f4cb47702fd3b0001f854',
      'public corpus bytes changed')
hold_hashes = {
    REPO_ROOT / '_config.yml': '64f01ca1d2469737772c9ffb809999d07fc804ce36584f22811fc6e94c5eff7b',
    REPO_ROOT / 'robots.txt': '78d87696b39031b60cd896b1ce0538a68f1612311e358dab0a38120918329f11',
    TOOL_DIR / 'PUBLICATION_HOLD.md': '64a87de56cddd8e166d5b42d5a2d68b3b552fc0b2c018575ae897b663ce9f14f',
    REPO_ROOT / 'index.html': 'e86763ce492fd0a4be1e48b299af262cf2ba476828b26d84307236d5754da719',
}
for path, expected_hash in hold_hashes.items():
    check(hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash,
          f'publication hold changed: {path.relative_to(REPO_ROOT)}')

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
print('public records:', C['story_count'])
print('represented texts:', sum(item['status'] != 'absent' for item in publication_texts))
print('published titles:', len(publication_texts))
print('public lines  :', C['line_count'])
print('collation rows:', len(COLLATION['corrections']))
if fails:
    print(f'\nFAILURES: {len(fails)}')
    for failure in fails[:50]:
        print('  -', failure)
    sys.exit(1)
print('ALL CHECKS PASS')
