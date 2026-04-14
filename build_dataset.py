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
PDF_PATH = Path("data/reg_kds.pdf")
OUTPUT_JSON_PATH = Path("data/hymns_dataset.json")

# Update this if you want a smaller test range first
START_HYMN = 1
END_HYMN = 791

REQUEST_TIMEOUT = 20


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

        # Ignore Bible-reference style text
        if re.match(r"^(?:[1-4]\s*)?[A-ZÆØÅa-zæøå]{2,}\s+\d+[,:.-]\d+", candidate):
            continue

        return candidate

    return ""


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
    # Example: "Et lidet barn så lysteligt"
    words = line.split()
    if 2 <= len(words) <= 8:
        # reject obvious lyric-style lowercase continuation lines
        if line[0].isupper():
            return True

    return False

    # Real melody lines often contain:
    # composer names + year
    # or slash-separated source/composer info
    has_year = bool(re.search(r"\b(1[0-9]{3}|20[0-9]{2}|[0-9]{1,2}\.\s*årh\.)\b", line))
    has_slash = "/" in line

    # Many valid melody lines are like:
    # "Henrik Rung 1857"
    # "15. årh. / Lossius 1553"
    # "Tysk visemelodi omkring 1600 / A.P. Berggreen 1849"
    if has_year or has_slash:
        return True

    return False


def extract_melodies(lines: list[str]) -> list[str]:
    melodies = []

    for i, line in enumerate(lines):
        if line.startswith("Mel.:"):
            first = clean_text(line.replace("Mel.:", ""))
            if first and looks_like_melody_line(first):
                melodies.append(first)

            j = i + 1
            while j < len(lines):
                next_line = clean_text(lines[j])

                # Stop when verses begin
                if re.match(r"^\d+\s+", next_line):
                    break
                if re.match(r"^\d+$", next_line):
                    break

                # Stop at obvious metadata sections
                if next_line.startswith("Tekst:") or next_line.startswith("HØR") or next_line.startswith("Hør"):
                    break

                if looks_like_melody_line(next_line):
                    melodies.append(next_line)
                    j += 1
                    continue

                break

    return list(dict.fromkeys(melodies))


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

        # Open homepage first to reduce 403 risk
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

    # Find hymn title by hymn number line
    for i, line in enumerate(lines):
        if line == str(hymn_number):
            if i + 1 < len(lines):
                hymn_title = clean_text(lines[i + 1])
            break

    melodies = extract_melodies(lines)
    first_line = extract_first_verse_line(lines)

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
        "hymn_url": url,
        "chorales": []
    }


# ---------------------------------
# MATCHING
# ---------------------------------
def melody_to_keywords(melody: str) -> list[str]:
    melody_norm = normalize_text(melody)

    known_keywords = [
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
        "schumann",
        "klug",
        "schop",
        "freylinghausen",
        "konig",
        "gebauer",
        "nutzhorn",
        "barnekow",
        "gade",
        "aagaard",
        "nielsen",
        "pontoppidan",
        "tysk",
        "svensk",
        "norsk",
        "dansk",
        "faroesk",
        "faeroesk",
        "ostrigsk",
    ]

    return [kw for kw in known_keywords if kw in melody_norm]


def find_chorale_candidates(match_text: str, chorales: list[dict]) -> list[dict]:
    """
    Best rule:
    match chorale titles that START with the hymn first line or title.
    """
    match_norm = normalize_text(match_text)
    if not match_norm:
        return []

    candidates = []

    for chorale in chorales:
        chorale_norm = normalize_text(chorale["chorale_title"])
        if chorale_norm.startswith(match_norm):
            candidates.append(chorale)

    return candidates


def filter_candidates_by_melody(candidates: list[dict], melodies: list[str]) -> list[dict]:
    if not candidates:
        return []

    keywords = []
    for melody in melodies:
        keywords.extend(melody_to_keywords(melody))

    keywords = list(dict.fromkeys(keywords))

    if not keywords:
        return candidates

    filtered = []
    for candidate in candidates:
        title_norm = normalize_text(candidate["chorale_title"])
        if any(keyword in title_norm for keyword in keywords):
            filtered.append(candidate)

    # If filtering removes everything, keep all original candidates
    return filtered if filtered else candidates


def deduplicate_chorales(chorales: list[dict]) -> list[dict]:
    seen = set()
    unique = []

    for chorale in chorales:
        number = chorale["chorale_number"]
        if number not in seen:
            seen.add(number)
            unique.append(chorale)

    return unique


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

    # Make sure folder exists BEFORE writing
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Saved dataset to {OUTPUT_JSON_PATH}")

if __name__ == "__main__":
    main()
