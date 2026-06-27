from pathlib import Path

import time
import json
import re
import unicodedata
import requests
from bs4 import BeautifulSoup


# ---------------------------------
# CONFIG
# ---------------------------------
OUTPUT_JSON_PATH = Path("data/hymns_dataset.json")

START_HYMN = 1
END_HYMN = 791

REQUEST_TIMEOUT = 20

# ---------------------------------
# MANUAL VERSE COUNT OVERRIDES
# ---------------------------------
MANUAL_VERSE_COUNT_OVERRIDES = {
    13: 3,
    73: 5,
    88: 9,
    111: 4,
    146: 8,
    167: 11,
    214: 5,
    242: 6,
    278: 5,
    285: 8,
    331: 4,
    335: 5,
    339: 2,
    370: 7,
    412: 6,
    477: 2,
    524: 6,
    582: 6,
    594: 3,
    720: 10,
    725: 5,
    731: 4,
    755: 3,
    787: 5,
    788: 6,
}


# ---------------------------------
# TEXT HELPERS
# ---------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    replacements = {
        "a. p.": "ap",
        "c. e. f.": "cef",
        "j. p. e.": "jpe",
        "h. o. c.": "hoc",
        "ö": "o",
        "ä": "a",
        "ü": "u",
        "å": "a",
        "æ": "ae",
        "ø": "o",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------
# HYMN PAGE SCRAPING
# ---------------------------------
def extract_first_verse_line(lines: list[str]) -> str:
    """
    Find the first real verse line.
    Ignore Bible references like:
    'Mos 28,10-19', 'Kor 15,12-20', 'Pet 1,3-9'
    """
    for line in lines:
        line = clean_text(line)

        match = re.match(r"^1\s+(.+)$", line)
        if not match:
            continue

        candidate = clean_text(match.group(1))

        if re.match(r"^(?:[1-4]\s*)?[A-ZÆØÅa-zæøå]{2,}\s+\d+[,:.-]\d+", candidate):
            continue

        return candidate

    return ""


def is_instruction_line(line: str) -> bool:
    line_norm = clean_text(line).lower()

    instruction_phrases = [
        "salmen kan synges som",
        "kan synges som",
        "vekselsang",
    ]

    return any(phrase in line_norm for phrase in instruction_phrases)


def looks_like_melody_line(line: str) -> bool:
    """
    Return True for actual melody lines, including:
    - composer/year lines
    - source/composer lines with '/'
    - melody-title lines like 'Et lidet barn så lysteligt'
    """

    line = clean_text(line)
    if not line:
        return False

    if is_instruction_line(line):
        return False

    # Definitely not melody lines
    if re.match(r"^\d+$", line):
        return False
    if re.match(r"^\d+\s+", line):
        return False

    # Verse / scripture / authorship references
    if any(book in line for book in ["Es ", "Åb ", "Job ", "Matt ", "Luk ", "Joh ", "Sam ", "Sl "]):
        return False

    # Long lyric lines usually end with punctuation
    if line.endswith(",") or line.endswith(";") or line.endswith(":") or line.endswith("!") or line.endswith("?"):
        return False

    has_year = bool(re.search(r"\b(1[0-9]{3}|20[0-9]{2}|[0-9]{1,2}\.\s*årh\.)\b", line))
    has_slash = "/" in line

    if has_year or has_slash:
        return True

    # Allow short melody-title lines with title-style capitalization
    words = line.split()
    if 2 <= len(words) <= 8:
        if line[0].isupper():
            return True

    return False


def merge_split_melody_lines(lines: list[str]) -> list[str]:
    """
    Merge lines like:
    'Førreformatorisk julevise /'
    + 'Joseph Klug 1543'
    """
    merged = []
    i = 0

    while i < len(lines):
        current = clean_text(lines[i])

        if not current:
            i += 1
            continue

        if current.endswith("/") and i + 1 < len(lines):
            next_line = clean_text(lines[i + 1])
            combined = clean_text(current + " " + next_line)
            merged.append(combined)
            i += 2
        else:
            merged.append(current)
            i += 1

    return merged


