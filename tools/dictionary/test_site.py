# -*- coding: utf-8 -*-
"""Build verification for miluk.org/dictionary/. Fails loudly; ships only green."""
import json, os, re, sys, html, collections
OUT = '/home/claude/site-repo/dictionary'
SRC = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(SRC, 'corpus.json')))
D = json.load(open(os.path.join(SRC, 'dictionary.json')))
fails = []
def check(cond, msg):
    if not cond: fails.append(msg)

# 1. every entry and every populated story has a page
for e in D['entries']:
    check(os.path.exists(os.path.join(OUT, 'words', e['entry_id'] + '.html')),
          'missing entry page: ' + e['entry_id'])
SLIP = re.compile(r'-(f\d+|slipfile|slip-file|jacobs-slip)', re.I)
live = [s for s in C['stories'] if s['lines'] and not SLIP.search(s['story_id'])]
for s in live:
    check(os.path.exists(os.path.join(OUT, 'stories', s['story_id'] + '.html')),
          'missing story page: ' + s['story_id'])

# 2. every internal href/src resolves to a real file; every #lN anchor exists in its target
pages = []
for root, _, fs in os.walk(OUT):
    for f in fs:
        if f.endswith('.html'): pages.append(os.path.join(root, f))
HREF = re.compile(r'(?:href|src)="([^"#]*)(#[^"]*)?"')
anchor_cache = {}
def anchors_of(path):
    if path not in anchor_cache:
        t = open(path, encoding='utf-8').read()
        anchor_cache[path] = set(re.findall(r'id="([^"]+)"', t))
    return anchor_cache[path]
nlinks = 0
for p in pages:
    t = open(p, encoding='utf-8').read()
    base = os.path.dirname(p)
    for m in HREF.finditer(t):
        url, frag = m.group(1), m.group(2)
        if url.startswith(('http', 'mailto:', 'data:')): continue
        nlinks += 1
        if url == '':
            tgt = p
        else:
            tgt = os.path.normpath(os.path.join(base, url))
            if url.endswith('/'): tgt = os.path.join(tgt, 'index.html')
        if tgt.startswith(os.path.normpath(os.path.join(OUT, '..'))) and not tgt.startswith(OUT):
            continue  # links up into the main site — checked separately
        check(os.path.exists(tgt), 'broken link in %s -> %s' % (os.path.relpath(p, OUT), url))
        if frag and frag != '#' and os.path.exists(tgt) and tgt.endswith('.html'):
            check(frag[1:] in anchors_of(tgt),
                  'broken anchor in %s -> %s%s' % (os.path.relpath(p, OUT), url, frag))

# 3. every entry page shows its headword; every displayed attestation contains a <b>
for e in D['entries']:
    t = open(os.path.join(OUT, 'words', e['entry_id'] + '.html'), encoding='utf-8').read()
    check(html.escape(e['headword']) in t, 'headword missing on its page: ' + e['entry_id'])
    atts = re.findall(r'<div class="att"><p class="m">(.*?)</p>', t, re.S)
    for a in atts:
        # examples (from the |p blocks) have no bolding; corpus attestations must
        pass
    corpus_atts = [a for a in atts if '<b>' in a or True]
# stricter: any att block that carries a src link into stories must contain a <b>
for e in D['entries']:
    t = open(os.path.join(OUT, 'words', e['entry_id'] + '.html'), encoding='utf-8').read()
    for blk in re.findall(r'<div class="att">(.*?)</div>', t, re.S):
        if 'stories/' in blk:
            check('<b>' in blk, 'attestation without bolded form on ' + e['entry_id'])

# 4. story pages: line count matches the data; every line anchor present
for s in live:
    t = open(os.path.join(OUT, 'stories', s['story_id'] + '.html'), encoding='utf-8').read()
    n = len(re.findall(r'<div class="line" id="l\d+">', t))
    check(n == s['line_count'], 'line count mismatch %s: %d vs %d' % (s['story_id'], n, s['line_count']))

# 5. search index integrity
idx = json.load(open(os.path.join(OUT, 'search-index.json')))
check(len(idx['entries']) == len(D['entries']), 'search index entry count')
check(len(idx['stories']) == len(live), 'search index story count')
ids = {e['entry_id'] for e in D['entries']}
for r in idx['entries']:
    check(r['i'] in ids, 'search index unknown id ' + r['i'])

# 6. no entry page links into an excluded (slip) story
import glob
for pg in glob.glob(os.path.join(OUT,'words','*.html')):
    t = open(pg, encoding='utf-8').read()
    for m in re.finditer(r'href="\.\./stories/([^".]+)\.html', t):
        check(not SLIP.search(m.group(1)), 'entry links into excluded slip story: %s in %s' % (m.group(1), os.path.basename(pg)))

# 7. spot content: a known corrected line renders corrected
t = open(os.path.join(OUT, 'stories', 't003-a-deserted-poor-woman-was-given-food-by-shag.html'), encoding='utf-8').read()
check('hú·mis' in t, 'Jacobs correction (hú·mis) not present in story 1')

print('links checked :', nlinks)
print('pages checked :', len(pages))
if fails:
    print('\nFAILURES: %d' % len(fails))
    for f in fails[:30]: print('  -', f)
    sys.exit(1)
print('ALL CHECKS PASS')
