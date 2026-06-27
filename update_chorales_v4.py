"""Build reconciled DDS -> KDS links for the hymn finder.

Data sources:
- data/reg_kds.pdf              KDS number -> chorale title / title aliases
- data/melodihenvisning.pdf     DDS hymn -> KDS number(s) + verse count
- data/hymns_dataset.json       hymn metadata scraped from Den Danske Salmebog Online

Melodihenvisninger is the primary mapping, but it can omit a chorale that is
listed by exact title in the alphabetical KDS register. This script therefore
keeps the printed DDS -> KDS references and supplements them only with
conservative, exact title matches from reg_kds.pdf. It never uses fuzzy title
matching to discover additional KDS chorales.
"""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pdfplumber

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
CHORALE_REGISTER_PDF = Path("data/reg_kds.pdf")
MELODY_REFERENCE_PDF = Path("data/melodihenvisning.pdf")
HYMNS_JSON_PATH = Path("data/hymns_dataset.json")
OUTPUT_JSON_PATH = Path("data/hymns_dataset_updated.json")
AUDIT_JSON_PATH = Path("data/melody_mapping_audit.json")

KDS_CODE_RE = re.compile(r"^\d+(?:[ab])?$")

# The printed reference PDF contains one visually merged cell for DDS 380.
# It means KDS 439 and 63, with 11 verses. Keep this explicit rather than
# silently accepting the OCR/text-extraction artefact "6311".
REFERENCE_OVERRIDES: dict[str, dict[str, Any]] = {
    "380": {"kds_codes": ["439", "63"], "verse_count": 11},
    # DDS 438 is printed as "Nadver C", not a KDS chorale number.
    "438": {"kds_codes": [], "verse_count": None, "special_reference": "Nadver C"},
}


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------
def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalize_match_text(value: str | None) -> str:
    """Normalize titles and composer labels for a conservative comparison."""
    text = clean_text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    replacements = {"æ": "ae", "ø": "o", "å": "a", "ö": "o", "ä": "a", "ü": "u", "hoffmann": "hoffman"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def composer_key(value: str | None) -> str | None:
    """Return the likely surname from a composer/year-style label, if present."""
    normalized = normalize_match_text(value)
    if not normalized or not re.search(r"\b(?:1[4-9]\d{2}|20\d{2})\b", normalized):
        return None
    words = [word for word in normalized.split() if not word.isdigit()]
    if not words:
        return None
    candidate = words[-1]
    non_names = {"arh", "melodi", "visemelodi", "hymne", "psalter", "sangbog", "dansk", "norsk", "svensk", "tysk", "engelsk", "fransk"}
    return None if candidate in non_names else candidate


def variant_label(chorale_title: str) -> str | None:
    match = re.search(r"\(([^()]*)\)\s*$", clean_text(chorale_title))
    if not match:
        return None
    label = normalize_match_text(match.group(1))
    if label in {"", "a b", "a", "b"}:
        return None
    return label


def similar_titles(left: str | None, right: str | None) -> bool:
    left_norm, right_norm = normalize_match_text(left), normalize_match_text(right)
    if not left_norm or not right_norm:
        return False
    if left_norm in right_norm or right_norm in left_norm:
        return True
    return SequenceMatcher(None, left_norm, right_norm).ratio() >= 0.90


def kds_base(code: str) -> str:
    """24a / 24b share one register entry: 24."""
    return re.sub(r"[ab]$", "", str(code))


def kds_sort_key(code: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)([ab])?", str(code))
    if not match:
        return (9999, 9)
    return (int(match.group(1)), {None: 0, "a": 1, "b": 2}[match.group(2)])


def unique_in_order(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, dict) else str(item)
        if marker not in seen:
            seen.add(marker)
            result.append(item)
    return result


def register_title_aliases(title: str | None) -> list[str]:
    """Return exact-match aliases from an alphabetical-register title.

    KDS titles often add a composer/arrangement in parentheses, and a few
    entries list more than one hymn title separated by ``/``. Parenthetical
    labels are not part of the title comparison, while slash-separated titles
    are kept as individual aliases.
    """
    without_parentheses = clean_text(re.sub(r"\([^()]*\)", "", clean_text(title)))
    aliases = [
        normalize_match_text(part)
        for part in re.split(r"\s*/\s*", without_parentheses)
    ]
    return [alias for alias in unique_in_order(aliases) if alias]


def build_register_title_index(
    register: dict[str, dict[str, str]],
) -> dict[str, list[str]]:
    """Build normalized title/alias -> KDS base-code lookup."""
    index: dict[str, list[str]] = {}
    for code, entry in register.items():
        for alias in register_title_aliases(entry["chorale_title"]):
            index.setdefault(alias, []).append(code)

    for alias, codes in index.items():
        index[alias] = unique_in_order(codes)
    return index


def expand_base_code_to_known_variants(
    code: str,
    reference_codes: list[str],
) -> list[str]:
    """Prefer printed 24a/24b-style references over an unsuffixed base code."""
    base = kds_base(code)
    variants = [
        reference_code
        for reference_code in reference_codes
        if kds_base(reference_code) == base and reference_code != base
    ]
    return unique_in_order(variants or [code])


def reconcile_kds_codes(
    hymn: dict[str, Any],
    reference_codes: list[str],
    register_title_index: dict[str, list[str]],
) -> tuple[list[str], dict[str, list[str]]]:
    """Combine printed references with conservative exact register matches.

    Priority/order:
    1. Exact match to the hymn title or first line in the KDS register.
    2. Exact match to a source melody title in the KDS register.
    3. The printed DDS -> KDS references from Melodihenvisninger.

    The first two steps are supplements, not replacements. The output stores
    provenance for each KDS code so later audits can identify which options
    were added from the alphabetical register.
    """
    code_sources: dict[str, list[str]] = {}
    reconciled_codes: list[str] = []

    def add_code(code: str, source: str) -> None:
        if code not in reconciled_codes:
            reconciled_codes.append(code)
        code_sources.setdefault(code, [])
        if source not in code_sources[code]:
            code_sources[code].append(source)

    def add_exact_matches(values: list[str], source: str) -> None:
        for value in values:
            for alias in register_title_aliases(value):
                for base_code in register_title_index.get(alias, []):
                    for code in expand_base_code_to_known_variants(
                        base_code, reference_codes
                    ):
                        add_code(code, source)

    # A hymnal title / first line is the strongest supplemental evidence.
    add_exact_matches(
        [
            clean_text(hymn.get("hymn_title")),
            clean_text(hymn.get("first_line")),
        ],
        "alphabetical_register_title",
    )

    # A source-melody label can identify an alternative tune title directly.
    add_exact_matches(
        [
            clean_text(item)
            for item in hymn.get("melodies", [])
            if clean_text(item)
        ],
        "alphabetical_register_source_melody",
    )

    for code in reference_codes:
        add_code(code, "melodihenvisning")

    return reconciled_codes, code_sources


# -----------------------------------------------------------------------------
# Parse the alphabetical KDS register (reg_kds.pdf)
# -----------------------------------------------------------------------------
def parse_chorale_register(pdf_path: Path) -> dict[str, dict[str, str]]:
    """Return a lookup such as {'54': {'chorale_number': '54', ...}}."""
    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def parse_text_block(text: str | None) -> None:
        current_number: str | None = None
        current_title_parts: list[str] = []

        def save_current() -> None:
            if current_number is None:
                return
            title = clean_text(" ".join(current_title_parts))
            key = (current_number, title)
            if title and key not in seen:
                seen.add(key)
                entries.append({"chorale_number": current_number, "chorale_title": title})

        for raw_line in (text or "").splitlines():
            line = clean_text(raw_line)
            if not line:
                continue

            match = re.match(r"^(\d+)\.\s+(.*)$", line)
            if match:
                save_current()
                current_number = match.group(1)
                current_title_parts = [match.group(2)]
            elif current_number is not None:
                current_title_parts.append(line)

        save_current()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # This PDF has two columns; cropping prevents text from the columns
            # becoming interleaved.
            width, height = page.width, page.height
            parse_text_block(page.crop((0, 0, width / 2, height)).extract_text())
            parse_text_block(page.crop((width / 2, 0, width, height)).extract_text())

    lookup: dict[str, dict[str, str]] = {}
    for entry in entries:
        # One entry per base KDS number is expected. Keep the first occurrence.
        lookup.setdefault(entry["chorale_number"], entry)
    return lookup


# -----------------------------------------------------------------------------
# Parse Melodihenvisninger (DDS hymn -> KDS codes + verse count)
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Turn KDS codes into selectable options
# -----------------------------------------------------------------------------
def make_chorale_options(
    kds_codes: list[str],
    register: dict[str, dict[str, str]],
    recordings: list[str],
    source_melodies: list[str],
    mapping_sources_by_code: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[str], list[dict[str, Any]]]:
    """Build one selectable option for every KDS code.

    Important: codes such as ``2a`` and ``2b`` are separate entries in
    Melodihenvisninger. They must remain separate selectable options, even
    though the alphabetical KDS register stores their shared title under the
    base number ``2``. The base number is used only for the title lookup.

    Recording labels are paired only when their count equals the number of
    *individual* printed KDS codes. Otherwise the script preserves every KDS
    option but does not invent a one-to-one recording association.
    """
    options: list[dict[str, Any]] = []
    flat_chorales: list[dict[str, str]] = []
    missing_register_codes: list[str] = []
    assignment_audit: list[dict[str, Any]] = []
    can_pair_recordings = bool(recordings) and len(recordings) == len(kds_codes)

    for index, code in enumerate(kds_codes):
        base = kds_base(code)
        register_entry = register.get(base)

        if register_entry:
            title = register_entry["chorale_title"]
        else:
            title = "KDS entry not found in alphabetical register"
            missing_register_codes.append(code)

        recording_label = recordings[index] if can_pair_recordings else None
        source_melody = source_melodies[index] if len(source_melodies) == len(kds_codes) else None
        recording_composer = composer_key(recording_label)
        title_variant = variant_label(title)

        if recording_composer and title_variant and recording_composer == title_variant:
            match_method = "composer_label"
        elif source_melody and similar_titles(source_melody, title):
            match_method = "source_melody_title"
        elif can_pair_recordings:
            # Order is a useful provisional pairing, but must be reviewed if
            # the register cannot distinguish the variants (for example 2a/2b).
            match_method = "same_order_unverified"
        else:
            match_method = "unassigned"

        option = {
            "option_id": f"kds:{code}",
            "kds_codes": [code],
            "display_kds": code,
            "chorale_title": title,
            "recording_melody": recording_label,
            "source_melody": source_melody,
            "recording_match_method": match_method,
            "mapping_sources": mapping_sources_by_code.get(code, []),
        }
        assignment_audit.append({
            "display_kds": code,
            "recording_melody": recording_label,
            "source_melody": source_melody,
            "match_method": match_method,
        })
        options.append(option)
        flat_chorales.append({"chorale_number": code, "chorale_title": title})

    return options, flat_chorales, missing_register_codes, assignment_audit


# -----------------------------------------------------------------------------
# Dataset generation and audit
# -----------------------------------------------------------------------------
def update_hymn_dataset(
    hymns_dataset: dict[str, dict[str, Any]],
    register: dict[str, dict[str, str]],
    references: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    updated: dict[str, dict[str, Any]] = {}
    register_title_index = build_register_title_index(register)
    audit: dict[str, Any] = {
        "summary": {
            "hymns_in_dataset": len(hymns_dataset),
            "hymns_with_reference_mapping": 0,
            "hymns_without_any_mapping": [],
            "special_non_kds_references": [],
            "recording_count_mismatches": [],
            "missing_register_entries": [],
            "unverified_recording_assignments": [],
            "register_supplemental_codes": [],
        },
        "by_hymn": {},
    }

    for hymn_id, hymn in hymns_dataset.items():
        updated_hymn = dict(hymn)
        reference = references.get(hymn_id)
        reference_codes = list(reference.get("kds_codes", [])) if reference else []
        recordings = [
            clean_text(item)
            for item in hymn.get("recording_melodies", [])
            if clean_text(item)
        ]
        source_melodies = [
            clean_text(item)
            for item in hymn.get("melodies", [])
            if clean_text(item)
        ]

        kds_codes, mapping_sources_by_code = reconcile_kds_codes(
            hymn,
            reference_codes,
            register_title_index,
        )

        if not kds_codes:
            updated_hymn["chorale_options"] = []
            updated_hymn["chorales"] = []
            audit["summary"]["hymns_without_any_mapping"].append(hymn_id)
            updated[hymn_id] = updated_hymn
            continue

        if reference:
            audit["summary"]["hymns_with_reference_mapping"] += 1

        options, flat_chorales, missing_register_codes, assignment_audit = make_chorale_options(
            kds_codes,
            register,
            recordings,
            source_melodies,
            mapping_sources_by_code,
        )

        # Melodihenvisninger remains the verse-count source when it has a value.
        if reference and isinstance(reference.get("verse_count"), int):
            updated_hymn["verse_count"] = reference["verse_count"]

        updated_hymn["chorale_options"] = options
        updated_hymn["chorales"] = flat_chorales

        if reference and reference.get("special_reference"):
            updated_hymn["special_reference"] = reference["special_reference"]
            audit["summary"]["special_non_kds_references"].append(
                {"hymn_number": hymn_id, "reference": reference["special_reference"]}
            )

        supplemental_codes = [
            {
                "kds_code": code,
                "sources": sources,
            }
            for code, sources in mapping_sources_by_code.items()
            if any(source.startswith("alphabetical_register") for source in sources)
            and "melodihenvisning" not in sources
        ]
        if supplemental_codes:
            audit["summary"]["register_supplemental_codes"].append(
                {"hymn_number": hymn_id, "codes": supplemental_codes}
            )

        if recordings and len(recordings) != len(options):
            audit["summary"]["recording_count_mismatches"].append(
                {
                    "hymn_number": hymn_id,
                    "recording_melodies": recordings,
                    "kds_option_count": len(options),
                    "kds_codes": kds_codes,
                }
            )

        if missing_register_codes:
            audit["summary"]["missing_register_entries"].append(
                {"hymn_number": hymn_id, "kds_codes": missing_register_codes}
            )

        unverified = [
            item
            for item in assignment_audit
            if item["match_method"] == "same_order_unverified"
        ]
        if unverified:
            audit["summary"]["unverified_recording_assignments"].append(
                {"hymn_number": hymn_id, "assignments": unverified}
            )

        audit["by_hymn"][hymn_id] = {
            "reference_kds_codes": reference_codes,
            "reconciled_kds_codes": kds_codes,
            "mapping_sources": mapping_sources_by_code,
            "verse_count": reference.get("verse_count") if reference else None,
            "recording_count": len(recordings),
            "kds_option_count": len(options),
            "recording_pairing": assignment_audit,
        }
        updated[hymn_id] = updated_hymn

    audit["summary"]["hymns_without_any_mapping_count"] = len(
        audit["summary"]["hymns_without_any_mapping"]
    )
    return updated, audit

def main() -> None:
    for path in (CHORALE_REGISTER_PDF, MELODY_REFERENCE_PDF, HYMNS_JSON_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    print("Parsing alphabetical KDS register...")
    register = parse_chorale_register(CHORALE_REGISTER_PDF)
    print(f"Parsed {len(register)} KDS register entries")

    print("Parsing DDS → KDS melody references...")
    references = parse_melody_reference_pdf(MELODY_REFERENCE_PDF)
    print(f"Parsed reference mappings for {len(references)} DDS entries")

    with HYMNS_JSON_PATH.open("r", encoding="utf-8") as file:
        hymns_dataset = json.load(file)

    print("Generating authoritative chorale mappings...")
    updated_dataset, audit = update_hymn_dataset(hymns_dataset, register, references)

    with OUTPUT_JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(updated_dataset, file, ensure_ascii=False, indent=2)
    with AUDIT_JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(audit, file, ensure_ascii=False, indent=2)

    print(f"Saved updated dataset: {OUTPUT_JSON_PATH}")
    print(f"Saved audit report:    {AUDIT_JSON_PATH}")
    print(f"No KDS mapping found:     {audit['summary']['hymns_without_any_mapping_count']}")
    print(f"Register supplements:     {len(audit['summary']['register_supplemental_codes'])}")
    print(f"Recording/KDS mismatches: {len(audit['summary']['recording_count_mismatches'])}")
    print(f"Unverified recording assignments: {len(audit['summary']['unverified_recording_assignments'])}")


if __name__ == "__main__":
    main()
