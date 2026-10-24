# Dataset audit — 24 October 2026

Audited all 791 website hymn pages, all 791 rows of the supplied melody reference,
and all 568 numbered chorales in the supplied alphabetical register. The
application loads `data/hymns_dataset_updated.json`. At the audited main revision
(`5560bdc`), Hymn 5 already had seven verses and chorales 424 and 563. The
README's older rebuild command could lose this and other previous repairs.
Hymn 5 is now an explicit regression test of both data generation and rendering.

## Root causes and fixes

- **Competing builders:** the documented `update_chorales.py` used title prefixes
  and composer keywords, discarding secondary melodies. `update_chorales_v4.py`
  had different rules and silently supplemented links using ambiguous titles.
  Both commands now use one deterministic, validated implementation.
- **Lost source identifiers:** the scraper flattened HTML into lines, throwing
  away explicit `/salme/<hymn>/<chorale>` URLs and full recording labels in link
  attributes. Labels were then assigned by array position, even when chorale
  order differed. Store the URL, code and full label together; assign by code,
  retaining separate `a`/`b` choices. A base-code recording identifies the tune
  for those arrangements, not a specific arrangement. PDF-only options have no
  invented recording attribution. Free-text melody labels are never paired by
  position or used to discover links by title similarity.
- **Verse parsing:** whole-page number scanning confused hymn numbers and Bible
  references with verse labels; manual overrides could replace correct counts
  (for example, hymn 285 has four website verse rows, not eight). Parse numbered
  rows of `table#salme` with an HTML5 parser that repairs invalid nesting. Count
  774 hymns from the source table. The other **17** omit verse text on the website
  and use the PDF counts, with explicit provenance. No zero/one default is used.
- **Melody parsing:** heuristic length/capitalization filters missed long titles
  and single-word labels. Read the melody metadata block, merge wrapped lines,
  and stop at performance instructions. This restores the secondary label for
  131, `Spiritual` for 470, and the wrapped labels for 504 and 734.
- **PDF boundaries:** footers leaked into 11 register titles, and KDS 294's title
  continued onto the next page. Exclude page furniture and preserve continuation
  state across columns and pages. Validate every numbered entry.
- **Misread merged cell:** the previous special case for hymn 380 interpreted
  printed `6311` as chorale 63 plus eleven verses. The website has six verse rows
  and an explicit `/380/311` link. Resolve it as six verses, chorales 439 and 311.