def extract_melodies(lines: list[str]) -> list[str]:
    melodies = []

    for i, line in enumerate(lines):
        if line.startswith("Mel.:"):
            first = clean_text(line.replace("Mel.:", ""))
            candidate_lines = []

            if first:
                candidate_lines.append(first)

            j = i + 1
            while j < len(lines):
                next_line = clean_text(lines[j])

                if re.match(r"^\d+\s+", next_line):
                    break
                if re.match(r"^\d+$", next_line):
                    break

                if next_line.startswith("Tekst:") or next_line.startswith("HØR") or next_line.startswith("Hør"):
                    break

                if is_instruction_line(next_line):
                    j += 1
                    continue

                if looks_like_melody_line(next_line):
                    candidate_lines.append(next_line)
                    j += 1
                    continue

                break

            candidate_lines = merge_split_melody_lines(candidate_lines)

            for candidate in candidate_lines:
                if candidate and looks_like_melody_line(candidate):
                    melodies.append(candidate)

    return list(dict.fromkeys(melodies))

def extract_recording_melodies(lines: list[str]) -> list[str]:
    recording_melodies = []

    for i, line in enumerate(lines):
        if line == "Vælg melodi:":
            j = i + 1

            while j < len(lines):
                next_line = clean_text(lines[j])

                if not next_line:
                    break

                if next_line.startswith(("Orgel", "Piano", "00.00", "HØR", "Hør", "Se salmens tekst")):
                    break

                recording_melodies.append(next_line)
                j += 1

    return list(dict.fromkeys(recording_melodies))


def extract_verse_count(lines: list[str]) -> int:
    verse_numbers = []
    expected = 1

    for i, line in enumerate(lines):
        line = clean_text(line)
        if not line:
            continue

        # Case 1: "1 Nu takker alle Gud"
        same_line_match = re.match(r"^(\d+)\s+(.+)$", line)

        # Case 2: "1" alone, then verse text next line
        solo_number_match = re.match(r"^(\d+)$", line)

        found_number = None

        if same_line_match:
            found_number = int(same_line_match.group(1))

        elif solo_number_match:
            found_number = int(solo_number_match.group(1))
            next_line = clean_text(lines[i + 1]) if i + 1 < len(lines) else ""

            if not next_line:
                continue
            if re.match(r"^\d+$", next_line):
                continue
            if next_line.startswith(("Mel.:", "Tekst:", "HØR", "Hør")):
                continue

        if found_number == expected:
            verse_numbers.append(found_number)
            expected += 1

    return len(verse_numbers)


def parse_hymn_page(hymn_number: int):
    url = f"https://m.dendanskesalmebogonline.dk/salme/{hymn_number}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "da,en-US;q=0.9,en;q=0.8",
        "Referer": "https://m.dendanskesalmebogonline.dk/",
        "Connection": "keep-alive",
    }

    try:
        session = requests.Session()
        session.headers.update(headers)

        session.get("https://m.dendanskesalmebogonline.dk/", timeout=REQUEST_TIMEOUT)

        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch hymn {hymn_number}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    raw_lines = soup.get_text("\n").split("\n")
    lines = [clean_text(line) for line in raw_lines]
    lines = [line for line in lines if line]

    hymn_title = ""
    first_line = ""
    melodies = []
    verse_count = 0

    # Find hymn title by hymn number line
    for i, line in enumerate(lines):
        if line == str(hymn_number):
            if i + 1 < len(lines):
                hymn_title = clean_text(lines[i + 1])
            break

    melodies = extract_melodies(lines)
    recording_melodies = extract_recording_melodies(lines)
    first_line = extract_first_verse_line(lines)
    verse_count = extract_verse_count(lines)

    if hymn_number in MANUAL_VERSE_COUNT_OVERRIDES:
        verse_count = MANUAL_VERSE_COUNT_OVERRIDES[hymn_number]

    if not first_line:
        first_line = hymn_title

    if not hymn_title and soup.title and soup.title.string:
        hymn_title = clean_text(soup.title.string)

    if not hymn_title:
        print(f"Warning: could not find title for hymn {hymn_number}")

    return {
        "hymn_number": hymn_number,
        "hymn_title": hymn_title,
        "first_line": first_line,
        "melodies": melodies,
        "recording_melodies": recording_melodies,
        "verse_count": verse_count,
        "hymn_url": url,
        "chorales": []
    }

# ---------------------------------
# BUILD DATASET
# ---------------------------------
def build_dataset() -> dict:
    dataset = {}

    for hymn_number in range(START_HYMN, END_HYMN + 1):
        print(f"Scraping hymn {hymn_number}...")
        hymn = parse_hymn_page(hymn_number)

        if hymn is None:
            time.sleep(0.2)
            continue

        dataset[str(hymn_number)] = hymn
        time.sleep(0.2)

    return dataset


# ---------------------------------
# MAIN
# ---------------------------------
def main():
    print("Building hymn dataset from website...")
    dataset = build_dataset()

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Saved dataset to {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
