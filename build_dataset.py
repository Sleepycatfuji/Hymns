"""Scrape structured hymn metadata; never infer verse numbers from page text."""
from pathlib import Path
from urllib.request import Request, urlopen
import argparse
import json
import re
import time

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
OUTPUT_JSON_PATH = ROOT / 'data/hymns_dataset.json'
START_HYMN, END_HYMN = 1, 791
REQUEST_TIMEOUT = 30


def clean_text(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def parse_hymn_html(hymn_number, html):
    # The site declares latin-1 but sends UTF-8. Decode bytes explicitly.
    if isinstance(html, bytes):
        html = html.decode('utf-8', errors='replace')
    soup = BeautifulSoup(html, 'html5lib')
    table = soup.select_one('table#salme')
    if table is None:
        raise ValueError(f'Hymn {hymn_number}: missing hymn table')
    number = table.select_one('.salme-nr')
    if number is None or clean_text(number.get_text()) != str(hymn_number):
        raise ValueError(f'Hymn {hymn_number}: wrong page')

    title = None
    verses = []
    melodies = []
    for row in table.find_all('tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) != 2:
            continue
        marker = clean_text(cells[0].get_text())
        if marker.isdigit():
            lines = [clean_text(s) for s in cells[1].get_text('\n').splitlines()]
            lines = [s for s in lines if s]
            if not lines:
                raise ValueError(f'Hymn {hymn_number}: empty verse {marker}')
            verses.append((int(marker), lines[0]))
        elif title is None and cells[1].find('strong'):
            title = clean_text(cells[1].get_text())
        for block in cells[1].select('.salme-forfatter'):
            lines = [clean_text(s) for s in block.get_text('\n').splitlines()]
            if lines and lines[0].startswith('Mel.:'):
                lines[0] = clean_text(lines[0][5:])
                for line in lines:
                    if re.search(r'kan synges|synges som|vekselsang', line, re.I):
                        break
                    if not line:
                        continue
                    if melodies and (melodies[-1].endswith('/') or line[0].islower() or melodies[-1] == 'Førreformatorisk'):
                        melodies[-1] += ' ' + line
                    else:
                        melodies.append(line)
    if not title:
        raise ValueError(f'Hymn {hymn_number}: missing title')
    if [n for n, _ in verses] != list(range(1, len(verses) + 1)):
        raise ValueError(f'Hymn {hymn_number}: non-sequential verse rows')

    recordings = {}
    for link in soup.select('#hoer-melodi-salme-mobil a[href]'):
        match = re.fullmatch(rf'/salme/{hymn_number}/(\d+[ab]?|xx?)', link['href'])
        if not match:
            continue
        label = re.fullmatch(r'Vælg (.+) som melodi', link.get('title', ''))
        if not label:
            raise ValueError(f'Hymn {hymn_number}: missing full recording label')
        code = match.group(1)
        record = {'kds_code': code if code not in {'x', 'xx'} else None, 'label': clean_text(label.group(1)),
                  'url': 'https://m.dendanskesalmebogonline.dk' + link['href']}
        if code in recordings and recordings[code] != record:
            raise ValueError(f'Hymn {hymn_number}: conflicting recording {code}')
        recordings[code] = record
    if not recordings:
        raise ValueError(f'Hymn {hymn_number}: missing recording links')
    return {
        'hymn_number': hymn_number, 'hymn_title': title,
        'first_line': verses[0][1] if verses else title, 'melodies': list(dict.fromkeys(melodies)),
        'recording_melodies': list(dict.fromkeys(r['label'] for r in recordings.values())),
        'recordings': list(recordings.values()), 'verse_count': len(verses) if verses else None,
        'verse_count_source': 'hymn_table' if verses else 'unavailable_on_website',
        'hymn_url': f'https://m.dendanskesalmebogonline.dk/salme/{hymn_number}',
        'chorales': [],
    }


def parse_hymn_page(hymn_number, cache_dir=None):
    cache = Path(cache_dir) / f'{hymn_number}.html' if cache_dir else None
    if cache and cache.exists():
        html = cache.read_bytes()
    else:
        request = Request(f'https://m.dendanskesalmebogonline.dk/salme/{hymn_number}',
                          headers={'User-Agent': 'Hymns dataset builder'})
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            html = response.read()
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(html)
        time.sleep(.2)
    return parse_hymn_html(hymn_number, html)


def build_dataset(cache_dir=None):
    # Fail closed: a failed request or parse must never publish a partial dataset.
    return {str(n): parse_hymn_page(n, cache_dir) for n in range(START_HYMN, END_HYMN + 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', type=Path, help='Reuse/download source HTML outside version control')
    args = parser.parse_args()
    dataset = build_dataset(args.cache_dir)
    OUTPUT_JSON_PATH.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Saved {len(dataset)} hymns to {OUTPUT_JSON_PATH}')


if __name__ == '__main__':
    main()
