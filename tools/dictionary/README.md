# Dictionary build and restoration record

`/dictionary/` is generated. Do not hand-edit generated HTML or
`search-index.json`.

## Clean build

From the repository root, using Python 3 and only the standard library:

```sh
python3 tools/dictionary/gen.py
python3 tools/dictionary/test_site.py
```

The defaults read the canonical public inputs from `dictionary/data/` and write
the site to `dictionary/`. Both commands also accept `--data` and `--out`.
Generation removes stale generator-owned word and story pages, is deterministic,
and the verifier runs a second generation before checking that the tracked
`dictionary/` tree has no diff.

## Edition boundary

This edition contains the Miluk texts published by Melville Jacobs in *Coos
Narrative and Ethnologic Texts* (1939) and *Coos Myth Texts* (1940), together
with Troy Anderson's 1990 dictionary. It does not admit slip-file, 1953,
Harrington, Frachtenberg, Dorsey, Milhau, Grant, modern-speaker, or other source
layers as edition corpus evidence.

The restored working corpus had 151 records / 7,723 lines. Explicit source
classification of the recovered export shows:

- 108 UWPA-section corpus records / 7,149 lines in
  `dictionary/data/corpus.json`;
- 35 Jacobs slip-file records / 574 lines preserved in
  `archive/outside-edition/slip-file-records.json`; and
- eight empty Word Cruncher section containers preserved in
  `archive/outside-edition/working-containers.json`.

The former filename regex suppressed 32 slip records but missed file 10, file
20, and file 30 after their generated slugs became `f-1`, `f-2`, and `f-3`.
`provenance/source-classification.json` now makes the recovered-export boundary
inspectable and the build does not infer provenance from filenames. That
numerical boundary does not prove publication completeness. The separate
`provenance/publication-inventory.json` inventories 111 Miluk-bearing published
texts (77 in 1939, 34 in 1940): 110 are represented in the 108 recovered
records, including two absorbed texts, and one 1940 text is absent.

The absorbed texts are “A man obtains fir power” at lines 69-90 of `t006` and
“The water got high” at lines 92-118 of `t023`. “The rock point person lost his
good luck thing” (1940, printed pages 133-135) is absent. Record splitting or a
source-bound import is pending source-integrity work requiring Troy's
authorization; this repair performs neither.

Original 1990 dictionary citations to outside-edition sources remain in
`dictionary.json`. They resolve against the archival outside-edition records for
verification but cannot generate public story pages or corpus attestations.

## Restoration pipeline

The repository copy under `pipeline/` is canonical; the Dropbox directory is an
archive/mirror. Stages are intentionally separate:

1. `convert_fin.py` converts the 684 preserved `.FIN` sources to UTF-8 text.
2. `parse_dictionary.py` parses documentary entry blocks without changing their
   ASCII values.
3. `parse_corpus.py` parses the Word Cruncher export and applies only the
   recovered, logged corpus repairs.
4. `normalize_dictionary.py` creates display forms while retaining each ASCII
   form and logs every repair.
5. `verify_dictionary.py` corroborates derived forms only against records
   explicitly classified `uwpa-recovered-record`.
6. `classify_sources.py` and `publish_corpus.py` enforce the public boundary and
   emit deterministic public and archival JSON.
7. `import_collation.py`, `build_v2_receipt.py`, and `hash_manifest.py` emit the
   correction and custody records.

All JSON emission is UTF-8, sorted by stable source order, indented two spaces,
and terminated by one newline.

### Archival completeness status

The repository can reproducibly build and verify the committed public site and
can deterministically re-derive the public corpus from the preserved post-repair
working checkpoint. The 684 `.FIN` sources also convert and parse to 684 source
records with repository code.

The complete `.FIN`-to-1,111-entry derivation is **not yet fidelity-verified**.
The restoration archive does not contain the exact LibreOffice UTF-8 conversion
output, `lexicon.json`, `corpus_index.pkl`, the pre-restructure intermediates, or
the original repair/verification logs. The recovered scripts referenced those
files outside the restoration directory. The repository therefore does not
claim that its new converter reproduces the original conversion byte for byte,
and does not claim that 1,111 entries reproduce from the archival `.FIN` files.
The exact missing-artifact list and discovered hashes are in
`provenance/source-inventory.json`.

## Provenance and corrections

- `provenance/fin-source-manifest.json` hashes every preserved 1990 source file.
- `dictionary/data/correction-ledger.json` is the complete 922-observation 1939
  collation: 343 workbook observations say an operation was applied, representing
  337 unique applied transformations; 579 remain unresolved. The workbook's
  separate 125 uncertain-diacritic observations remain described in the source
  inventory and were not misrepresented as applied corrections.
- `provenance/v2-effective-diff.json` records every effective field change in
  commit `dc186a2`: 166 English-field changes across 40 stories; 19 field
  unswaps (five UWPA, fourteen slip-file); one gloss cleanup; and four derived
  attestation-verification changes.
- Changed corpus lines retain `documentary_original_fields` and stable
  `transformation_ids`; changed English fields also retain `english_original`.
  The visible `english` value remains the display value.

Entry pages render at most eight full quotations. Additional public attestations
are linked or summarized, outside-edition citations are counted separately, and
unresolved 1990 citations remain visibly unresolved. “All attestations” means
the data and navigation preserve them; it does not mean every quotation is
expanded inline.

The 1940 volume remains uncollated. The Anthony P. Grant/Milhau material was
reviewed only to enforce the edition boundary and was not imported or used as
entry evidence.
