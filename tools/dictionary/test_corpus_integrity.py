#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Field-integrity checks on the published corpus.

    python3 tools/dictionary/test_corpus_integrity.py

These are guardrails against a specific failure the restoration has already had
once: a repair pass that decides a line's Miluk and English fields are the wrong
way round, and swaps a line that was not broken.

The failure is not hypothetical and it was not loud. Two lines
(t055 line 219 and t039 line 86) went through the v2 field-orientation repair
with their English prose written into `miluk_ascii`, and the transliteration
stage then ran over that English and produced Miluk-looking output from it —
"very" rendered as "ᵉry", "where are" as "whɛrɛ arɛ". Nothing in the build
objected. The corrected lines are asserted by name below, and the general
conditions that would have caught them are asserted for the whole corpus.
"""
import json
import re
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parents[1]
DATA = REPO_ROOT / 'dictionary' / 'data'
PROV = TOOL_DIR / 'provenance'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


CORPUS = load(DATA / 'corpus.json')
NOTEBOOK = load(PROV / 'notebook-collation-corrections.json')
LINES = {(s['story_id'], l['line']): l for s in CORPUS['stories'] for l in s['lines']}

# Jacobs' ASCII transcription uses these as ordinary symbols; running English
# does not.
TRANSCRIPTION_MARKS = set('<@#;&%')

COMMON_ENGLISH = set("""
a an the and of to in on at is was were be it they them his her their that this you your we our my me him he she
not no so with for from oh very well nephew uncle aunt now then all come came go went said say says people man
woman child children good bad here there what who why how when where are your dog take hold old just only
""".split())

# t051 line 99 carries Word Cruncher concordance debris inside its Miluk field
# ("+ 1p100 why do you not take hold of your dog? +"). It arrived that way from
# the source export — it has no transformation ids — so it is a documented
# exception rather than a regression. Remove this entry when that line is
# repaired; the test will then hold the corpus to the stricter rule.
RUNNING_ENGLISH_EXCEPTIONS = {
    ('t051-that-whittles-his-penis-old-man-or-the-five-', 99):
        'source-borne concordance debris; not a restoration regression',
}


def english_fraction(text):
    words = [re.sub(r"[^a-z']", '', w.lower()) for w in (text or '').split()]
    words = [w for w in words if len(w) > 1]
    return (sum(1 for w in words if w in COMMON_ENGLISH) / len(words)) if words else 0.0


def reads_as_running_english(text):
    words = [w for w in (text or '').split() if re.search(r'[A-Za-z]', w)]
    return len([w for w in words if len(w) > 1]) >= 3 and english_fraction(text) >= 0.40


fails = []

# 1. No line's Miluk may read as running English. This is the condition that the
#    two known regressions violate and that nothing else in the corpus does.
for (story_id, number), line in sorted(LINES.items()):
    if reads_as_running_english(line.get('miluk_ascii')):
        if (story_id, number) in RUNNING_ENGLISH_EXCEPTIONS:
            continue
        fails.append('%s line %d: miluk_ascii reads as running English: %r'
                     % (story_id, number, line.get('miluk_ascii')[:70]))

# 2. Nor may a line's English read as ASCII transcription.
for (story_id, number), line in sorted(LINES.items()):
    words = [w for w in (line.get('english') or '').split() if re.search(r'[A-Za-z]', w)]
    if not words:
        continue
    marked = sum(1 for w in words if any(c in TRANSCRIPTION_MARKS for c in w))
    if marked / len(words) >= 0.6 and english_fraction(line.get('english')) < 0.2:
        fails.append('%s line %d: english reads as ASCII transcription: %r'
                     % (story_id, number, line.get('english')[:70]))

# 3. No field may carry a long run of one repeated character. A 512-character
#    run of U+00D2 sat inside one English field before this check existed, and
#    an earlier draft of this test missed it by exempting alphanumerics — U+00D2
#    is a letter. With that run removed the corpus contains no run of six or
#    more identical characters in any field at all, in any script, so the rule
#    needs no exemptions and is stated without them.
RUN = re.compile(r'(.)\1{5,}')
for (story_id, number), line in sorted(LINES.items()):
    for field in ('english', 'miluk', 'miluk_ascii'):
        match = RUN.search(line.get(field) or '')
        if match:
            fails.append('%s line %d: %s carries a run of %d %r characters'
                         % (story_id, number, field,
                            len(match.group(0)), match.group(1)))

# 4. Every notebook-collation correction is applied, and the last record
#    touching a field is the value that field now carries. A field can
#    carry more than one record -- t039 line 76 is reverted to its
#    documentary value and then redivided -- so asserting every record's
#    revised_value would fail on the earlier one. test_site.py already
#    checks the last correction per field for the same reason.
LAST_RECORD = {}
for item in NOTEBOOK['corrections']:
    target = item['target']
    LAST_RECORD[(target['story_id'], target['line'], target['field'])] = item
for item in NOTEBOOK['corrections']:
    target = item['target']
    line = LINES.get((target['story_id'], target['line']))
    if line is None:
        fails.append('%s: target line is missing from the corpus' % item['correction_id'])
        continue
    key = (target['story_id'], target['line'], target['field'])
    if LAST_RECORD[key] is item and line.get(target['field']) != item['revised_value']:
        fails.append('%s: %s is not the revised value'
                     % (item['correction_id'], target['field']))
    if item['correction_id'] not in (line.get('transformation_ids') or []):
        fails.append('%s: correction id absent from the line transformation_ids'
                     % item['correction_id'])

# 5. Named regressions, asserted literally so that a future repair pass cannot
#    quietly reintroduce them.
REGRESSIONS = [
    ('t055-the-trickster-person-who-made-the-country', 219, 'miluk_ascii', 'h@:<::u, de<u.'),
    ('t055-the-trickster-person-who-made-the-country', 219, 'english', 'H@@/@@u (oh very well), nephew.'),
    ('t039-black-bear-and-pack-basket-bear-grizzly', 86, 'miluk_ascii', 'h@:<:::u idja<u-is'),
    ('t039-black-bear-and-pack-basket-bear-grizzly', 86, 'english', 'H@@@@@u where are you?'),
    ('t055-the-trickster-person-who-made-the-country', 1251, 'english', 'And they laid sitting mats.'),
    # t039 line 76 is the third line the v2 orientation repair mishandled,
    # and the only one whose documentary record was itself wrong: its
    # English field held a degraded ASCII duplicate of the cry rather than
    # English, so the repair had nothing correct to swap towards and
    # rotated the good transcription out of miluk_ascii instead. Restoring
    # it recovered the vocative t#@-'n@hi:<me, which no visible field
    # carried after v2. That vocative then moved to line 77, where the
    # edition's own English for it already stood, so 76 and 77 are
    # asserted together: the boundary between them is the repair. Line
    # 77 must equal line 80, which carries the same English against the
    # same two vocatives. The English on 76 is an editorial rendering of
    # untranslated vocables, not a Jacobs gloss. Rendered Miluk is not
    # asserted literally here, because writing it into this file would
    # mean transcribing it by hand -- check 4 holds it against the
    # correction record, which derives it from the repository.
    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'miluk_ascii',
     "h@'@:<:: he:<:. h@:<:h@h@::"),
    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 'english',
     "Huh-'uhhh, hehhh. Huhhh-huh-huhhh,"),
    ('t039-black-bear-and-pack-basket-bear-grizzly', 77, 'miluk_ascii',
     "t#@-'n@hi:<me t#@-'n@hi:<me!"),
    # t055 1308's English glossed the following notebook page, typo and
    # all ('thyes' for 'their eyes'). Its entries are still the 1990
    # dictionary's own citations for 'day' and 'five', which belong to
    # that same wrong gloss; check 8 is why they cannot be cut here.
    ('t055-the-trickster-person-who-made-the-country', 1308, 'english',
     "Now he took out the snail-shell eyes."),
]
# A rule was drafted here and withdrawn: "no Miluk field may contain
# U+002F", on the theory that the slashes in this line's v2 output were
# Word Cruncher damage. Run against the corpus it failed on eight lines of
# t003 and t004 where the slash is ordinary Jacobs notation inside a word
# (tsu<-ts#i<ntsim-d@/k!a). The slash is only damage in the company it
# keeps on t039 line 76, which the assertions above already cover.
for story_id, number, field, expected in REGRESSIONS:
    line = LINES.get((story_id, number))
    if line is None or line.get(field) != expected:
        fails.append('%s line %d: %s is not %r' % (story_id, number, field, expected))

# 6. No line's visible English may be identical to the Miluk that the
#    line's own documentary record preserves. That is the exact signature
#    of a field-orientation repair that moved rendered Miluk into the
#    English column, and it is the only general rule here that catches
#    t039 line 76: checks 1 and 2 both pass on that defect, because the
#    value sitting in its English field was rendered Miluk rather than
#    ASCII transcription and so carried none of the marks check 2 looks
#    for. Run against the corpus as it stood before that correction, this
#    fires on line 76 and on nothing else; after it, on nothing.
for (story_id, number), line in sorted(LINES.items()):
    documentary_miluk = (line.get('documentary_original_fields') or {}).get('miluk')
    if documentary_miluk and line.get('english') == documentary_miluk:
        fails.append('%s line %d: english is verbatim the documentary miluk: %r'
                     % (story_id, number, documentary_miluk[:70]))

# 7. A line-division repair moves words between two adjacent lines; it must
#    never add or drop one. For each repaired pair the words across the two
#    lines must still be the words the documentary record held across the
#    same two lines. Sentence punctuation is allowed to move to the new end
#    of a line, so it is stripped before comparing; nothing else is.
REDIVIDED_PAIRS = [
    ('t039-black-bear-and-pack-basket-bear-grizzly', 76, 77),
]
for story_id, first, second in REDIVIDED_PAIRS:
    for field in ('miluk', 'miluk_ascii'):
        now, before = [], []
        for number in (first, second):
            line = LINES.get((story_id, number))
            if line is None:
                continue
            documentary = (line.get('documentary_original_fields') or {})
            now += [w.strip(',.') for w in (line.get(field) or '').split()]
            before += [w.strip(',.') for w in
                       (documentary.get(field, line.get(field)) or '').split()]
        if sorted(now) != sorted(before):
            fails.append('%s lines %d-%d: %s words changed across the pair'
                         % (story_id, first, second, field))

# 8. Every corpus line's `entries` must be exactly the set of dictionary
#    entries attested on that line, and the reverse. The two are one link
#    set stored twice, and they agree on all 7,149 lines today. Nothing
#    checked that before, which is what makes a half-repair possible:
#    moving a word between two lines, or cutting a wrong entry link,
#    fixes the corpus side and leaves dictionary.json pointing at a line
#    that no longer holds the word. This is why t055 1220/1221 (#14) and
#    the entries half of t055 1308 (#15) are not in this pass: they need
#    a dictionary-side correction stage, which does not exist yet.
DICTIONARY = load(DATA / 'dictionary.json')
attested = {}
for entry in DICTIONARY['entries']:
    for attestation in entry.get('attestations') or []:
        story_id = attestation.get('story_id')
        number = attestation.get('line')
        if story_id is None or number is None:
            continue
        attested.setdefault((story_id, number), set()).add(entry['entry_id'])
for (story_id, number), line in sorted(LINES.items()):
    here = set(line.get('entries') or [])
    there = attested.get((story_id, number), set())
    if here != there:
        fails.append('%s line %d: entries %s but dictionary attests %s'
                     % (story_id, number, sorted(here), sorted(there)))

print('corpus records         :', CORPUS['story_count'])
print('corpus lines           :', CORPUS['line_count'])
print('notebook corrections   :', len(NOTEBOOK['corrections']))
print('running-English exempt :', len(RUNNING_ENGLISH_EXCEPTIONS))
if fails:
    print('\nFAILURES: %d' % len(fails))
    for failure in fails[:50]:
        print('  -', failure)
    sys.exit(1)
print('ALL CHECKS PASS')
