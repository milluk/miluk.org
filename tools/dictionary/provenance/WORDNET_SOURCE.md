# WordNet source for the English approximate-match index (B1)

`wordnet-synonyms.json` is derived from Princeton WordNet 3.0, a public-domain
English lexical database, not from any Miluk source material. It never
touches corpus, dictionary, correction-ledger, or other protected inputs; it
only reads the public `gloss` field already emitted for each of the 1,275
dictionary entries.

## Retrieval

- Archive: `wordnet.zip`
- Retrieved from: `https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip`
  (NLTK's mirror of the official Princeton WordNet 3.0 database files)
- Retrieved: 2026-09-01
- Archive SHA-256: `cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59`
- License: WordNet 3.0 license (public-domain-style permissive; full text was
  vendored alongside the raw files during extraction — see the `LICENSE` file
  inside the archive above).

Only `index.noun`, `data.noun`, `index.verb`, and `data.verb` were used. The
raw WordNet database (~23 MB) is **not** vendored in this repository — it is
a build-time-only input for `wordnet_expand.py`, the same way source `.FIN`
files feed the restoration pipeline without every intermediate being carried
forward. What's checked in is the derived output, `wordnet-synonyms.json`,
which is what `gen.py` actually reads.

## Method

For every distinct English content word in a published gloss, `wordnet_expand.py`
looks up its noun/verb WordNet synsets and records, per related word:

- **1.0** — direct synonym (same synset)
- **0.6** — one hop up or down the hypernym/hyponym tree (broader or
  narrower term)

**Shipped scope:** the checked-in `wordnet-synonyms.json` was generated with
the tool's default `--min-score 1.0`, i.e. **direct synonyms only** (4,338
related words, ~630 KB pretty / ~300 KB compact at runtime). The
hypernym/hyponym tier is implemented and covered by tests, but generating it
at scale (`--min-score 0.6`) produces a roughly 5x larger index; it was left
out of this first shipped pass purely to keep the initial change small and
easy to review, not for any design reason. Re-running with `--min-score 0.6`
is a one-line follow-up whenever that broader coverage is wanted.

Multi-word WordNet lemmas are dropped (the runtime index only serves
single-token search queries). Up to 8 highest-scoring entries are kept per
related word.

## Regeneration

Not part of the standard `gen.py` build (which stays offline and
standard-library-only). Re-run by hand only when glosses change enough to
warrant a refresh, with a local WordNet 3.0 copy:

```sh
python3 tools/dictionary/wordnet_expand.py --wordnet-dir /path/to/wordnet
```

Commit the regenerated `wordnet-synonyms.json` as its own ledger-backed
change, same as any derived-data update.
