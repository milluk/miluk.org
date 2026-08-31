# -*- coding: utf-8 -*-
"""miluk.org /dictionary/ — static site generator.
Reads corpus.json + dictionary.json (the 1990 dictionary, restored 2026)
and emits the dictionary sub-site. Everything is generated; nothing hand-edited."""
import argparse, json, os, re, html, unicodedata, collections, sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parents[1]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data', type=Path, default=REPO_ROOT / 'dictionary' / 'data',
                    help='input directory containing corpus.json and dictionary.json')
parser.add_argument('--out', type=Path, default=REPO_ROOT / 'dictionary',
                    help='generated dictionary site directory')
args = parser.parse_args()
DATA = args.data.resolve()
OUT = args.out.resolve()
PIPELINE = TOOL_DIR / 'pipeline'
sys.path.insert(0, str(PIPELINE))
from build_complete_dictionary import build as build_complete_dictionary
from anderson import convert as convert_1990
from jacobs_alphabet import ORDER as JACOBS_ORDER, category as jacobs_category, initial_for_entry

# dictionary.json is generated data. Rebuild it from the frozen D-Z checkpoint
# and the byte-preserved A-C tables before rendering the site.
if DATA == (REPO_ROOT / 'dictionary' / 'data').resolve():
    rebuilt, recovered_records = build_complete_dictionary(
        TOOL_DIR / 'archive' / 'restoration-checkpoint' / 'dictionary-dz-1111.json',
        TOOL_DIR / 'archive' / '1990-abc')
    dictionary_bytes = (json.dumps(rebuilt, ensure_ascii=False, indent=1) + '\n').encode()
    dictionary_path = DATA / 'dictionary.json'
    if not dictionary_path.exists() or dictionary_path.read_bytes() != dictionary_bytes:
        dictionary_path.write_bytes(dictionary_bytes)
    receipt = {'schema': 'miluk-1990-recovered-records/1',
               'record_count': len(recovered_records), 'records': recovered_records}
    receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=1) + '\n').encode()
    receipt_path = TOOL_DIR / 'provenance' / 'recovered-records.json'
    if not receipt_path.exists() or receipt_path.read_bytes() != receipt_bytes:
        receipt_path.write_bytes(receipt_bytes)
C = json.loads((DATA / 'corpus.json').read_text(encoding='utf-8'))
D = json.loads((DATA / 'dictionary.json').read_text(encoding='utf-8'))
ENTRIES = D['entries']; STORIES = C['stories']

# ---------------- fold (identical in app.js) ----------------
SUP = str.maketrans({'ⁱ':'i','ᵘ':'u','ʷ':'w','ᵃ':'a','ᵉ':'e','ⁿ':'n','ʸ':'y','ʰ':None,'ʻ':None})
FOLD = {'ɛ':'e','ə':'e','ɢ':'g','ƚ':'l','ł':'l','ɣ':'g','ʒ':'z','ʃ':'s','š':'s','ǯ':'j',
        'ŋ':'n','ɪ':'i','ʊ':'u','ð':'d','ɴ':'n','ʟ':'l','ᴍ':'m'}
def fold(s):
    s = unicodedata.normalize('NFC', s)
    s = s.replace('č', 'tc').replace('ǯ', 'dj').replace('ʒ', 'j')
    s = s.translate(SUP)
    d = unicodedata.normalize('NFD', s)
    d = ''.join(c for c in d if not unicodedata.combining(c))
    d = d.replace('ƛ', 'tl')
    d = ''.join(FOLD.get(c, c) for c in d.lower())
    return re.sub(r'[^a-z0-9]', '', d)

def E(s): return html.escape(s or '', quote=True)

# ---------------- prepared lookups ----------------
by_id = {e['entry_id']: e for e in ENTRIES}
story_by_id = {s['story_id']: s for s in STORIES}
line_by = {}
for s in STORIES:
    for l in s['lines']:
        line_by[(s['story_id'], l['line'])] = l

