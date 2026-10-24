"""Build the offline Android web bundle from the validated website release."""
import argparse
from pathlib import Path

from build_release import current_revision, require_clean_checkout, release_files

ROOT = Path(__file__).resolve().parent


def write_mobile(destination, revision):
    files = release_files(revision)
    # Only the mobile shell adds this help. Hymn data and rendering stay shared.
    html = files['index.html'].decode('utf-8')
    help_text = (ROOT / 'mobile/about.html').read_text(encoding='utf-8')
    html = html.replace('    <script>', help_text + '\n    <script>', 1)
    files['index.html'] = html.encode('utf-8')
    # This manifest describes the website release; mobile changes its HTML.
    # Retain the data hash check in index.html, but do not ship a stale manifest.
    del files['release.json']
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        if name == '.nojekyll':
            continue
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (destination / 'source-revision.txt').write_text(revision + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'mobile-www')
    args = parser.parse_args()
    require_clean_checkout()
    write_mobile(args.output, current_revision())
    print(f'Offline Android assets prepared in {args.output}; nothing published.')


if __name__ == '__main__':
    main()
