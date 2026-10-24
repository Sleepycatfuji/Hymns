"""Sync a verified release into a portfolio checkout; never push or change other paths."""
import argparse
import json
from pathlib import Path
import shutil

from build_release import sha256


def sync_release(release, checkout):
    release, checkout = Path(release).resolve(), Path(checkout).resolve()
    manifest = json.loads((release / 'release.json').read_text(encoding='utf-8'))
    data_path = manifest['data_path']
    digest = manifest['files'].get(data_path, '')
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid dataset digest')
    if data_path != f'data/hymns.{digest}.json':
        raise ValueError('Invalid release data path')
    expected = {'index.html', data_path, '.nojekyll'}
    if set(manifest['files']) != expected:
        raise ValueError('Unexpected release files')
    for name in expected:
        path = release / name
        if path.is_symlink() or not path.is_file() or sha256(path.read_bytes()) != manifest['files'][name]:
            raise ValueError(f'Invalid release file: {name}')
    destination = checkout / 'hymns'
    # Refuse symlinks instead of following them outside the publication folder.
    if destination.is_symlink() or (destination.exists() and any(p.is_symlink() for p in destination.rglob('*'))):
        raise ValueError('Symlink in portfolio hymns directory')
    if (release / 'data').is_symlink():
        raise ValueError('Symlink in release data directory')
    for name in sorted(expected | {'release.json'}):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(release / name, target)
    # Old immutable payloads remain available to already-open older frontends.
    # Only the obsolete mutable dataset is removed; unrelated portfolio files stay.
    legacy = destination / 'data/hymns_dataset_updated.json'
    if legacy.exists():
        legacy.unlink()
    return manifest['revision']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--checkout', type=Path, required=True)
    args = parser.parse_args()
    revision = sync_release(args.release, args.checkout)
    print(f'Synced release {revision} into {args.checkout}/hymns only.')


if __name__ == '__main__':
    main()
