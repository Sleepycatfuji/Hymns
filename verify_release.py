"""Read-only comparison of a local or live release with the checked-out commit."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

from build_release import current_revision, release_files, require_clean_checkout


def verify_files(read, revision, check_host_markers=True):
    expected = release_files(revision)
    # Compare every byte, including the revision and manifest, against this checkout.
    for name, content in expected.items():
        # Jekyll hosts need not serve deployment control dotfiles.
        if name == '.nojekyll' and not check_host_markers:
            continue
        if read(name) != content:
            raise ValueError(f'Release mismatch: {name}')
    return json.loads(expected['release.json'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--directory', type=Path)
    target.add_argument('--url', help='Deployed application directory, e.g. https://hellokim.me/hymns/')
    args = parser.parse_args()
    require_clean_checkout()
    revision = current_revision()
    if args.directory:
        read = lambda name: (args.directory / name).read_bytes()
    else:
        if not args.url.startswith(('https://', 'http://127.0.0.1:', 'http://localhost:')):
            raise SystemExit('Use HTTPS for production, or HTTP on localhost for a preview')
        def read(name):
            request = Request(args.url.rstrip('/') + '/' + name + '?verify=' + revision,
                              headers={'Cache-Control': 'no-cache'})
            with urlopen(request, timeout=30) as response:
                return response.read()
    manifest = verify_files(read, revision, check_host_markers=bool(args.directory))
    print(f"Verified frontend and all {manifest['hymn_count']} hymns against commit {revision}.")


if __name__ == '__main__':
    main()