# forms per entry, folded, longest first (linkable if len>=3)
entry_keys = {}
for e in ENTRIES:
    ks = sorted({fold(f['form']) for f in e['forms'] if len(fold(f['form'])) >= 2},
                key=len, reverse=True)
    entry_keys[e['entry_id']] = ks

live = [s for s in STORIES if s.get('source', {}).get('layer') == 'uwpa-recovered-record']
live_ids = {s['story_id'] for s in live}
HOM = re.compile(r'[¹²³⁴⁵]+$')
def plain_hw(e): return HOM.sub('', e['headword'])

# ---------------- public cross-reference display ----------------
# Archival fields retain Anderson's 1990 ASCII. Only their public rendering is
# converted here, and links are emitted only for a unique dictionary target.
ASCII_NOTATION = re.compile(r"[<@#;!&$%`0/]|:")

def ascii_reference_fold(value):
    value = value.lower()
    value = re.sub(r"[<:;!&$'`0/]", '', value)
    value = value.replace('#', 'l').replace('@', 'e').replace('%', 'g')
    value = re.sub(r'v(?=[a-z])', '', value)
    return re.sub(r'[^a-z0-9]', '', value)

def reference_targets(value):
    target_fold = ascii_reference_fold(value)
    if len(target_fold) < 3:
        return []
    matches = []
    for candidate in ENTRIES:
        if fold(plain_hw(candidate)) == target_fold:
            matches.append(candidate)
    for candidate in ENTRIES:
        if (candidate not in matches and
                any(fold(form['form']) == target_fold for form in candidate['forms'])):
            matches.append(candidate)
    return matches

def converted_reference(value):
    return convert_1990(value) if ASCII_NOTATION.search(value) else value

def gloss_reference(value):
    match = re.search(r"\bsee(?: reference under)?\s+(\S+)$", value, re.I)
    if not match or not ASCII_NOTATION.search(match.group(1)):
        return None
    return match, match.group(1)

def public_gloss_text(value):
    """Convert only a terminal 1990 see-target for plain-text public surfaces."""
    found = gloss_reference(value)
    if not found:
        return value
    match, raw_target = found
    return value[:match.start(1)] + converted_reference(raw_target)

def public_gloss(value):
    """Escape a gloss and link a converted terminal target only if unique."""
    found = gloss_reference(value)
    if not found:
        return E(value)
    match, raw_target = found
    label = E(converted_reference(raw_target))
    targets = reference_targets(raw_target)
    if len(targets) == 1:
        label = '<a href="%s.html">%s</a>' % (targets[0]['entry_id'], label)
    return E(value[:match.start(1)]) + label

# ---------------- word-level linking ----------------
PUNCT = '.,;:?!"«»“”‘’()[]'
def link_line(miluk, cands, root, self_id=None):
    """Render a Miluk line with each recognizable piece linked to its entry.
       If self_id is set, that entry's pieces are bolded instead of linked."""
    out = []
    for tok in miluk.split(' '):
        if not tok:
            out.append(''); continue
        lead = tok[:len(tok)-len(tok.lstrip(PUNCT))]
        core = tok.strip(PUNCT)
        trail = tok[len(lead)+len(core):]
        pieces = core.split('-') if core else []
        rend = []
        for pc in pieces:
            pf = fold(pc)
            def hits(eid):
                best = 0
                for k in entry_keys.get(eid, ()):
                    if k == pf or (len(k) >= 3 and len(pf) >= 3 and (k in pf or pf in k)):
                        best = max(best, len(k))
                return best
            def self_hits():
                # self-bolding is looser: the cited form may sit inside a larger piece
                for k in entry_keys.get(self_id, ()):
                    if k == pf or k in pf or (len(k) >= 3 and len(pf) >= 3 and pf in k):
                        return True
                return False
            # the entry being displayed gets first claim on its own pieces
            if self_id is not None and self_hits():
                rend.append('<b>%s</b>' % E(pc)); continue
            best, bestlen = None, 0
            for eid in cands:
                if eid == self_id: continue
                h = hits(eid)
                if h > bestlen: best, bestlen = eid, h
            if best is None:
                rend.append(E(pc))
            else:
                rend.append('<a class="w" href="%swords/%s.html">%s</a>' % (root, best, E(pc)))
        out.append(E(lead) + '-'.join(rend) + E(trail))
    return ' '.join(out)

