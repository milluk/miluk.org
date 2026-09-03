"""B1: build the offline English approximate-match index for the search box.

This is a one-time (re-run-on-gloss-change) extraction tool, not part of the
standard `gen.py` build. It reads Princeton WordNet 3.0's raw database files
(not vendored in this repository — see provenance/WORDNET_SOURCE.md for the
exact archive, hash, and retrieval URL) and this edition's public glosses
(`dictionary/data/dictionary.json`), and writes a small, checked-in, sorted
JSON file, `wordnet-synonyms.json`, mapping an English word a person might
type to the entries whose gloss is a WordNet synonym or immediate
hypernym/hyponym (one broader- or narrower-term hop) of a word in that gloss.

`gen.py` reads only this checked-in output — never WordNet itself, never the
network — so the reproducible build stays standard-library-only and offline,
per tools/dictionary/README.md. Re-run this script by hand (with a local copy
of the WordNet 3.0 database) only when glosses change enough to warrant a
refresh; commit the regenerated `wordnet-synonyms.json` as its own
ledger-backed change, the same as any other derived-data update.

Usage:
    python3 tools/dictionary/wordnet_expand.py --wordnet-dir /path/to/wordnet
"""
import argparse, json, re, sys
from pathlib import Path
from collections import defaultdict

TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parent.parent

STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has',
    'have', 'he', 'her', 'him', 'his', 'in', 'into', 'is', 'it', 'its',
    'not', 'of', 'on', 'one', 'or', 'she', 'that', 'the', 'their', 'them',
    'they', 'this', 'to', 'was', 'were', 'with', 'you', 'your',
}

HYPERNYM = {'@', '@i'}
HYPONYM = {'~', '~i'}


def load_pos(wn_dir: Path, pos: str):
    """Parse index.<pos> and data.<pos> into:
       lemma_to_offsets: {lemma: [synset_offset,...]}
       synset: {offset: {'lemmas': [...], 'hyper': [offset,...], 'hypo': [offset,...]}}
    """
    lemma_to_offsets = defaultdict(list)
    index_path = wn_dir / ('index.%s' % pos)
    for line in index_path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('  '):
            continue
        parts = line.split()
        lemma = parts[0].replace('_', ' ')
        # last field is synset_cnt; the trailing synset_cnt offsets are the last N tokens
        try:
            synset_cnt = int(parts[2])
        except (IndexError, ValueError):
            continue
        offsets = parts[-synset_cnt:] if synset_cnt else []
        lemma_to_offsets[lemma].extend(offsets)

    synset = {}
    data_path = wn_dir / ('data.%s' % pos)
    for line in data_path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('  '):
            continue
        body = line.split('|', 1)[0].split()
        offset = body[0]
        w_cnt = int(body[3], 16)
        idx = 4
        lemmas = []
        for _ in range(w_cnt):
            lemmas.append(body[idx].replace('_', ' '))
            idx += 2
        p_cnt = int(body[idx]); idx += 1
        hyper, hypo = [], []
        for _ in range(p_cnt):
            sym, target = body[idx], body[idx + 1]
            idx += 4
            if sym in HYPERNYM:
                hyper.append(target)
            elif sym in HYPONYM:
                hypo.append(target)
        synset[offset] = {'lemmas': lemmas, 'hyper': hyper, 'hypo': hypo}
    return lemma_to_offsets, synset


def gloss_words(gloss: str):
    words = re.findall(r"[a-zA-Z']+", gloss.lower())
    return sorted({w for w in words if len(w) >= 3 and w not in STOPWORDS})


def lookup_offsets(word, lemma_to_offsets):
    for candidate in (word, word.rstrip('s'), word + 's', word[:-2] if word.endswith('es') else None):
        if candidate and candidate in lemma_to_offsets:
            return lemma_to_offsets[candidate]
    return []


WORD_RE = re.compile(r"^[a-z']+$")


def _add(out, lem, score, word):
    lem = lem.lower()
    if lem == word or not WORD_RE.match(lem):
        return  # skip proper nouns, acronyms, multi-word or punctuated lemmas
    out[lem] = max(out.get(lem, 0), score)


def related_for_word(word, lemma_to_offsets, synsets):
    """-> {related_word: score}, best score kept per word. Only ever returns
    lowercase, single-token, purely-alphabetic keys (see WORD_RE) so the
    runtime index only ever needs to match a plain lowercased search box
    query."""
    out = {}
    for offset in lookup_offsets(word, lemma_to_offsets):
        s0 = synsets.get(offset)
        if not s0:
            continue
        for lem in s0['lemmas']:
            _add(out, lem, 1.0, word)  # direct synonym
        for p1 in s0['hyper'] + s0['hypo']:
            s1 = synsets.get(p1)
            if not s1:
                continue
            for lem in s1['lemmas']:
                _add(out, lem, 0.6, word)  # immediate broader/narrower term
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wordnet-dir', required=True, type=Path,
                     help='Directory containing index.noun/data.noun/index.verb/data.verb')
    ap.add_argument('--dictionary', type=Path,
                     default=REPO_ROOT / 'dictionary' / 'data' / 'dictionary.json')
    ap.add_argument('--out', type=Path, default=TOOL_DIR / 'wordnet-synonyms.json')
    ap.add_argument('--max-per-word', type=int, default=8)
    ap.add_argument('--min-score', type=float, default=1.0,
                     help='Drop related words scoring below this (default keeps only '
                          'direct synonyms; lower to 0.6 to also include immediate '
                          'hypernym/hyponym neighbors, at roughly 5x the output size).')
    args = ap.parse_args()

    entries = json.loads(args.dictionary.read_text(encoding='utf-8'))['entries']

    lemma_to_offsets = {}
    synsets = {}
    for pos in ('noun', 'verb'):
        l2o, ss = load_pos(args.wordnet_dir, pos)
        for k, v in l2o.items():
            lemma_to_offsets.setdefault(k, []).extend(v)
        synsets.update(ss)

    # word -> {entry_id: best_score}
    index = defaultdict(dict)
    seen_words = {}
    for e in entries:
        gloss = (e.get('gloss') or '')
        if not gloss:
            continue
        for w in gloss_words(gloss):
            if w not in seen_words:
                seen_words[w] = related_for_word(w, lemma_to_offsets, synsets)
            for related, score in seen_words[w].items():
                related = related.strip()
                if not related or ' ' in related:
                    continue  # keep the runtime index to single-token queries
                cur = index[related].get(e['entry_id'], 0)
                if score > cur:
                    index[related][e['entry_id']] = score

    out = {}
    for word, entry_scores in sorted(index.items()):
        ranked = sorted(entry_scores.items(), key=lambda kv: (-kv[1], kv[0]))[:args.max_per_word]
        ranked = [(eid, score) for eid, score in ranked if score >= args.min_score]
        if ranked:
            out[word] = [[eid, round(score, 2)] for eid, score in ranked]

    args.out.write_text(
        json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print('related-word keys:', len(out))


if __name__ == '__main__':
    main()
