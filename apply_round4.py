#!/usr/bin/env python3
"""One-shot applier: restore the comma the printed 1990 page carries on t039 77.

Run once from the repository root:

    python3 apply_round4.py

Then rebuild the corpus and the site. This file is deleted in the same commit.

The printed page, supplied by Troy on 16 September 2026, reads:

    "h@'@'::  he'::  h@'-h@h@::!(21)
     t#@-'n@hi:'me,  t#@-'n@hi:'me!
     t#@-d@k!i'#an,
     kwi:'ya ku:-da:'.
     t#@-'n@hi:'me  t#@-'n@hi:'me!
     da'q#a!

Two things follow.

First, the redivision already made in this branch is right: the cry stands
alone and the two vocatives stand together on the next line, exactly as the
page prints them.

Second, it corrects that redivision in one detail. The earlier record derived
line 77 by asserting it equalled line 80 of the same story, and stripped the
comma off the moved vocative to make that equality hold. The page shows the two
lines are *not* identical: the second line carries a comma between the
vocatives and the fifth does not. The comma belongs to line 77, it was there in
line 76's own documentary value, and stripping it was an inference dressed up
as a check.

So the two line-77 records are amended in place -- they are on an unmerged
branch and have not been reviewed -- rather than a third record being stacked
on the same field. The equality claim against line 80 is replaced by the thing
that is actually true: the moved token is carried across verbatim.

Nothing non-ASCII is typed here. The values are rebuilt from the same
repository sources as before.
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

PAGE_SOURCE = ('the printed 1990 page, which sets the cry on one line and the '
               'two vocatives on the next with a comma between them; Melville '
               'Jacobs Notebook 99 p. 37')

REASON_77 = (
    'this line reads "My children, my children" against a single vocative. '
    'The second is the one stranded at the end of line 76, and it is carried '
    'across verbatim, comma and all. The printed page sets these two '
    'vocatives with a comma between them; line 80 of this story prints the '
    'same two words without one, so the two lines are not identical and an '
    'earlier draft of this record was wrong to force them to be. Directed by '
    'Troy, 2026-09-16')

REASON_76 = (
    'the vocative closing this line has no English against it here, because '
    'the edition glosses it on line 77, where the printed page sets it. '
    'Moving it there leaves line 76 as the untranslated cry alone, matching '
    'its English and matching the printed page, which sets the cry on a line '
    'of its own. No word and no mark is added or lost. Directed by Troy, '
    '2026-09-16')


def fail(message):
    sys.exit('apply_round4: ' + message)


def replace_once(path, old, new):
    text = path.read_text(encoding='utf-8')
    if text.count(old) != 1:
        fail('%s: anchor matches %d times, expected exactly 1'
             % (path, text.count(old)))
    path.write_text(text.replace(old, new), encoding='utf-8')


def main():
    v2 = {item['correction_id']: item for item in
          json.loads(V2_RECEIPT.read_text(encoding='utf-8'))['corrections']}
    checkpoint = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
    stories = {s['story_id']: {l['line']: l for l in s['lines']}
               for s in checkpoint['stories']}
    data = json.loads(CORRECTIONS.read_text(encoding='utf-8'))
    by_id = {item['correction_id']: item for item in data['corrections']}

    for field in ('miluk_ascii', 'miluk'):
        slug = field.replace('_', '-')
        documentary = v2['v2-corpus-t039-l0076-%s' % slug]['original_value']
        head, separator, moved = documentary.rpartition(' ')
        if not separator:
            fail('t039 76 %s: cannot split a tail off %r' % (field, documentary))

        line77 = stories[T039][77][field]
        rebuilt = moved + ' ' + line77
        line80 = stories[T039][80][field]
        if rebuilt == line80:
            fail('t039 %s: line 77 and line 80 came out identical; the printed '
                 'page says they differ by the comma, so something is wrong'
                 % field)
        if rebuilt.replace(',', '') != line80.replace(',', ''):
            fail('t039 %s: line 77 and line 80 differ by more than punctuation\n'
                 '  line 77 %r\n  line 80 %r' % (field, rebuilt, line80))

        redivide = by_id.get('nbc-corpus-t039-l0076-%s-redivide' % slug)
        seventy_seven = by_id.get('nbc-corpus-t039-l0077-%s' % slug)
        if redivide is None or seventy_seven is None:
            fail('the round-two records for t039 %s are not present' % field)
        if redivide['revised_value'] != head:
            fail('t039 76 %s: unexpected revised value on the redivide record' % field)

        redivide['reason'] = REASON_76
        redivide['moved_to'] = {'line': 77, 'token': moved}
        redivide['verification_source'] = PAGE_SOURCE

        seventy_seven['revised_value'] = rebuilt
        seventy_seven['reason'] = REASON_77
        seventy_seven['moved_from'] = {'line': 76, 'token': moved}
        seventy_seven['verification_source'] = PAGE_SOURCE
        seventy_seven.pop('equals_line', None)
        seventy_seven['differs_from_line_80_by'] = (
            'a comma between the two vocatives, which the printed page sets on '
            'this line and not on line 80')

    CORRECTIONS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8')
    print('corrections: %d records, t039 line 77 amended in place'
          % len(data['corrections']))

    # The literal assertion follows the printed page.
    replace_once(
        INTEGRITY,
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 77, 'miluk_ascii',\n"
        '     "t#@-\'n@hi:<me t#@-\'n@hi:<me!"),\n',
        "    ('t039-black-bear-and-pack-basket-bear-grizzly', 77, 'miluk_ascii',\n"
        '     "t#@-\'n@hi:<me, t#@-\'n@hi:<me!"),\n')

    # With the comma carried across rather than stripped, no punctuation moves
    # at all, so check 7 no longer needs to forgive any and can compare the
    # tokens exactly. A stricter check for a smaller reason to be lenient.
    replace_once(
        INTEGRITY,
        "#    lines must still be the words the documentary record held across the\n"
        "#    same two lines. Sentence punctuation is allowed to move to the new end\n"
        "#    of a line, so it is stripped before comparing; nothing else is.\n",
        "#    lines must still be exactly the tokens the documentary record held\n"
        "#    across the same two lines -- punctuation included. An earlier draft\n"
        "#    stripped commas before comparing, to let a moved vocative shed the\n"
        "#    comma it was carrying. The printed 1990 page shows the comma belongs\n"
        "#    where the word goes, so nothing needs forgiving and nothing is.\n")
    replace_once(
        INTEGRITY,
        "            now += [w.strip(',.') for w in (line.get(field) or '').split()]\n"
        "            before += [w.strip(',.') for w in\n"
        "                       (documentary.get(field, line.get(field)) or '').split()]\n",
        "            now += (line.get(field) or '').split()\n"
        "            before += (documentary.get(field, line.get(field)) or '').split()\n")
    replace_once(
        INTEGRITY,
        "            fails.append('%s lines %d-%d: %s words changed across the pair'\n",
        "            fails.append('%s lines %d-%d: %s tokens changed across the pair'\n")
    print('%s: line 77 literal updated, check 7 made exact' % INTEGRITY)

    marker = "      '3d7ff81ae29fd3c7cc1d38d0eef5f8c46db81e76a74840831d7f49c2fac7a684',\n"
    anchor = ('#   2f7e96984f310cbca603862260a7fd2a954c883f8de621c3d2a3dfc92675988e\n'
              '#       t039 line 76, before the line-division repair\n')
    replace_once(SITE, anchor, anchor +
                 '#   3d7ff81ae29fd3c7cc1d38d0eef5f8c46db81e76a74840831d7f49c2fac7a684\n'
                 '#       the line-division repair, before the printed page restored\n'
                 '#       the comma on line 77\n')
    replace_once(SITE, marker, "      'CORPUS_SHA_PLACEHOLDER',\n")
    print('%s: pin comment extended, new pin left as a placeholder' % SITE)


if __name__ == '__main__':
    main()
