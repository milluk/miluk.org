# Dictionary build

`/dictionary/` is generated — do not hand-edit it. To rebuild:

1. Update `/dictionary/data/corpus.json` and `dictionary.json` (produced by the
   pipeline in Dropbox: `Miluk/Language/MILUK/Dictionary/Rebuild 2026-08-27/pipeline/`).
2. Point `gen.py`'s SRC at the data (it reads corpus.json, dictionary.json,
   foreword.html, intro1990.html from its own directory) and OUT at `/dictionary/`.
3. `python3 gen.py && python3 test_site.py` — ship only on ALL CHECKS PASS.

The slip-file texts are deliberately excluded from this edition (the 1990
dictionary is the Jacobs narrative corpus only).
