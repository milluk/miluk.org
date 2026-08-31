# Complete-source recovery: evidence and founder rulings

## Live state verified before writes

- PR #1 was open and draft at `0cb9608410602fcc9495946d1016bbe2c976ce3c`.
- `main` was deployed at `7b24d78c4132804110c2453e68ec0a2ad8034a69`.
- No remote movement had to be reconciled.

## Exhaustive authority inventory

`provenance/authoritative-directory-inventory.json` records all 2,118 regular
files under the authoritative MILUK directory in bytewise relative-path order:
64,600,989 bytes, 1,159 unique SHA-256 values, 962 root files, 360
extensionless files, 1,368 case-insensitive FIN paths, and 959 duplicate paths.
Every item has an explicit structural classification and pipeline disposition.

The former converter used `Path.glob('*.FIN')` at the directory root and
required exactly 684 matches. It therefore saw the canonical D-Z FIN set but
could not see the A-C consolidated tables or extensionless reference files.

The five newly admitted final-entry tables are:

| Original path | Bytes | SHA-256 | Rows |
|---|---:|---|---:|
| `ABC/DICT#.BYN` | 8,352 | `f170a116e25e0b2d05e8cdfefb133f1096d843963bc2e13f2dcf564225cbdf1c` | 58 |
| `ABC/DICT%.BYN` | 755 | `c73463cfdaf49d12b13db46b09d4b4f289e8db5328eb991d25c7e633177e312c` | 8 |
| `ABC/DICTA.BYN` | 4,472 | `239dd33ef1741292befe30e084ca8842fd44dac94791c50ee8c55abc39ae2ea0` | 35 |
| `ABC/DICTB.BYN` | 4,159 | `fb9ff1e571092d736a2d244b0fdfa0014770fcf7c4afacb7e25a2649b6b7482d` | 40 |
| `ABC/DICTC.BYN` | 1,745 | `3be526780158750551f1f53e81c8c8887a8f469df7e968e091676879a74a030e` | 24 |

They contain 165 numbered source rows. The literal root files Troy identified
are WordCruncher reference support, not the consolidated final-entry tables:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `#` | 555 | `ecc3855a8c793e9a73d41bf1f206b1aac7543e598878ab715bb3651a61dc7ace` |
| `%` | 214 | `5e0ece7ad4c8ef8a2be38e3686b1ea3324b9486864157d9a852aba10528e6095` |
| `A` | 658 | `6d2ffacb78823b3a59bb218cde94c8a540b86ad24c497dd14abecebec0aeb9f5` |
| `B` | 714 | `5293fd924b938ed71250ef89633cad6a58d8ed9eb161269480bf539c4ffbf863` |
| `C` | 580 | `175f541b6199569e17366370dd579b7c407511925dbefb191bc0ba7794707494` |

Each has a byte-identical `ABC/` copy. Both original path layers are archived
and hashed in `provenance/recovered-source-manifest.json`.

The admitted-source count is therefore 684 before recovery and 689 after
recovery. No other inventoried file matched an independent final-entry
container: every one of the remaining 1,429 authority items has an explicit
duplicate, support, archive, intermediate, or non-final disposition in the
exhaustive inventory.

## Character and alphabet authority

Jacobs's *Coos Phonetics from UWPA.pdf* is 11,673,201 bytes with SHA-256
`de8f1cd6abfb4a19088cc87e2fab564ac081b87d6de34f3596283a6ec9ab050f`.
The phonetic description is on printed pages 11-18. The historical mapping
guide, *Guide to Moving Melville Jacobs Materials from Handwritten to
Machine.docx*, is 3,006,624 bytes with SHA-256
`bdc74baa66c467d731f8ab9c9a44f93ca4e2bd4704d3cb45bc2605c718d31ba2`.
Together they establish `#` as barred l, `%` as `ɣ`, and the 1990 ASCII forms
of Jacobs's multi-character consonants.

Jacobs's complete phonetic inventory, grouped in his descriptive order, is:

- vowels: `ə a ɛ i u`;
- bilabial: `b p p' w w' m m'`;
- alveolar: `d t t' dz ts t's s s' n n'`;
- c-series: `dj tc t'c c c'`;
- anterior palatal: `g̯ k̯ k̯' x̯ x̯' y y'`;
- medial palatal: `g gw k kw k' k'w ɣ ɣ' ɣw x xw x'`;
- velar: `g̣ g̣w q qw q' q'w ɣ̣ ɣ̣' ɣ̣w x̣ x̣' x̣w`;
- faucal: `ʔ h hw`; and
- lateral: `dl tł t'ł l l' ł ł'`.

