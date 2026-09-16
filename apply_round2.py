#!/usr/bin/env python3
"""One-shot applier: second round of the 2026 notebook collation, t039 line 76.

Run once from the repository root:

    python3 apply_round2.py

Then rebuild the corpus and the site as usual. This file is deleted in the same
commit; it is a transport device, not part of the build.

Why it exists. The values this correction needs are non-ASCII -- combining
marks, schwa, barred l, the raised interpunct. Retyping those through a tool
call is exactly how a restoration corrupts itself: escapes arrive decoded,
combining sequences arrive normalised, and the result still looks right. So
nothing non-ASCII is typed here. Every non-ASCII value is read out of
provenance/v2-effective-diff.json, the repository's own receipt for what commit
dc186a2 did to this line, and a revert is defined as the inverse of the
recorded correction rather than as a string somebody transcribed.

The only new text in this file is the English rendering, which is ASCII by
construction: the line has no English gloss in any source, and this is an
editorial rendering of untranslated vocables in English orthography.
"""
import json
import sys
from pathlib import Path

TOOL = Path('tools/dictionary')
CORRECTIONS = TOOL / 'provenance' / 'notebook-collation-corrections.json'
V2_RECEIPT = TOOL / 'provenance' / 'v2-effective-diff.json'
INTEGRITY = TOOL / 'test_corpus_integrity.py'
SITE = TOOL / 'test_site.py'

STORY = 't039-black-bear-and-pack-basket-bear-grizzly'
LINE = 76
ISSUE = 18
SOURCE = ("Melville Jacobs Notebook 99 p. 37; the line's own "
          'documentary_original_fields')
ENGLISH_RENDERING = "Huh-'uhhh, hehhh. Huhhh-huh-huhhh,"

REASONS = {
    'miluk_ascii':
        "the v2 field-orientation repair moved this line's correct ASCII "
        'transcription out of the field and left a degraded duplicate of the '
        "cry in its place; the vocative t#@-'n@hi:<me, was lost with it and "
        'survived in no visible field. Notebook 99 p. 37 carries the full '
        'reading',
    'miluk':
        'the transliteration stage then ran over that degraded duplicate and '
        "produced Miluk-looking output from it, carrying the duplicate's "
        'U+002F characters into the rendered form',
    'english':
        "this line is the mother's cry on finding she has eaten her own child, "
        'and it has no English gloss in any source: Jacobs wrote the vocables '
        'down and began glossing one word later, at the vocative. The '
        'documentary English field held a degraded ASCII duplicate of the cry '
        'rather than English, so unlike the other reverts in this file there '
        'is no documentary English to restore, and the v2 repair left rendered '
        'Miluk sitting in the English column. The vocables are rendered in '
        'English orthography, unit for unit against the transcription: '
        "h@'@:<:: -> Huh-'uhhh, he:<:. -> hehhh., h@:<:h@h@:: -> "
        'Huhhh-huh-huhhh',
}

SUPERSESSION_NOTE = (
    ' The three t039 line 76 records added in the second round supersede v2 '
    'corrections in the same way, but only two of them restore a documentary '
    'value; the English field held no English in the documentary record '
    'either, and its record says so explicitly.'
)

INTEGRITY_REGRESSIONS_ANCHOR = (
    "    ('t055-the-trickster-person-who-made-the-country', 1251, 'english', "
    "'And they laid sitting mats.'),\n]\n"
)