# ---------------- page shell ----------------
def shell(title, body, root, desc='', active=''):
    nav = ''.join(
        '<a href="%s%s"%s>%s</a>' % (root, href, ' class="on"' if key == active else '', label)
        for key, label, href in [
            ('home', 'Dictionary', 'index.html'),
            ('words', 'Words', 'words/index.html'),
            ('english', 'English', 'english/index.html'),
            ('stories', 'Stories', 'stories/index.html'),
            ('about', 'About', 'about.html')])
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s — Miluk Dictionary</title>
%s<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Charis+SIL:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="%sstyle.css">
</head>
<body data-root="%s">
<nav class="sticky-nav"><div class="nav-container">
<a href="%s../" class="nav-logo">Miluk</a>
<div class="nav-links">%s</div>
</div></nav>
<main class="dict-main">
%s
</main>
<footer class="dict-footer">
<p>The voice in these texts is Annie Miner Peterson&rsquo;s, recorded by Melville Jacobs in 1933&ndash;34.</p>
<p>Miluk is the heritage of the Coquille Indian Tribe, the Confederated Tribes of Coos, Lower Umpqua and Siuslaw Indians, and the Confederated Tribes of Siletz Indians.</p>
<p><a href="%s../">miluk.org</a> &middot; &copy; 2026 adalsi yunyesa</p>
</footer>
<script src="%sapp.js"></script>
</body>
</html>''' % (E(title),
              ('<meta name="description" content="%s">\n' % E(desc)) if desc else '',
              root, root, root, nav, body, root, root)

def write(path, text):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')

# Remove only generator-owned pages. This prevents stale entry or story pages from
# surviving a boundary correction while leaving data and static assets untouched.
for owned_dir in (OUT / 'words', OUT / 'stories'):
    if owned_dir.exists():
        for owned_page in owned_dir.glob('*.html'):
            owned_page.unlink()

# ---------------- entry pages ----------------
BADGE = {'corpus':       ('badge-corpus', 'attested verbatim in the corpus'),
         'corroborated': ('badge-corr',   'converted from the 1990 notation and corroborated in a Jacobs text'),
         'unverified':   ('badge-unv',    'not found in the digitized corpus — needs review')}

def letter_of(e):
    return initial_for_entry(e)

# section label letters (majority real initial per folded letter)
groups = collections.defaultdict(list)
for e in ENTRIES: groups[letter_of(e)].append(e)
label_for = {k: jacobs_category(k)['display'] for k in groups}
attested_inventory = {
    'schema': 'miluk-attested-initial-index/1',
    'rule': 'Only attested word-initial Jacobs units are emitted; the sole documentary exception is separately scoped.',
    'categories': [dict(jacobs_category(k), count=len(groups[k]))
                   for k in sorted(groups, key=JACOBS_ORDER.__getitem__)],
}
attested_bytes = (json.dumps(attested_inventory, ensure_ascii=False, indent=2) + '\n').encode()
attested_path = TOOL_DIR / 'provenance' / 'attested-index-inventory.json'
if not attested_path.exists() or attested_path.read_bytes() != attested_bytes:
    attested_path.write_bytes(attested_bytes)

MAX_FULL = 8
for e in ENTRIES:
    eid = e['entry_id']; root = '../'
    b = []
    b.append('<p class="crumb"><a href="../words/index.html">Words</a> · %s</p>' % E(label_for[letter_of(e)]))
    b.append('<h1 class="hw">%s</h1>' % E(e['headword']))
    if e['gloss']:
        b.append('<p class="gloss">%s</p>' % public_gloss(e['gloss']))
    # forms
    if e['forms']:
        b.append('<section class="forms"><h2>Attested forms</h2><ul class="formlist">')
    for f in e['forms']:
        cls, tip = BADGE.get(f['evidence'], ('badge-unv', f['evidence']))
        b.append('<li><span class="mk">%s</span> <span class="badge %s" title="%s">%s</span></li>'
                 % (E(f['form']), cls, E(tip),
                    {'corpus':'corpus','corroborated':'corroborated','unverified':'unverified'}[f['evidence']]))
    if e['forms']:
        b.append('</ul></section>')
    if e.get('extensions') or e.get('citation_summary') or e.get('record_notes') or e.get('raw_source_lines'):
        b.append('<section class="record1990"><h2>1990 record</h2>')
        if e.get('extensions'):
            b.append('<p><strong>Extensions:</strong> %s</p>' % E('; '.join(e['extensions'])))
        if e.get('citation_summary'):
            b.append('<p><strong>Source citation:</strong> %s</p>' % E(e['citation_summary']))
        for note in e.get('record_notes', []):
            b.append('<p>%s</p>' % E(note))
        if e.get('raw_source_lines'):
            b.append('<details class="source-record"><summary>Complete 1990 source record</summary><pre>%s</pre></details>' %
                     E('\n'.join(e['raw_source_lines'])))
        b.append('</section>')
    # cross references
    if e.get('cross_references'):
        xs = []
        for x in e['cross_references']:
            tail = x.split('--')[-1].strip()
            targets = reference_targets(tail)
            if len(targets) == 1:
                tgt = targets[0]
                lead = x.split('--')[0].strip()
                pre = (E(lead) + ' — ') if '--' in x and lead else ''
                xs.append('%s<a href="%s.html">%s</a>' % (pre, tgt['entry_id'], E(tgt['headword'])))
            else:
                if ASCII_NOTATION.search(tail):
                    if '--' in x:
                        lead = x.split('--')[0].strip()
                        shown = ((E(lead) + ' — ') if lead else '') + E(converted_reference(tail))
                    else:
                        shown = E(converted_reference(tail))
                    xs.append('<span class="mk">%s</span>' % shown)
                else:
                    xs.append('<span class="code1990" title="1990 note, in the original keyboard notation">%s</span>' % E(x))
        b.append('<p class="xref">See %s</p>' % ', '.join(xs))
    # attestations
    def really_verified(a):
        ln = line_by.get((a.get('story_id'), a.get('line')))
        if ln is None: return False
        ks = entry_keys.get(eid, ())
        for t in ln['miluk'].split(' '):
            for pc in t.strip(PUNCT).split('-'):
                pf = fold(pc)
                if any(k == pf or k in pf or (len(k) >= 3 and len(pf) >= 3 and pf in k) for k in ks):
                    return True
        return False
    ver = [a for a in e['attestations'] if a.get('story_id') in live_ids and really_verified(a)]
    unv = [a for a in e['attestations'] if a.get('story_id') and a.get('story_id') in live_ids
           and not really_verified(a)]
    slipn = sum(1 for a in e['attestations'] if a.get('story_id') and a.get('story_id') not in live_ids)
    unres = [a for a in e['attestations'] if 'unresolved' in a]
    seen = set(); shown = 0; more = []
    if ver or e.get('examples'):
        b.append('<section class="atts"><h2>In the texts</h2>')
    for a in ver:
        key = (a['story_id'], a['line'])
        if key in seen: continue
        seen.add(key)
        ln = line_by.get(key)
        if ln is None: continue
        if shown < MAX_FULL:
            b.append('<div class="att"><p class="m">%s</p>' %
                     link_line(ln['miluk'], ln.get('entries', []), root, self_id=eid))
            if ln['english']:
                b.append('<p class="t">&lsquo;%s&rsquo;</p>' % E(ln['english'].strip()))
            b.append('<p class="src"><a href="../stories/%s.html#l%d">%s, line %d</a></p></div>'
                     % (a['story_id'], a['line'], E(a['title']), a['line']))
            shown += 1
        else:
            more.append('<a href="../stories/%s.html#l%d">%s %d</a>' % (a['story_id'], a['line'], E(a['title']), a['line']))
    for ex in e.get('examples', []):
        mm = ex.get('miluk_modern') or ''
        if not mm or shown >= MAX_FULL: break
        b.append('<div class="att"><p class="m">%s</p>' % E(mm))
        if ex.get('english'): b.append('<p class="t">&lsquo;%s&rsquo;</p>' % E(ex['english']))
        if ex.get('cite'): b.append('<p class="src">%s</p>' % E(ex['cite']))
        b.append('</div>')
        shown += 1
    if ver or e.get('examples'):
        b.append('</section>')
    if more:
        b.append('<p class="more"><span>further attestations:</span> %s</p>' % ' · '.join(more))
    if unv:
        refs = []
        seen2 = set()
        for a in unv:
            key = (a['story_id'], a['line'])
            if key in seen2: continue
            seen2.add(key)
            refs.append('<a href="../stories/%s.html#l%d">%s %d</a>' % (a['story_id'], a['line'], E(a['title']), a['line']))
        b.append('<p class="more unloc"><span>also cited (form not located verbatim in the line):</span> %s</p>' % ' · '.join(refs))
    if slipn:
        b.append('<p class="more unloc"><span>also cited in the 1953/slip-file material (outside this edition):</span> %d citation%s</p>'
                 % (slipn, 's' if slipn != 1 else ''))
    if unres:
        b.append('<p class="more unloc"><span>unresolved 1990 citations:</span> %s</p>'
                 % ' · '.join(E(a['unresolved']) for a in unres))
    b.append('<p class="prov">1990 source file: %s · id: %s</p>' % (E(e.get('source_file') or ''), E(eid)))
    write('words/%s.html' % eid,
          shell(e['headword'], '\n'.join(b), root, active='words',
                desc='Miluk dictionary entry: %s — %s' %
                     (plain_hw(e), public_gloss_text(e['gloss']) if e['gloss'] else 'Miluk word')))

# ---------------- words index (Miluk A–Z) ----------------
order = sorted(groups.keys(), key=JACOBS_ORDER.__getitem__)
anchor_for = {key: 's-%02d' % JACOBS_ORDER[key] for key in order}
b = ['<h1>Miluk words</h1>',
     '<p class="lead">%d entries from the 1990 dictionary. Diacritics are ignored in the index order.</p>' % len(ENTRIES),
     '<div class="search-box"><input id="q" type="search" placeholder="Search Miluk or English…" autocomplete="off"><div id="results"></div></div>',
     '<p class="alpha">%s</p>' % ' '.join('<a href="#%s">%s</a>' % (anchor_for[k], E(label_for[k])) for k in order)]
for k in order:
    b.append('<h2 id="%s">%s</h2><ul class="entryindex">' % (anchor_for[k], E(label_for[k])))
    for e in sorted(groups[k], key=lambda x: (fold(plain_hw(x)), x['headword'])):
        b.append('<li><a href="%s.html" class="mk">%s</a><span class="g">%s</span></li>'
                 % (e['entry_id'], E(e['headword']), E(public_gloss_text(e['gloss'] or ''))))
    b.append('</ul>')
write('words/index.html', shell('Miluk words', '\n'.join(b), '../', active='words',
                                desc='Miluk–English: all %d entries of the 1990 Miluk dictionary.' % len(ENTRIES)))

# ---------------- english finder ----------------
senses = collections.defaultdict(set)
for e in ENTRIES:
    if not e['gloss']: continue
    for sense in re.split(r'[;/]| or ', e['gloss']):
        for part in sense.split(','):
            p = part.strip(' .,?')
            if not p or not (1 < len(p) < 60): continue
            if re.search(r"[<@#;!&$%`]|\.BYB|^see |reference", p, re.I): continue
            senses[p.lower()].add(e['entry_id'])
b = ['<h1>English finder</h1>',
     '<p class="lead">%d English senses pointing into the Miluk entries.</p>' % len(senses),
     '<div class="search-box"><input id="q" type="search" placeholder="Search Miluk or English…" autocomplete="off"><div id="results"></div></div>']
cur = None
for k in sorted(senses):
    f0 = (k[:1] or '#').upper()
    if f0 != cur:
        cur = f0
        b.append('<h2>%s</h2>' % E(cur))
    links = ', '.join('<a class="mk" href="../words/%s.html">%s</a>' % (i, E(by_id[i]['headword']))
                      for i in sorted(senses[k]))
    b.append('<p class="sense"><span class="e">%s</span> %s</p>' % (E(k), links))
write('english/index.html', shell('English finder', '\n'.join(b), '../', active='english',
                                  desc='English–Miluk finder list of the 1990 Miluk dictionary.'))

# ---------------- story pages ----------------
for i, s in enumerate(live):
    root = '../'
    b = ['<p class="crumb"><a href="index.html">Stories</a></p>',
         '<h1>%s</h1>' % E(s['title']),
         '<p class="lead">%d lines · from Melville Jacobs&rsquo;s Coos texts, dictated by Annie Miner Peterson (1933&ndash;34); keyed 1986&ndash;1990.</p>' % s['line_count'],
         '<div class="modes" role="tablist">'
         '<button data-mode="inter" class="on">Interlinear</button>'
         '<button data-mode="miluk">Miluk</button>'
         '<button data-mode="english">English</button></div>',
         '<div class="story mode-inter" id="story">']
    for l in s['lines']:
        b.append('<div class="line" id="l%d"><a class="n" href="#l%d">%d</a>'
                 '<p class="m">%s</p><p class="e">%s</p></div>'
                 % (l['line'], l['line'], l['line'],
                    link_line(l['miluk'], l.get('entries', []), root),
                    E(l['english'].strip())))
    b.append('</div>')
    nav2 = []
    if i > 0: nav2.append('<a href="%s.html">&larr; %s</a>' % (live[i-1]['story_id'], E(live[i-1]['title'])))
    if i < len(live)-1: nav2.append('<a class="nxt" href="%s.html">%s &rarr;</a>' % (live[i+1]['story_id'], E(live[i+1]['title'])))
    if nav2: b.append('<p class="storynav">%s</p>' % ' '.join(nav2))
    write('stories/%s.html' % s['story_id'],
          shell(s['title'], '\n'.join(b), root, active='stories',
                desc='Miluk text: %s — interlinear, with every word linked to the dictionary.' % s['title']))

# ---------------- stories index ----------------
b = ['<h1>The texts</h1>',
     '<p class="lead">%d recovered corpus records representing 110 of 111 published Miluk-bearing texts, %d numbered lines. Two published texts are absorbed within records and one 1940 text is absent pending source-integrity work. Read interlinearly, or in Miluk or English alone; every recognizable Miluk word links to its dictionary entry.</p>'
     % (len(live), sum(s['line_count'] for s in live)),
     '<input id="storyfilter" type="search" placeholder="Filter by title…" autocomplete="off">',
     '<ul class="storylist">']
for s in live:
    b.append('<li><a href="%s.html">%s</a><span class="lc">%d lines</span></li>'
             % (s['story_id'], E(s['title']), s['line_count']))
b.append('</ul>')
write('stories/index.html', shell('The texts', '\n'.join(b), '../', active='stories',
                                  desc='The Miluk texts of Annie Miner Peterson, readable interlinearly.'))

# ---------------- search index ----------------
def search_aliases(e):
    raw = e.get('headword_ascii') or ''
    key = letter_of(e)
    remainder = raw[len(key):] if raw.lower().startswith(key) else raw
    return [alias + remainder for alias in jacobs_category(key)['search_aliases']]

idx = {'entries': [{'i': e['entry_id'], 'h': e['headword'],
                    'k': fold(plain_hw(e)) or '',
                    'kk': sorted({fold(f['form']) for f in e['forms'] if fold(f['form'])} |
                                 {fold(a) for a in search_aliases(e) if fold(a)}),
                    'g': public_gloss_text(e['gloss'] or '')} for e in ENTRIES],
       'stories': [{'i': s['story_id'], 't': s['title']} for s in live]}
write('search-index.json', json.dumps(idx, ensure_ascii=False, separators=(',', ':')))

# ---------------- about ----------------
FOREWORD = (TOOL_DIR / 'foreword.html').read_text(encoding='utf-8')
INTRO = (TOOL_DIR / 'intro1990.html').read_text(encoding='utf-8')
b = ['<h1>About the dictionary</h1>', FOREWORD, '<hr class="rule">',
     '<h1>Introduction (1990)</h1>', INTRO]
write('about.html', shell('About', '\n'.join(b), './', active='about',
                          desc='Foreword to the restored edition and the original 1990 introduction.'))

# ---------------- dictionary home ----------------
nstats = (len(ENTRIES), sum(len(e['forms']) for e in ENTRIES), len(live), sum(s['line_count'] for s in live))
b = ['''<div class="dict-hero">
<p class="hero-greeting">tłɛ-hɛ́·niyɛ</p>
<h1>A Miluk Dictionary</h1>
<p class="hero-subtitle">The 1990 lexicography of the Jacobs corpus, restored</p>
<div class="search-box big"><input id="q" type="search" placeholder="Search Miluk or English — try &lsquo;neqe&rsquo; or &lsquo;run away&rsquo;…" autocomplete="off"><div id="results"></div></div>
<p class="stats">%d entries · %d attested forms · %d corpus records · %d lines</p>
</div>''' % nstats,
     '''<div class="cards">
