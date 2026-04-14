import json
import re
import unicodedata
from pathlib import Path

import pdfplumber


# ---------------------------------
# FILE PATHS
# ---------------------------------
PDF_PATH = Path("data/reg_kds.pdf")
HYMNS_JSON_PATH = Path("data/hymns_dataset.json")
OUTPUT_JSON_PATH = Path("data/hymns_dataset_updated.json")


# ---------------------------------
# TEXT HELPERS
# ---------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ---------------------------------
# TEXT HELPERS
# ---------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_parenthetical(text: str) -> str:
    """
    Remove things like:
    (Litaniet), (Nytår), (Vægterversene)
    """
    text = clean_text(text)
    text = re.sub(r"\s*\([^)]*\)", "", text)
    return clean_text(text)


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    text = text.replace("a.p.", "ap")
    text = text.replace("c. e. f.", "cef")
    text = text.replace("j. p. e.", "jpe")
    text = text.replace("h. o. c.", "hoc")

    text = re.sub(r"[^a-z0-9æøå\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------
# PDF PARSING
# ---------------------------------
def parse_chorale_pdf(pdf_path: Path) -> list[dict]:
    chorales = []
    seen = set()

    def parse_text_block(text: str):
        current_number = None
        current_title_parts = []

        if not text:
            return

        lines = text.split("\n")

        for raw_line in lines:
            line = clean_text(raw_line)
            if not line:
                continue

            # New chorale entry
            match = re.match(r"^(\d+)\.\s+(.*)$", line)
            if match:
                # Save previous entry
                if current_number is not None:
                    full_title = clean_text(" ".join(current_title_parts))
                    key = (current_number, full_title)
                    if full_title and key not in seen:
                        seen.add(key)
                        chorales.append({
                            "chorale_number": current_number,
                            "chorale_title": full_title
                        })

                current_number = int(match.group(1))
                current_title_parts = [match.group(2)]

            else:
                # Continuation line
                if current_number is not None:
                    current_title_parts.append(line)

        # Save final entry in block
        if current_number is not None:
            full_title = clean_text(" ".join(current_title_parts))
            key = (current_number, full_title)
            if full_title and key not in seen:
                seen.add(key)
                chorales.append({
                    "chorale_number": current_number,
                    "chorale_title": full_title
                })

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            width = page.width
            height = page.height

            # Split page into left and right halves
            left_bbox = (0, 0, width / 2, height)
            right_bbox = (width / 2, 0, width, height)

            left_page = page.crop(left_bbox)
            right_page = page.crop(right_bbox)

            left_text = left_page.extract_text()
            right_text = right_page.extract_text()

            if not left_text and not right_text:
                print(f"Warning: no text on page {page_num}")
                continue

            parse_text_block(left_text)
            parse_text_block(right_text)

    return chorales


# ---------------------------------
# MATCHING HELPERS
# ---------------------------------
def find_chorale_candidates(search_text: str, chorales: list[dict]) -> list[dict]:
    """
    Find chorale entries whose title starts with the given text.
    """
    search_norm = normalize_text(search_text)
    matches = []

    if not search_norm:
        return matches

    for chorale in chorales:
        chorale_norm = normalize_text(chorale["chorale_title"])

        if chorale_norm.startswith(search_norm):
            matches.append(chorale)

    return matches

def find_candidates_from_melody_titles(melodies: list[str], chorales: list[dict]) -> list[dict]:
    """
    Fallback:
    Some hymns use another hymn/chorale title as their melody, e.g.
    'Et lidet barn så lysteligt' or 'Kraften fra det høje'.
    Try matching those melody texts directly against chorale titles.
    """
    results = []

    for melody in melodies:
        melody = clean_text(melody)

        # Skip empty or obviously non-title melody lines
        if not melody:
            continue
        if re.match(r"^\d+$", melody):
            continue
        if any(ch.isdigit() for ch in melody):
            # composer/year style melody line, skip for this fallback
            continue

        candidates = find_chorale_candidates(melody, chorales)
        results.extend(candidates)

    return deduplicate_chorales(results)


def melody_to_keywords(melody: str) -> list[str]:
    melody_norm = normalize_text(melody)

    possible_keywords = [
        "lossius",
        "berggreen",
        "weyse",
        "laub",
        "meidell",
        "rung",
        "hartmann",
        "lindeman",
        "ring",
        "kalhauge",
        "winding",
        "grundtvig",
        "schumann",
        "klug",
        "cruger",
        "cruger",
        "nielsen",
        "schop",
        "freylinghausen",
        "konig",
        "gebauer",
        "nutzhorn",
        "barnekow",
        "tysk",
        "svensk",
        "norsk",
        "dansk",
        "faroesk",
        "færøsk",
    ]

    found = [kw for kw in possible_keywords if kw in melody_norm]
    return list(set(found))


def filter_candidates_by_melody(candidates: list[dict], melodies: list[str]) -> list[dict]:
    """
    If multiple chorale candidates share the same hymn text,
    use melody keywords to narrow them down.
    """
    if not candidates:
        return []

    all_keywords = []
    for melody in melodies:
        all_keywords.extend(melody_to_keywords(melody))

    all_keywords = list(set(all_keywords))

    if not all_keywords:
        return candidates

    filtered = []
    for candidate in candidates:
        title_norm = normalize_text(candidate["chorale_title"])
        if any(keyword in title_norm for keyword in all_keywords):
            filtered.append(candidate)

    # If melody filtering finds nothing, keep the original candidates
    return filtered if filtered else candidates


def deduplicate_chorales(chorales: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for chorale in chorales:
        key = chorale["chorale_number"]
        if key not in seen:
            seen.add(key)
            result.append(chorale)

    return result


# ---------------------------------
# MAIN UPDATE FUNCTION
# ---------------------------------

def update_hymn_dataset(hymns_dataset: dict, chorales: list[dict]) -> dict:
    updated = {}

    for hymn_id, hymn in hymns_dataset.items():
        hymn_title = clean_text(hymn.get("hymn_title", ""))
        first_line = clean_text(hymn.get("first_line", ""))
        melodies = hymn.get("melodies", [])

        match_text = first_line if first_line else hymn_title

        # First attempt
        candidates = find_chorale_candidates(match_text, chorales)

        # Second attempt (strip parentheses)
        if not candidates:
            simplified_text = strip_parenthetical(match_text)
            if simplified_text != match_text:
                candidates = find_chorale_candidates(simplified_text, chorales)

        final_matches = filter_candidates_by_melody(candidates, melodies)
        final_matches = deduplicate_chorales(final_matches)

        # Fallback using melody titles
        if not final_matches:
            melody_title_matches = find_candidates_from_melody_titles(melodies, chorales)
            if melody_title_matches:
                final_matches = melody_title_matches

        updated_hymn = dict(hymn)
        updated_hymn["chorales"] = [
            {
                "chorale_number": c["chorale_number"],
                "chorale_title": c["chorale_title"]
            }
            for c in final_matches
        ]

        updated[hymn_id] = updated_hymn

        if not final_matches:
            print(f"NO MATCH -> hymn {hymn.get('hymn_number')}: {match_text}")
            print(f"  melodies: {melodies}")

    return updated


# ---------------------------------
# RUN
# ---------------------------------
def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if not HYMNS_JSON_PATH.exists():
        raise FileNotFoundError(f"Hymns JSON not found: {HYMNS_JSON_PATH}")

    print("Parsing chorale PDF...")
    chorales = parse_chorale_pdf(PDF_PATH)
    print(f"Parsed {len(chorales)} chorale entries")

    print("Loading hymn dataset...")
    with open(HYMNS_JSON_PATH, "r", encoding="utf-8") as f:
        hymns_dataset = json.load(f)

    print("Updating hymn dataset...")
    updated_dataset = update_hymn_dataset(hymns_dataset, chorales)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_dataset, f, ensure_ascii=False, indent=2)

    print(f"Saved updated dataset to: {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