INTEGRITY_REGRESSIONS_NEW = (
    "    ('t055-the-trickster-person-who-made-the-country', 1251, 'english', "
    "'And they laid sitting mats.'),\n"
    '    # t039 line 76 is the third line the v2 orientation repair mishandled,\n'
    '    # and the only one whose documentary record was itself wrong: its\n'
    '    # English field held a degraded ASCII duplicate of the cry rather than\n'
    '    # English, so the repair had nothing correct to swap towards and\n'
    '    # rotated the good transcription out of miluk_ascii instead. Restoring\n'
    "    # it recovers the vocative t#@-'n@hi:<me, which no visible field\n"
    '    # carried after v2. The English is an editorial rendering of\n'
    '    # untranslated vocables, not a Jacobs gloss; the correction record\n'
    '    # carries the unit-for-unit mapping. The rendered Miluk is not\n'
    '    # asserted literally here, because writing it into this file would\n'
    '    # mean transcribing it by hand -- check 4 holds it against the\n'
    '    # correction record, which derives it from the v2 receipt.\n'
    "    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'miluk_ascii',\n"
    '     "h@\'@:<:: he:<:. h@:<:h@h@:: t#@-\'n@hi:<me,"),\n'
    "    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'english',\n"
    '     "Huh-\'uhhh, hehhh. Huhhh-huh-huhhh,"),\n'
    ']\n'
    '# A rule was drafted here and withdrawn: "no Miluk field may contain\n'
    "# U+002F\", on the theory that the slashes in this line's v2 output were\n"
    '# Word Cruncher damage. Run against the corpus it failed on eight lines of\n'
    '# t003 and t004 where the slash is ordinary Jacobs notation inside a word\n'
    '# (tsu<-ts#i<ntsim-d@/k!a). The slash is only damage in the company it\n'
    '# keeps on t039 line 76, which the assertions above already cover.\n'
)

INTEGRITY_CHECK6_ANCHOR = (
    "for story_id, number, field, expected in REGRESSIONS:\n"
    "    line = LINES.get((story_id, number))\n"
    "    if line is None or line.get(field) != expected:\n"
    "        fails.append('%s line %d: %s is not %r' % (story_id, number, field, expected))\n"
)

INTEGRITY_CHECK6_NEW = INTEGRITY_CHECK6_ANCHOR + (
    "\n"
    "# 6. No line's visible English may be identical to the Miluk that the\n"
    "#    line's own documentary record preserves. That is the exact signature\n"
    '#    of a field-orientation repair that moved rendered Miluk into the\n'
    '#    English column, and it is the only general rule here that catches\n'
    '#    t039 line 76: checks 1 and 2 both pass on that defect, because the\n'
    '#    value sitting in its English field was rendered Miluk rather than\n'
    '#    ASCII transcription and so carried none of the marks check 2 looks\n'
    '#    for. Run against the corpus as it stood before that correction, this\n'
    '#    fires on line 76 and on nothing else; after it, on nothing.\n'
    'for (story_id, number), line in sorted(LINES.items()):\n'
    "    documentary_miluk = (line.get('documentary_original_fields') or {}).get('miluk')\n"
    "    if documentary_miluk and line.get('english') == documentary_miluk:\n"
    "        fails.append('%s line %d: english is verbatim the documentary miluk: %r'\n"
    '                     % (story_id, number, documentary_miluk[:70]))\n'
)

SITE_ANCHOR = (
    '# Pinned so the published corpus cannot change without a deliberate, reviewed\n'
    '# update to this line. Previous pin, before the 2026 notebook collation:\n'
    '#\n'
    "check(hashlib.sha256((DATA / 'corpus.json').read_bytes()).hexdigest() ==\n"
    "      'f6d0f1412c4647299d0dc845431754313f7f235a9718fc6981b3ac1d361df725',\n"
    "      'public corpus bytes changed')\n"
)

SITE_NEW = (
    '# Pinned so the published corpus cannot change without a deliberate, reviewed\n'
    '# update to this line. Superseded pins, most recent last:\n'
    '#\n'
    '#   0183a6305d0dc0a9737cad10eebaf47cd881ba12575f4cb47702fd3b0001f854\n'
    '#       before the 2026 notebook collation (PR #17)\n'
    '#   f6d0f1412c4647299d0dc845431754313f7f235a9718fc6981b3ac1d361df725\n'
    "#       the collation's first three lines: t055 219, t039 86, t055 1251\n"
    '#\n'
    '# The first of those was dropped from this comment when PR #17 rebuilt the\n'
    '# file through CI; it is restored here from the base branch.\n'
    "check(hashlib.sha256((DATA / 'corpus.json').read_bytes()).hexdigest() ==\n"
    "      'CORPUS_SHA_PLACEHOLDER',\n"
    "      'public corpus bytes changed')\n"
)