The historical keyboard map uses `@` for `ə`, `e` for `ɛ`, `!` for the
glottalization of ordinary stops, apostrophe in `t's`, `t'c`, and `t'#`, `&`
for the anterior-palatal inflection, `;` for the velar dot, `#` for `ł`, and
`%` for `ɣ`. Thus the crucial mappings are `c` → display `c` / search `sh`,
`tc` → display `tc` / search `ch`, `t'c` → display `t'c` / search `ch'`,
`t#` → `tł`, `t'#` → `t'ł`, `#` → `ł`, and `%` → `ɣ`. Search aliases do not
select the documentary display spelling.

### Initial-index presentation boundary

`KA.FIN` is preserved as the DOS-era source filename, but its filename is not
linguistic evidence that the “people, person” headword was simply `ka`.
`parse_dictionary.py` historically copied `Path.stem` into `headword`; that is
why entry `e0511-ka` and its generated navigation inherited `KA`. Its protected
first Reference List form is `k!&a'`, which the authoritative converter renders
`k̯̓a'`.

This is now an auditable general rule, not a KA-only exception. The deterministic
`provenance/filename-surrogate-inventory.json` accounts for all 1,275 entries.
It admits a public lemma only when one entry owns a `.FIN` source, that source
has exactly one Reference List, and the source filename and its first Reference
List form have the same conservative DOS-safe fold. Of 224 admitted filename
surrogates, 71 change the initial category: for example, `GAHAIS.FIN` supplies
`g;a<ha<is` → `g̣áháis`, under `g̣` rather than `g`. The 1,051 shared,
non-single, nonmatching, or non-FIN records are explicit audit findings and
remain unaltered.

The rule affects only public headers, index placement, and search presentation.
It leaves `.FIN` bytes, `source_file`, `headword_ascii`, `headword`, entry IDs,
and dictionary data unchanged. Unicode canonical ordering yields `k&!` from the
two combining marks, so initial classification normalizes that ordering to the
recovered inventory key `k!&`; it does not posit a new phonetic unit. The public
table of contents uses ordinary American English base-letter order; where that
order ignores a Miluk diacritic, the documented Jacobs inventory supplies the
stable tie-break.

The visible `x'` bucket was likewise a classifier artifact. Entry
`e1021-xinxinu` displays `x·ínx̣inu`, and its preserved form begins
`x:i<nx;inu`: the colon is the length mark rendered as a middle dot. The raw
classifier converted the middle dot back to a colon and then selected `x:` by
longest match, even though the Jacobs inventory uses that same key to name the
distinct glottalized `x'` unit. Presentation-aware classification now keeps
this length-bearing entry beneath `x`. Jacobs `x'` remains in the 68-unit
inventory but is unattested word-initially, so no `x'` tab is emitted.

The four recovered records `DICT#.BYN:3` through `DICT#.BYN:6` (entries
`e1114-l-e-nwi` through `e1117-l-u`) begin with raw `#:` and display barred L
plus length (`ł·`). The colon is therefore a length mark in these lexical
records, not evidence for word-initial Jacobs `ł′`. Initial classification
uses that converted presentation evidence to group the four beneath `ł`.
Jacobs `ł′` remains one of the 68 phonetic units but is unattested initially,
so no `ł′` index tab is emitted. The raw rows, entry IDs, and headwords are
unchanged.

`e0027-u-u` remains a Gate 2 read-only source-fidelity audit target for its
missing gloss and large form family; Gate 1 makes no inference or regrouping.

## Source duplicate

`DICT#.BYN:27` and `DICT#.BYN:28` have the same headword `#dja`, gloss
“ate/eat up,” primary citation, and alternate-form set. Row 28 is a strict
superset, adding extension `-t` and form `#dje\``. Both raw rows are retained.
The verified strict-superset exclusion admits 164 final entries from the 165
rows, producing 1,275 dictionary entries total. The retained entry traces to
both rows, with row 28 explicitly identified as the content-bearing superset.

## Identifier gate

All existing `e0001`-`e1111` identifiers and URLs remain unchanged. Recovered
entries append at `e1112` through `e1275`; no existing ID, URL, or internal
link is renumbered. The historical tables contain no stable identifiers.

## Documentary Z exception

The existing source `Z.FIN` (421 bytes, SHA-256
`e5d30ad24eace3cf3ef2bfb7ec9b22a56d75d2de69212f41abec438c723502e4`)
produces `e1111-z`, headword `z`, form `zu:<t'#u:c`, gloss “awful thing.”
Jacobs's authoritative inventory contains `dz` but no independent `z` unit.

