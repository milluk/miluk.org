# Correction and transformation summary

## 1939 collation

`dictionary/data/correction-ledger.json` imports all 922 rows of the recovered
Jacobs collation workbook. Each row retains a stable ID, target, transcription
value, Jacobs reading, disposition, category, book-page span, and restoration
stage.

The workbook contains two related counts that must not be collapsed:

- 343 observation rows are labeled `APPLIED to corpus`;
- those rows refer to 337 unique applied transformation records; and
- 579 observation rows remain for review and are represented as unresolved.

The workbook also has a separate `Uncertain` sheet with 125 diacritic
observations. They are part of the source inventory, not part of the 922-item
correction count, and were not silently treated as applied changes.

## Dictionary v2 effective diff

`v2-effective-diff.json` is a field-level structured diff of commit
`dc186a2b8cea67a1a4c08b33549c1302951d99f7` against its first parent. It
confirms:

- English-field changes in 166 corpus records across 40 stories;
- 19 records in which Miluk/English fields were re-oriented, comprising five
  published UWPA records and fourteen outside-edition slip-file records;
- five changed dictionary entries: one gloss cleanup and four derived
  attestation-verification changes.

The commit message's “167” describes converted embedded tokens, not changed
corpus records, and its “one line” field-unswap statement understates the
effective structured diff. The existing commit message was not rewritten.

Every changed corpus line now retains its previous field value in
`documentary_original_fields`, references the receipt through stable
`transformation_ids`, and retains `english_original` when the English field
changed. These are 2026 restoration/presentation operations, not changes
retroactively attributed to the 1990 dictionary.

## Boundary disposition

The 35 Jacobs slip-file records and eight empty working containers remain under
`tools/dictionary/archive/outside-edition/`. Original 1990 entry citations to
them remain in `dictionary.json`, but those records cannot enter the public
corpus or generate story pages.

Anthony P. Grant's paper on John Milhau's 1856 Hanis vocabularies was reviewed
and excluded. No Grant, Milhau, Lower Coquille, reconstructed, or other later
form was imported as edition evidence.
