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
  register. Show service-order references for hymns 438 and 440 instead of fake
  chorale options. The [editorial preface](https://www.thor-callesen.com/koralbog/pdf/forord_brinth.pdf)
  explicitly describes the Sanctus and Agnus Dei references as page numbers in
  Bind I, 2. del (Højmesseordning).

## Source policy and reviewed differences

Website recording URLs and printed DDS-to-KDS references provide link evidence.
Preserve their union, including printed alternatives without recordings, unless
an explicit reviewed correction applies. An equal title alone is insufficient:
the register contains aliases for multiple tunes and distinct liturgical forms.
Each option records its source. `data/reference_corrections.json` records the
reviewed liturgical distinctions and hymn 790 correction with reasons and URLs.
The generated audit lists the source and resolved values for every hymn.

Numbered website verse rows take precedence over PDF verse counts. After fixing
380's extraction, the remaining discrepancy is hymn 369: the website has six
verses, while the PDF says seven. The output uses six and retains the discrepancy
in the audit. The PDF's blank counts for 419, 420 and 438 do not erase available
website counts.

The source lists differ in 34 hymns (after resolving 380). These differences do
not imply 34 errors: several printed alternatives have no website recording.
The audit preserves both lists and documents all five reviewed exceptions.

Changes to chorale sets compared with the original committed application data:

| Hymn | Before | After | Basis |
| --- | --- | --- | --- |
| 239 | 143, 531 | 531 | Both explicit sources identify 531; 143 was an inferred title-alias match |
| 380 | 439, 311, 63 | 439, 311 | Resolve merged PDF cell against source rows/URL |
| 432 | 201, 202 | 202 | Litany, not Kyrie; explicit URL and register qualifier |
| 433 | 201, 202 | 201 | Kyrie, not Litany; explicit URL and register qualifier |
| 438 | 568 | Nadver C / Sanctus | Liturgical page reference, not chorale 568 |
| 440 | 570, 416 | Agnus Dei / højmesseordningen | Liturgical page reference; 416 is a different text/tune |
| 597 | 493, 63, 423 | 493, 63 | Both explicit sources identify 493 and 63; 423 was inferred from an alias |
| 735 | 396, 364 | 396, 364, 109 | Explicit secondary recording URL omitted by previous title matching |
| 790 | 156, 158a, 158b | 156 | Website URL/composer and register title agree; PDF points to a different hymn |

The published dataset's verse counts change for 369 (7 → 6) and 380 (11 → 6).
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
search, saved preferences, discarded invalid choices and escaped service-order
references. CI runs the same checks and fails if generated JSON or audit drift.

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