def fail(message):
    sys.exit('apply_round2: ' + message)


def replace_once(path, old, new):
    text = path.read_text(encoding='utf-8')
    if text.count(old) != 1:
        fail('%s: anchor matches %d times, expected exactly 1'
             % (path, text.count(old)))
    path.write_text(text.replace(old, new), encoding='utf-8')


def main():
    v2 = {item['correction_id']: item
          for item in json.loads(V2_RECEIPT.read_text(encoding='utf-8'))['corrections']}

    data = json.loads(CORRECTIONS.read_text(encoding='utf-8'))
    existing = {item['correction_id'] for item in data['corrections']}

    for field in ('miluk_ascii', 'miluk', 'english'):
        slug = field.replace('_', '-')
        v2_id = 'v2-corpus-t039-l0076-%s' % slug
        if v2_id not in v2:
            fail('%s is not in the v2 receipt' % v2_id)
        source = v2[v2_id]
        if source['target']['story_id'] != STORY or source['target']['line'] != LINE:
            fail('%s does not target %s line %d' % (v2_id, STORY, LINE))

        record = {
            'correction_id': 'nbc-corpus-t039-l0076-%s' % slug,
            'target': {'source': 'corpus', 'story_id': STORY,
                       'line': LINE, 'field': field},
            # What v2 wrote is what this stage finds in the field now.
            'original_value': source['revised_value'],
            # A revert restores what v2 replaced. The English field has no
            # documentary English to restore, so it takes the rendering.
            'revised_value': (ENGLISH_RENDERING if field == 'english'
                              else source['original_value']),
            'disposition': 'changed',
            'change_kind': ('render-untranslated-vocables' if field == 'english'
                            else 'revert-field-unswap'),
            'reason': REASONS[field],
            'verification_source': SOURCE,
            'affects': 'restoration-corpus',
            'restoration_stage': '2026 notebook collation',
            'reverts': [v2_id],
        }
        if field == 'english':
            record['supersedes_without_restoring_documentary_value'] = True
            record['considered_alternative'] = {
                'value': ENGLISH_RENDERING + ' my children,',
                'basis': "Jacobs' interlinear gloss on Notebook 99 p. 37 "
                         'reads "my children  my children  its hand" '
                         "beneath t#@n@hi:<me t#@n@hi:<me t#@d@k'&i<#an, so "
                         'his own gloss does cover the vocative that closes '
                         'this line',
                'rejected_because': 'the 1990 edition divides those words '
                                    'across lines 76 and 77 and glosses them '
                                    'at 77; repeating the gloss at 76 would '
                                    'change the published line division. '
                                    'Directed by Troy, 2026-09-16',
            }
        record['github_issue'] = ISSUE

        if record['correction_id'] in existing:
            fail('%s is already present' % record['correction_id'])
        data['corrections'].append(record)

    data['note_on_supersession'] = data['note_on_supersession'] + SUPERSESSION_NOTE
    data['summary']['records'] = len(data['corrections'])
    data['summary']['lines_affected'] = len(
        {(i['target']['story_id'], i['target']['line']) for i in data['corrections']})
    data['summary']['reverted_transformations'] = sorted(
        {r for i in data['corrections'] for r in i.get('reverts', [])})
    CORRECTIONS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8')
    print('corrections: %d records over %d lines'
          % (data['summary']['records'], data['summary']['lines_affected']))

    replace_once(INTEGRITY, INTEGRITY_REGRESSIONS_ANCHOR, INTEGRITY_REGRESSIONS_NEW)
    replace_once(INTEGRITY, INTEGRITY_CHECK6_ANCHOR, INTEGRITY_CHECK6_NEW)
    print('%s: regressions extended, guardrail 6 added' % INTEGRITY)

    replace_once(SITE, SITE_ANCHOR, SITE_NEW)
    print('%s: pin comment rewritten, new pin left as a placeholder' % SITE)


if __name__ == '__main__':
    main()
