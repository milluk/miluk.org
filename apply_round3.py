#!/usr/bin/env python3
"""One-shot applier: round two of the 2026 notebook collation.

Run once from the repository root:

    python3 apply_round3.py

Then rebuild the corpus and the site. This file is deleted in the same commit.

Three things happen here.

1. t039 76/77 -- the vocative stranded at the end of line 76 moves down to 77,
   where the edition's own English for it already stands. Line 77 then becomes
   byte-identical to line 80 of the same story, which carries the same English
   against the same two vocatives, and the pair matches Notebook 99 p. 37.

2. t055 1308 -- the English on that line glosses the following notebook page.
   Jacobs' own gloss for this line's Miluk is put back. Issue #15.

3. Two guardrail repairs and one new guardrail, described at each site below.

Nothing non-ASCII is typed here. Every non-ASCII value is derived by splitting
a string the repository already holds, and checked against an independent copy
of the same text elsewhere in the corpus. Retyped combining marks are how a
restoration corrupts itself quietly.

Item 1 changes the 1990 line division, which the project otherwise leaves
alone. Directed by Troy, 16 September 2026; the documentary division is kept in
each line's documentary_original_fields.
"""
import json
import sys
from pathlib import Path

TOOL = Path('tools/dictionary')
CORRECTIONS = TOOL / 'provenance' / 'notebook-collation-corrections.json'
V2_RECEIPT = TOOL / 'provenance' / 'v2-effective-diff.json'
CHECKPOINT = TOOL / 'archive' / 'restoration-checkpoint' / 'corpus-v2-working.json'
INTEGRITY = TOOL / 'test_corpus_integrity.py'
SITE = TOOL / 'test_site.py'

T039 = 't039-black-bear-and-pack-basket-bear-grizzly'
T055 = 't055-the-trickster-person-who-made-the-country'
DIRECTION = 'Directed by Troy, 2026-09-16'

L1308_BEFORE = 'For five days they gambled with thyes.'
L1308_AFTER = 'Now he took out the snail-shell eyes.'


def fail(message):
    sys.exit('apply_round3: ' + message)


def replace_once(path, old, new):
    text = path.read_text(encoding='utf-8')
    if text.count(old) != 1:
        fail('%s: anchor matches %d times, expected exactly 1'
             % (path, text.count(old)))
    path.write_text(text.replace(old, new), encoding='utf-8')


def record(correction_id, story_id, line, field, original, revised,
           change_kind, reason, source, issue, **extra):
    out = {
        'correction_id': correction_id,
        'target': {'source': 'corpus', 'story_id': story_id,
                   'line': line, 'field': field},
        'original_value': original,
        'revised_value': revised,
        'disposition': 'changed',
        'change_kind': change_kind,
        'reason': reason,
        'verification_source': source,
        'affects': 'restoration-corpus',
        'restoration_stage': '2026 notebook collation',
    }
    out.update(extra)
    out['github_issue'] = issue
    return out


