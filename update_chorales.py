"""Build and validate all DDS -> KDS links from explicit source references.

Website recording URLs supplement the printed reference; titles are display
metadata, never evidence that two hymns use the same tune.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any
import pdfplumber

ROOT = Path(__file__).resolve().parent
CHORALE_REGISTER_PDF = ROOT / 'data/reg_kds.pdf'
MELODY_REFERENCE_PDF = ROOT / 'data/melodihenvisning.pdf'
HYMNS_JSON_PATH = ROOT / 'data/hymns_dataset.json'
OUTPUT_JSON_PATH = ROOT / 'data/hymns_dataset_updated.json'
AUDIT_JSON_PATH = ROOT / 'data/melody_mapping_audit.json'
KDS_CODE_RE = re.compile(r'^\d+(?:[ab])?$')
# The printed row reads "439 / 6311". The website's numbered verse rows
# and explicit /380/311 recording URL disambiguate it: six verses, KDS 311.
REFERENCE_OVERRIDES = {
    '380': {'kds_codes': ['439', '311'], 'verse_count': 6},
    '438': {'kds_codes': [], 'verse_count': None, 'special_reference': 'Nadver C'},
}
# Reviewed conflicts, not title-similarity guesses. Evidence is recorded in
# data/reference_corrections.json and copied into the generated audit.
LITURGICAL_PAGE_REFERENCES = {
    ('568', 'Hellig, hellig, hellig er Herren'),
    ('570', 'O Guds Lam uskyldig (Agnus Dei)'),
    ('571', 'O du Guds Lam uskyldig, du, som'),
}
CORRECTIONS_PATH = ROOT / 'data/reference_corrections.json'


def clean_text(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def unique_in_order(items):
    return list(dict.fromkeys(items))


def kds_base(code):
    return re.sub(r'[ab]$', '', str(code))


def parse_chorale_register(pdf_path):
    # Read columns in order but retain the current entry across column/page
    # boundaries (KDS 294 continues on page 4). Exclude headers and footers.
    entries = {}
    current = None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for left, right in [(0, page.width / 2), (page.width / 2, page.width)]:
                text = page.crop((left, 70, right, page.height - 60)).extract_text() or ''
                for line in text.splitlines():
                    line = clean_text(line)
                    match = re.match(r'^(\d+)\.\s+(.*)$', line)
                    if match:
                        current, title = match.groups()
                        if (current, title) in LITURGICAL_PAGE_REFERENCES:
                            current = None
                            continue
                        if current in entries:
                            raise ValueError(f'Duplicate register code {current}')
                        entries[current] = {'chorale_number': current, 'chorale_title': title}
                    elif line and current:
                        entries[current]['chorale_title'] += ' ' + line
    if set(entries) != set(map(str, range(1, 569))):
        raise ValueError('Incomplete KDS register')
    return entries


def parse_melody_reference_pdf(pdf_path: Path) -> dict[str, dict[str, Any]]:
    """Parse the four-column table using word coordinates, not text order.

    A plain ``extract_text`` call mixes the four visual columns. The document
    uses stable x coordinates for DDS, KDS and v, so reading each column by
    position is much more reliable.
    """
    references: dict[str, dict[str, Any]] = {}
    # x positions of the DDS field in the PDF's four printed columns.
    column_starts = (56.7, 157.7, 258.7, 359.7)
    field_spacing = 27.0

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(keep_blank_chars=False, use_text_flow=True)

            for start_x in column_starts:
                column_words = [
                    word
                    for word in words
                    if start_x - 8 <= word["x0"] < start_x + 72
                    and 60 <= word["top"] <= page.height - 35
                ]

                rows: list[dict[str, Any]] = []
                for word in sorted(column_words, key=lambda item: (item["top"], item["x0"])):
                    if not rows or abs(rows[-1]["top"] - word["top"]) > 2:
                        rows.append({"top": word["top"], "words": [word]})
                    else:
                        rows[-1]["words"].append(word)

                current_hymn: str | None = None

                for row in rows:
                    cells = ["", "", ""]  # DDS, KDS, verses
                    for word in row["words"]:
                        relative_x = word["x0"] - start_x
                        field_index = min(range(3), key=lambda index: abs(relative_x - index * field_spacing))
                        if abs(relative_x - field_index * field_spacing) <= 12:
                            # Some codes are extracted as separate '2' and 'a'
                            # words; joining them gives the correct KDS code 2a.
                            cells[field_index] += word["text"]

                    dds_code, kds_code, verse_count = cells

                    if dds_code.isdigit() and KDS_CODE_RE.fullmatch(kds_code or ""):
                        current_hymn = dds_code
                        record = references.setdefault(
                            current_hymn,
                            {"kds_codes": [], "verse_count": None, "special_reference": None},
                        )
                        record["kds_codes"].append(kds_code)
                        if verse_count.isdigit():
                            record["verse_count"] = int(verse_count)

                    elif not dds_code and KDS_CODE_RE.fullmatch(kds_code or "") and current_hymn:
                        record = references[current_hymn]
                        record["kds_codes"].append(kds_code)
                        # A few rows put the verse count beside the final KDS code.
                        if verse_count.isdigit() and record["verse_count"] is None:
                            record["verse_count"] = int(verse_count)

    for record in references.values():
        record["kds_codes"] = unique_in_order(record["kds_codes"])

    # Correct the small number of PDF text-extraction edge cases explicitly.
    for hymn_number, override in REFERENCE_OVERRIDES.items():
        record = references.setdefault(hymn_number, {"kds_codes": [], "verse_count": None, "special_reference": None})
        record.update(override)

    return references


def update_hymn_dataset(hymns, register, references):
    corrections = json.loads(CORRECTIONS_PATH.read_text(encoding='utf-8'))
    result, by_hymn = {}, {}
    for hymn_id, hymn in hymns.items():
        reference = references[hymn_id]
        web_codes = [r['kds_code'] for r in hymn['recordings'] if r['kds_code']]
        ref_codes = reference['kds_codes']
        codes = []
        sources = {}
        for code, source in [(c, 'website_recording_url') for c in web_codes] + [(c, 'melodihenvisning') for c in ref_codes]:
            # A recording for base 24 applies to the tune, while the printed
            # reference retains separately selectable arrangements 24a and 24b.
            variants = [c for c in ref_codes if kds_base(c) == code and c != code]
            for expanded in variants or [code]:
                if expanded not in codes:
                    codes.append(expanded)
                sources.setdefault(expanded, [])
                if source not in sources[expanded]:
                    sources[expanded].append(source)
        correction = corrections.get(hymn_id)
        if correction:
            codes = correction['kds_codes']
            sources = {c: unique_in_order(sources.get(c, []) + ['reviewed_correction']) for c in codes}

        count = hymn['verse_count']
        count_source = hymn['verse_count_source']
        if count is None:
            count, count_source = reference['verse_count'], 'melodihenvisning'
        options = []
        for code in codes:
            title = register[kds_base(code)]['chorale_title']
            recordings = [r for r in hymn['recordings'] if r['kds_code'] == code]
            method = 'recording_url' if recordings else 'unassigned'
            if not recordings and code != kds_base(code):
                recordings = [r for r in hymn['recordings'] if r['kds_code'] == kds_base(code)]
                if recordings:
                    method = 'recording_base_code'
            recording = recordings[0] if len(recordings) == 1 else None
            options.append({
                'option_id': f'kds:{code}', 'kds_codes': [code], 'display_kds': code,
                'chorale_title': title,
                'recording_melody': recording['label'] if recording else None,
                'recording_url': recording['url'] if recording else None,
                'source_melody': None,  # Free-text melody labels have no positional association.
                'recording_match_method': method if recording else 'unassigned',
                'mapping_sources': sources[code],
            })
        updated = {**hymn, 'verse_count': count, 'verse_count_source': count_source,
                   'chorales': [{'chorale_number': o['display_kds'], 'chorale_title': o['chorale_title']} for o in options],
                   'chorale_options': options}
        special = (correction or {}).get('special_reference') or reference.get('special_reference')
        if special:
            updated['special_reference'] = special
        if correction and correction.get('book_page'):
            updated['book_page'] = correction['book_page']
            updated['book_page_label'] = correction['book_page_label']
        result[hymn_id] = updated
        by_hymn[hymn_id] = {
            'website_kds_codes': web_codes, 'reference_kds_codes': ref_codes,
            'resolved_kds_codes': codes, 'mapping_sources': sources,
            'book_reference': ({'page_number': updated['book_page'],
                                'label': updated['book_page_label'], 'volume': 'I',
                                'source': correction['evidence_url']}
                               if updated.get('book_page') else None),
            'website_verse_count': hymn['verse_count'], 'reference_verse_count': reference['verse_count'],
            'resolved_verse_count': count, 'verse_count_source': count_source,
            'reviewed_correction': correction,
            'options_without_recordings': [o['display_kds'] for o in options if not o['recording_url']],
        }
    summary = {
        'hymns_audited': len(result), 'register_entries': len(register),
        'reference_entries': len(references),
        'liturgical_page_references_excluded': [list(item) for item in sorted(LITURGICAL_PAGE_REFERENCES)],
        'verse_counts_from_pdf': [i for i, h in result.items() if h['verse_count_source'] == 'melodihenvisning'],
        'verse_count_conflicts': [i for i, h in by_hymn.items() if h['website_verse_count'] is not None and h['reference_verse_count'] is not None and h['website_verse_count'] != h['reference_verse_count']],
        'mapping_source_differences': [i for i, h in by_hymn.items() if {kds_base(c) for c in h['website_kds_codes']} != {kds_base(c) for c in h['reference_kds_codes']}],
        'reviewed_corrections': list(corrections),
        'reference_extraction_corrections': REFERENCE_OVERRIDES,
    }
    return result, {'summary': summary, 'by_hymn': by_hymn}


def validate_dataset(dataset, register, references):
    expected = set(map(str, range(1, 792)))
    if set(dataset) != expected or set(references) != expected:
        raise ValueError('Expected every hymn from 1 through 791')
    for key, hymn in dataset.items():
        if hymn['hymn_number'] != int(key) or not hymn['hymn_title']:
            raise ValueError(f'{key}: invalid identity')
        if type(hymn['verse_count']) is not int or hymn['verse_count'] <= 0:
            raise ValueError(f'{key}: invalid verse count')
        if 'book_page' in hymn:
            if type(hymn['book_page']) is not int or hymn['book_page'] <= 0 or not isinstance(hymn.get('book_page_label'), str) or not hymn['book_page_label'].strip():
                raise ValueError(f'{key}: invalid book-page reference')
        elif hymn.get('book_page_label'):
            raise ValueError(f'{key}: book label without a page number')
        options = hymn['chorale_options']
        codes = [o['display_kds'] for o in options]
        if (not codes and not hymn.get('book_page')) or len(codes) != len(set(codes)):
            raise ValueError(f'{key}: missing/duplicate chorales')
        for o in options:
            code = o['display_kds']
            if not KDS_CODE_RE.fullmatch(code) or kds_base(code) not in register:
                raise ValueError(f'{key}: invalid chorale {code}')
            if o['option_id'] != f'kds:{code}' or o['kds_codes'] != [code] or not o['mapping_sources']:
                raise ValueError(f'{key}: inconsistent option {code}')
            if o['recording_url']:
                matches = [r for r in hymn['recordings'] if r['url'] == o['recording_url'] and r['label'] == o['recording_melody']]
                if len(matches) != 1:
                    raise ValueError(f'{key}: unsupported recording label')
                source_code = matches[0]['kds_code']
                if o['recording_match_method'] != 'reviewed_correction' and source_code not in {code, kds_base(code)}:
                    raise ValueError(f'{key}: recording points to another chorale')
        if hymn['chorales'] != [{'chorale_number': o['display_kds'], 'chorale_title': o['chorale_title']} for o in options]:
            raise ValueError(f'{key}: flat/structured options diverge')


def generate():
    register = parse_chorale_register(CHORALE_REGISTER_PDF)
    references = parse_melody_reference_pdf(MELODY_REFERENCE_PDF)
    hymns = json.loads(HYMNS_JSON_PATH.read_text(encoding='utf-8'))
    dataset, audit = update_hymn_dataset(hymns, register, references)
    validate_dataset(dataset, register, references)
    return dataset, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify committed outputs without modifying files')
    args = parser.parse_args()
    dataset, audit = generate()
    for path, content in [(OUTPUT_JSON_PATH, dataset), (AUDIT_JSON_PATH, audit)]:
        text = json.dumps(content, ensure_ascii=False, indent=2) + '\n'
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != text:
                raise SystemExit(f'Stale generated file: {path}. Run python update_chorales.py')
        else:
            path.write_text(text, encoding='utf-8')
    print(f'Validated {len(dataset)} hymns; ' + ('committed outputs match.' if args.check else 'outputs regenerated.'))


if __name__ == '__main__':
    main()