- **Liturgical page numbers:** the register prints Sanctus page 568, Agnus Dei
  page 570, and another liturgical page 571 in the same style as chorale entries.
  The old parser kept the first 568, mislabelling the actual chorale 568
  (*Ånden opgav enkesønnen*). Exclude the three page references from the numbered
  register. Keep the useful numbers visible as **Koralbog, bind I, side 568**
  for hymn 438 and **side 570** for hymn 440. Hymn 440 also retains the
  melody-reference PDF’s explicit chorale 416 alternative, without attributing
  the website’s nonnumeric recording to it. The [editorial preface](https://www.thor-callesen.com/koralbog/pdf/forord_brinth.pdf)
  explicitly describes the Sanctus and Agnus Dei references as page numbers in
  Bind I, 2. del (Højmesseordning).

## Source policy and reviewed differences

Website recording URLs and printed DDS-to-KDS references provide link evidence.
Preserve their union, including printed alternatives without recordings, unless
an explicit reviewed correction applies. An equal title alone is insufficient:
the register contains aliases for multiple tunes and distinct liturgical forms.
Each option records its source. `data/reference_corrections.json` records the
reviewed liturgical distinctions with reasons and URLs.
The generated audit lists the source and resolved values for every hymn.

Numbered website verse rows take precedence over PDF verse counts. After fixing
380's extraction, the remaining discrepancy is hymn 369: the website has six
verses, while the PDF says seven. The output uses six and retains the discrepancy
in the audit. The PDF's blank counts for 419, 420 and 438 do not erase available
website counts.

The source lists differ in 34 hymns (after resolving 380). These differences do
not imply 34 errors: several printed alternatives have no website recording.
The audit preserves both lists and documents all four reviewed exceptions.

## Live site versus repository baseline

On re-checking `https://hellokim.me/hymns/` on 24 October 2026, its HTML and JSON
were different from the repository baseline audited above. The live site served
older-format data without `chorale_options`; for example, Hymn 5 had only 424 and
Hymn 790 had only 156. The PR is unmerged and has not been deployed by this work.
The original table's **Before** column meant repository commit `5560bdc`, not the
live website. No claim is made about which deployment mechanism caused the drift.

| Hymn | Live site when re-checked | Repository baseline 5560bdc | Proposed PR | Basis |
| --- | --- | --- | --- | --- |
| 239 | 531 | 143, 531 | 531 | Both explicit sources identify 531; 143 was inferred from an alias |
| 380 | 439 | 439, 311, 63 | 439, 311 | Resolve merged PDF cell against source rows/URL |
| 432 | 201, 202 | 201, 202 | 202 | Litany; explicit URL and register qualifier |
| 433 | 201 | 201, 202 | 201 | Kyrie; explicit URL and register qualifier |
| 438 | 568 | 568 | Book page 568 / Nadver C | Preserve numeric navigation, distinguish page from chorale 568 |
| 440 | 570 | 570, 416 | Book page 570 plus chorale 416 | Preserve both explicit references, without guessing recording association |
| 597 | 493 | 493, 63, 423 | 493, 63 | Both explicit sources identify 493 and 63; 423 was inferred from an alias |
| 735 | 396 | 396, 364 | 396, 364, 109 | Explicit secondary recording URL |
| 790 | 156 | 156, 158a, 158b | 156, 158a, 158b | Preserve website 156 and printed alternatives 158a/158b |

The initial PR removed 158a/158b for hymn 790 because the website identified 156
and the register assigned a different title to 158. **That was insufficient
evidence:** a hymn can use another hymn's melody, and the website need not record
every printed alternative. That removal has been reversed. The PDF/website
disagreement remains documented in the generated audit; 158a/158b have no invented
recording labels. Their absence from the website does not establish a PDF error.
The same reasoning retains the PDF's explicit chorale 416 for hymn 440. Its
website recording `x` remains unassigned to 416.

Compared with the repository baseline, verse counts change for 369 (7 → 6) and 380 (11 → 6).
The raw scraper snapshot also corrects counts that the previous mapping script
happened to mask. Every source recording label is now stored in full instead of
truncated UI text. Chorale 568's corrected title benefits hymns 148, 151 and 388.

## Reproduction and validation

Install `requirements.txt`, then run:

```sh
python -m unittest discover -s tests -v
python update_chorales.py --check
node tests/test_frontend.cjs
```

The offline tests exercise actual reduced source HTML (verse lyrics replaced by
placeholders), malformed markup, missing lyrics, scripture numbers, long and
wrapped melodies, liturgical links, recording-order changes, PDF continuation
rows, suffix variants, cross-page titles and complete 791-hymn integrity.
The frontend checks render all 791 option sets, verify Hymn 5, exact numeric
search, saved preferences, discarded invalid choices, retained 790 alternatives, numeric book pages and
escaped service-order references. CI runs the same checks and fails if generated JSON or audit drift.

To refresh all metadata, use `python build_dataset.py --cache-dir .cache/hymns`,
then `python update_chorales.py`. A failed fetch/parse never writes a partial
metadata dataset. Source HTML is cached outside version control; the reviewed
snapshot's hashes are in `data/source_manifest.json`. Update that provenance
manifest deliberately when performing a new source audit. The tests need no
live website access.

This audit establishes consistency against the provided register/reference and
the current website. It does not claim to identify additional performance
alternatives absent from those sources. Printed alternatives without recordings
remain available without guessed composer labels.