<a class="card" href="words/index.html"><span class="card-title">Miluk words</span><span class="card-sub">the full A&ndash;Z, every entry with its attestations in context</span></a>
<a class="card" href="english/index.html"><span class="card-title">English finder</span><span class="card-sub">from an English sense to its Miluk words</span></a>
<a class="card" href="stories/index.html"><span class="card-title">The texts</span><span class="card-sub">read interlinearly; tap any word to open its entry</span></a>
<a class="card" href="about.html"><span class="card-title">About</span><span class="card-sub">the foreword to this edition and the 1990 introduction</span></a>
</div>''',
     '''<div class="provenance">
<p>These are the Miluk texts Melville Jacobs recorded from <strong>Annie Miner Peterson</strong> in 1933 and 1934,
taken apart into their morphemes and put back together as a lexicon &mdash; compiled 1986&ndash;1990 by Troy Anderson
as the first reference work in Miluk lexicography, recovered and restored in 2026. Every entry cites the story and
line where its forms occur, and every text links back into the dictionary.</p>
</div>''']
write('index.html', shell('A Miluk Dictionary', '\n'.join(b), './', active='home',
                          desc='A Miluk Dictionary — %d entries and %d recovered corpus records representing 110 of 111 published Miluk-bearing texts, searchable in Miluk and English.' % (len(ENTRIES), len(live))))

print('pages written:', sum(len(fs) for _, _, fs in os.walk(OUT)))
print('entries:', len(ENTRIES), ' corpus records:', len(live))