def main():
    v2 = {item['correction_id']: item for item in
          json.loads(V2_RECEIPT.read_text(encoding='utf-8'))['corrections']}
    checkpoint = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    stories = {s['story_id']: {l['line']: l for l in s['lines']}
               for s in checkpoint['stories']}
    data = json.loads(CORRECTIONS.read_text(encoding='utf-8'))
    have = {item['correction_id'] for item in data['corrections']}
    new = []

    # ------------------------------------------------- t039 76/77 redivision
    t039_source = ('Melville Jacobs Notebook 99 p. 37, which carries the cry '
                   'and then two vocatives; and line 80 of this same story, '
                   'where the identical English already stands against two '
                   'vocatives on one line')
    reason_76 = (
        'the vocative closing this line has no English against it here, '
        'because the edition glosses it on line 77. Moving it to 77 leaves '
        'line 76 as the untranslated cry alone, matching its English, and '
        'makes line 77 identical in shape to line 80 of this story. No word '
        'is added or lost; ' + DIRECTION)
    reason_77 = (
        'this line reads "My children, my children" against a single '
        'vocative. The second is the one stranded at the end of line 76. '
        'After the move this line is byte-identical to line 80, which carries '
        'the same English against two vocatives; ' + DIRECTION)

    for field in ('miluk_ascii', 'miluk'):
        slug = field.replace('_', '-')
        documentary = v2['v2-corpus-t039-l0076-%s' % slug]['original_value']
        head, separator, tail = documentary.rpartition(' ')
        if not separator:
            fail('t039 76 %s: cannot split a tail off %r' % (field, documentary))
        moved = tail.rstrip(',')
        line77 = stories[T039][77][field]
        line80 = stories[T039][80][field]
        rebuilt = moved + ' ' + line77
        if rebuilt != line80:
            fail('t039 %s: rebuilt line 77 does not match line 80\n'
                 '  rebuilt %r\n  line 80 %r' % (field, rebuilt, line80))
        new.append(record(
            'nbc-corpus-t039-l0076-%s-redivide' % slug, T039, 76, field,
            documentary, head, 'repair-line-division', reason_76,
            t039_source, 18, moved_to={'line': 77, 'token': moved}))
        new.append(record(
            'nbc-corpus-t039-l0077-%s' % slug, T039, 77, field,
            line77, rebuilt, 'repair-line-division', reason_77,
            t039_source, 18, moved_from={'line': 76, 'token': moved},
            equals_line=80))

    # ------------------------------------------------------ t055 1308 English
    current = stories[T055][1308]['english']
    if current != L1308_BEFORE:
        fail('t055 1308 english is not the expected value: %r' % current)
    new.append(record(
        'nbc-corpus-t055-l1308-english', T055, 1308, 'english',
        L1308_BEFORE, L1308_AFTER, 'english-misattached',
        "the English on this line glosses Notebook 98 p. 25, the following "
        "page: 'five days' and 'they gambled with their eyes' are that page's "
        "gloss, not this line's. Jacobs' gloss for this line's own Miluk, on "
        "p. 24, is 'Now he took out the snail shell eyes'. The printed text "
        "also carries a typo, 'thyes' for 'their eyes', which is what makes "
        'the misattachment visible without the notebook; ' + DIRECTION,
        'Melville Jacobs Notebook 98 pp. 24-25; alignment matched this line '
        'confirmed against p. 24', 15,
        not_addressed_here={
            'field': 'entries',
            'value': ['e0272-gahais', 'e0297-gent-cin'],
            'why': "these are the 1990 dictionary's own citations of this "
                   "line for 'day' and 'five', mirrored by attestations in "
                   'dictionary.json. Severing one side would be the first '
                   'disagreement between the two in all 7,149 lines. Check 8 '
                   'now holds them level, so this has to be repaired on both '
                   'sides at once, in its own pass.'}))

    for item in new:
        if item['correction_id'] in have:
            fail('%s is already present' % item['correction_id'])
        data['corrections'].append(item)

    for item in data['corrections']:
        if item['correction_id'] == 'nbc-corpus-t039-l0076-english':
            alternative = item.get('considered_alternative')
            if not alternative:
                fail('the t039 l0076 english record has no considered_alternative')
            alternative['rejected_because'] += (
                ' Superseded in part: the line division was afterwards '
                'repaired instead, by moving the vocative down to line 77 '
                'rather than repeating its gloss on 76. See '
                'nbc-corpus-t039-l0076-miluk-redivide.')
            break
    else:
        fail('the t039 l0076 english record was not found')

    data['summary']['records'] = len(data['corrections'])
    data['summary']['lines_affected'] = len(
        {(i['target']['story_id'], i['target']['line']) for i in data['corrections']})
    data['summary']['reverted_transformations'] = sorted(
        {r for i in data['corrections'] for r in i.get('reverts', [])})
    data['note_on_line_divisions'] = (
        'Records with change_kind repair-line-division move Miluk words '
        'between two adjacent published lines so that each line matches the '
        'English printed beside it. They add, drop and alter nothing: check 7 '
        'holds the pair to the same words it held documentarily. They do '
        'change the 1990 line division, which the project otherwise leaves '
        'alone, so each is directed by Troy and the documentary division is '
        "kept in each line's documentary_original_fields.")
    data['note_on_multiple_records_per_field'] = (
        'A field may carry more than one record here when a later pass builds '
        'on an earlier one -- t039 line 76 is first reverted to its '
        'documentary value and then redivided. Records apply in file order, '
        'and anything checking that a correction took effect must look at the '
        'last record touching that field, not every one.')
    CORRECTIONS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8')
    print('corrections: %d records over %d lines'
          % (data['summary']['records'], data['summary']['lines_affected']))

    # ---------------------------------------------------------- check 4 fix
    # Exposed by this round: check 4 asserted every record's revised_value was
    # the field's current value, which is only true when a field carries one
    # record. test_site.py already had this fixed for the same reason; this
    # file did not, because until now no field carried two.
    old_check4 = (
        "# 4. Every notebook-collation correction is applied, and applied exactly.\n"
        "for item in NOTEBOOK['corrections']:\n"
        "    target = item['target']\n"
        "    line = LINES.get((target['story_id'], target['line']))\n"
        "    if line is None:\n"
        "        fails.append('%s: target line is missing from the corpus' % item['correction_id'])\n"
        "        continue\n"
        "    if line.get(target['field']) != item['revised_value']:\n"
        "        fails.append('%s: %s is not the revised value'\n"
        "                     % (item['correction_id'], target['field']))\n"
        "    if item['correction_id'] not in (line.get('transformation_ids') or []):\n"
        "        fails.append('%s: correction id absent from the line transformation_ids'\n"
        "                     % item['correction_id'])\n"
    )
    new_check4 = (
        "# 4. Every notebook-collation correction is applied, and the last record\n"
        "#    touching a field is the value that field now carries. A field can\n"
        "#    carry more than one record -- t039 line 76 is reverted to its\n"
        "#    documentary value and then redivided -- so asserting every record's\n"
        "#    revised_value would fail on the earlier one. test_site.py already\n"
        "#    checks the last correction per field for the same reason.\n"
        "LAST_RECORD = {}\n"
        "for item in NOTEBOOK['corrections']:\n"
        "    target = item['target']\n"
        "    LAST_RECORD[(target['story_id'], target['line'], target['field'])] = item\n"
        "for item in NOTEBOOK['corrections']:\n"
        "    target = item['target']\n"
        "    line = LINES.get((target['story_id'], target['line']))\n"
        "    if line is None:\n"
        "        fails.append('%s: target line is missing from the corpus' % item['correction_id'])\n"
        "        continue\n"
        "    key = (target['story_id'], target['line'], target['field'])\n"
        "    if LAST_RECORD[key] is item and line.get(target['field']) != item['revised_value']:\n"
        "        fails.append('%s: %s is not the revised value'\n"
        "                     % (item['correction_id'], target['field']))\n"
        "    if item['correction_id'] not in (line.get('transformation_ids') or []):\n"
        "        fails.append('%s: correction id absent from the line transformation_ids'\n"
        "                     % item['correction_id'])\n"
    )
    replace_once(INTEGRITY, old_check4, new_check4)

    # ------------------------------------------------------ check 5 literals
    old_block = (
        "    # it recovers the vocative t#@-'n@hi:<me, which no visible field\n"
        "    # carried after v2. The English is an editorial rendering of\n"
        "    # untranslated vocables, not a Jacobs gloss; the correction record\n"
        "    # carries the unit-for-unit mapping. The rendered Miluk is not\n"
        "    # asserted literally here, because writing it into this file would\n"
        "    # mean transcribing it by hand -- check 4 holds it against the\n"
        "    # correction record, which derives it from the v2 receipt.\n"
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'miluk_ascii',\n"
        '     "h@\'@:<:: he:<:. h@:<:h@h@:: t#@-\'n@hi:<me,"),\n'
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'english',\n"
        '     "Huh-\'uhhh, hehhh. Huhhh-huh-huhhh,"),\n'
    )
    new_block = (
        "    # it recovered the vocative t#@-'n@hi:<me, which no visible field\n"
        "    # carried after v2. That vocative then moved to line 77, where the\n"
        "    # edition's own English for it already stood, so 76 and 77 are\n"
        "    # asserted together: the boundary between them is the repair. Line\n"
        "    # 77 must equal line 80, which carries the same English against the\n"
        "    # same two vocatives. The English on 76 is an editorial rendering of\n"
        "    # untranslated vocables, not a Jacobs gloss. Rendered Miluk is not\n"
        "    # asserted literally here, because writing it into this file would\n"
        "    # mean transcribing it by hand -- check 4 holds it against the\n"
        "    # correction record, which derives it from the repository.\n"
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'miluk_ascii',\n"
        '     "h@\'@:<:: he:<:. h@:<:h@h@::"),\n'
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'english',\n"
        '     "Huh-\'uhhh, hehhh. Huhhh-huh-huhhh,"),\n'
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 77, 'miluk_ascii',\n"
        '     "t#@-\'n@hi:<me t#@-\'n@hi:<me!"),\n'
        "    # t055 1308's English glossed the following notebook page, typo and\n"
        "    # all ('thyes' for 'their eyes'). Its entries are still the 1990\n"
        "    # dictionary's own citations for 'day' and 'five', which belong to\n"
        "    # that same wrong gloss; check 8 is why they cannot be cut here.\n"
        "    ('t055-the-trickster-person-who-made-the-country', 1308, 'english',\n"
        '     "Now he took out the snail-shell eyes."),\n'
    )
    replace_once(INTEGRITY, old_block, new_block)

    # -------------------------------------------------- checks 7 and 8 added
    check6_tail = (
        "    if documentary_miluk and line.get('english') == documentary_miluk:\n"
        "        fails.append('%s line %d: english is verbatim the documentary miluk: %r'\n"
        '                     % (story_id, number, documentary_miluk[:70]))\n'
    )
    added = check6_tail + (
        "\n"
        "# 7. A line-division repair moves words between two adjacent lines; it must\n"
        "#    never add or drop one. For each repaired pair the words across the two\n"
        "#    lines must still be the words the documentary record held across the\n"
        "#    same two lines. Sentence punctuation is allowed to move to the new end\n"
        "#    of a line, so it is stripped before comparing; nothing else is.\n"
        'REDIVIDED_PAIRS = [\n'
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 77),\n"
        ']\n'
        "for story_id, first, second in REDIVIDED_PAIRS:\n"
        "    for field in ('miluk', 'miluk_ascii'):\n"
        '        now, before = [], []\n'
        '        for number in (first, second):\n'
        '            line = LINES.get((story_id, number))\n'
        '            if line is None:\n'
        '                continue\n'
        "            documentary = (line.get('documentary_original_fields') or {})\n"
        "            now += [w.strip(',.') for w in (line.get(field) or '').split()]\n"
        "            before += [w.strip(',.') for w in\n"
        "                       (documentary.get(field, line.get(field)) or '').split()]\n"
        '        if sorted(now) != sorted(before):\n'
        "            fails.append('%s lines %d-%d: %s words changed across the pair'\n"
        '                         % (story_id, first, second, field))\n'
        "\n"
        "# 8. Every corpus line's `entries` must be exactly the set of dictionary\n"
        "#    entries attested on that line, and the reverse. The two are one link\n"
        "#    set stored twice, and they agree on all 7,149 lines today. Nothing\n"
        "#    checked that before, which is what makes a half-repair possible:\n"
        "#    moving a word between two lines, or cutting a wrong entry link,\n"
        "#    fixes the corpus side and leaves dictionary.json pointing at a line\n"
        "#    that no longer holds the word. This is why t055 1220/1221 (#14) and\n"
        "#    the entries half of t055 1308 (#15) are not in this pass: they need\n"
        "#    a dictionary-side correction stage, which does not exist yet.\n"
        "DICTIONARY = load(DATA / 'dictionary.json')\n"
        'attested = {}\n'
        "for entry in DICTIONARY['entries']:\n"
        "    for attestation in entry.get('attestations') or []:\n"
        "        story_id = attestation.get('story_id')\n"
        "        number = attestation.get('line')\n"
        '        if story_id is None or number is None:\n'
        '            continue\n'
        "        attested.setdefault((story_id, number), set()).add(entry['entry_id'])\n"
        'for (story_id, number), line in sorted(LINES.items()):\n'
        "    here = set(line.get('entries') or [])\n"
        '    there = attested.get((story_id, number), set())\n'
        '    if here != there:\n'
        "        fails.append('%s line %d: entries %s but dictionary attests %s'\n"
        '                     % (story_id, number, sorted(here), sorted(there)))\n'
    )
    replace_once(INTEGRITY, check6_tail, added)
    print('%s: check 4 repaired, literals updated, checks 7 and 8 added' % INTEGRITY)

    # ------------------------------------------------------------- the pin
    marker = "      '2f7e96984f310cbca603862260a7fd2a954c883f8de621c3d2a3dfc92675988e',\n"
    anchor = ('#\n'
              '# The first of those was dropped from this comment when PR #17 rebuilt the\n'
              '# file through CI; it is restored here from the base branch.\n')
    replace_once(SITE, anchor,
                 '#   2f7e96984f310cbca603862260a7fd2a954c883f8de621c3d2a3dfc92675988e\n'
                 '#       t039 line 76, before the line-division repair\n' + anchor)
    replace_once(SITE, marker, "      'CORPUS_SHA_PLACEHOLDER',\n")
    print('%s: pin comment extended, new pin left as a placeholder' % SITE)


if __name__ == '__main__':
    main()
