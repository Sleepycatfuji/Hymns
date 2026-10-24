"""Package frontend and its exact dataset together; never deploy anything."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import update_chorales

ROOT = Path(__file__).resolve().parent
DATA_PATH_LINE = 'const DATA_PATH = "./data/hymns_dataset_updated.json";'
DATA_HASH_LINE = 'const DATA_SHA256 = null;'


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def release_files(revision):
    # Refuse to package stale generated data/audit.
    dataset, audit = update_chorales.generate()
    for path, expected in [(update_chorales.OUTPUT_JSON_PATH, dataset),
                           (update_chorales.AUDIT_JSON_PATH, audit)]:
        if json.loads(path.read_text(encoding='utf-8')) != expected:
            raise ValueError(f'Stale generated input: {path.name}')
    payload = update_chorales.OUTPUT_JSON_PATH.read_bytes()
    digest = sha256(payload)
    data_path = f'data/hymns.{digest}.json'
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    if html.count(DATA_PATH_LINE) != 1 or html.count(DATA_HASH_LINE) != 1:
        raise ValueError('Frontend release placeholders are missing or ambiguous')
    html = html.replace(DATA_PATH_LINE, f'const DATA_PATH = "./{data_path}";')
    html = html.replace(DATA_HASH_LINE, f'const DATA_SHA256 = "{digest}";')
    files = {'index.html': html.encode('utf-8'), data_path: payload, '.nojekyll': b''}
    manifest = {
        'schema_version': 1, 'revision': revision, 'hymn_count': len(dataset),
        'data_path': data_path,
        'files': {name: sha256(content) for name, content in files.items()},
    }
    files['release.json'] = (json.dumps(manifest, indent=2) + '\n').encode('utf-8')
    return files


def write_release(destination, revision):
    files = release_files(revision)
    # Never mix a new release with files from a previous package.
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return destination


def current_revision():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def require_clean_checkout():
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, text=True).strip():
        raise SystemExit('Commit tracked changes before building or verifying a release')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory for the complete release')
    args = parser.parse_args()
    require_clean_checkout()
    write_release(args.output, current_revision())
    print(f'Packaged frontend and dataset in {args.output}; nothing deployed.')


if __name__ == '__main__':
    main()