The founder ruling retains a visible lowercase `z` index category for this literal 1990
source form. It does not reinterpret the entry as `DZ` and does not add an
independent `z` to Jacobs's phonetic inventory. The exception is constrained
in code and verification to entry `e1111-z`, source file `Z`, and ASCII
headword `Z`; every other independent-z initial fails generation. The entry's
literal form remains searchable.

## Before/after entries and attested index

The old 1,111-entry checkpoint and complete 1,275-entry result classify as
follows under the same source-provenanced rule. “Recovered” is the mechanical
difference between the two builds.

| Initial | Before | Recovered | After |
|---|---:|---:|---:|
| `a` | 0 | 35 | 35 |
| `ɛ` | 28 | 0 | 28 |
| `i` | 27 | 0 | 27 |
| `u` | 5 | 0 | 5 |
| `b` | 0 | 40 | 40 |
| `p` | 18 | 0 | 18 |
| `p'` | 2 | 0 | 2 |
| `w` | 63 | 0 | 63 |
| `m` | 65 | 0 | 65 |
| `d` | 99 | 0 | 99 |
| `t` | 66 | 0 | 66 |
| `t'` | 4 | 0 | 4 |
| `dz` | 32 | 0 | 32 |
| `ts` | 30 | 0 | 30 |
| `t's` | 14 | 0 | 14 |
| `s` | 35 | 0 | 35 |
| `n` | 33 | 0 | 33 |
| `dj` | 17 | 0 | 17 |
| `tc` | 18 | 0 | 18 |
| `t'c` | 8 | 0 | 8 |
| `c` | 3 | 24 | 27 |
| `g̯` | 1 | 0 | 1 |
| `k̯` | 6 | 0 | 6 |
| `k̯'` | 10 | 0 | 10 |
| `x̯` | 4 | 0 | 4 |
| `y` | 45 | 0 | 45 |
| `g` | 41 | 0 | 41 |
| `gw` | 27 | 0 | 27 |
| `k` | 28 | 0 | 28 |
| `kw` | 18 | 0 | 18 |
| `k'` | 4 | 0 | 4 |
| `k'w` | 7 | 0 | 7 |
| `ɣ` | 0 | 8 | 8 |
| `x` | 22 | 0 | 22 |
| `xw` | 8 | 0 | 8 |
| `g̣` | 39 | 0 | 39 |
| `g̣w` | 2 | 0 | 2 |
| `q` | 32 | 0 | 32 |
| `qw` | 10 | 0 | 10 |
| `q'` | 12 | 0 | 12 |
| `q'w` | 2 | 0 | 2 |
| `x̣` | 16 | 0 | 16 |
| `x̣w` | 4 | 0 | 4 |
| `h` | 109 | 0 | 109 |
| `hw` | 5 | 0 | 5 |
| `dl` | 24 | 0 | 24 |
| `tł` | 17 | 0 | 17 |
| `t'ł` | 19 | 0 | 19 |
| `l` | 31 | 0 | 31 |
| `ł` | 0 | 57 | 57 |
| `z` | 1 | 0 | 1 |

The 51 rows above are the complete attested initial-index inventory, already in
Jacobs order with the documentary exception last. The phonetic inventory has
68 units; the 18 unattested word-initial units are omitted from the visible
index rather than emitted as empty tabs.

## Dictionary font path

The site still requests Charis SIL remotely and retains Georgia/Times fallbacks;
no font files or dependencies were added. Chrome's receipt for `x̣` identified
a separate CSS defect: `.alpha`, generic `h2`, and `.crumb` explicitly selected
the system sans stack, so those linguistic index labels could never inherit the
body's Charis stack. The word-index alphabet and section headings, plus the
linguistic part of entry breadcrumbs, now select the serif/Charis stack. The
breadcrumb link and the rest of the navigation/interface chrome remain on the
system sans stack.

## Integrity hashes

- dictionary before: `e20c3c794a5bff5cc0b126628a737ed1cb7b020589881af037c55a587afdea2d`;
- dictionary after: `aa23cf40154c49d0cbd285c691445eb472ad7a9cd2bcd661a2615efd01f38c81`;
- corpus before and after: `0183a6305d0dc0a9737cad10eebaf47cd881ba12575f4cb47702fd3b0001f854`.

Generation and verification produce 1,394 pages, check 57,228 links across
1,388 HTML pages, and confirm 1,275 dictionary entries, 108 public records,
and 7,149 public lines. A second generation is deterministic.
