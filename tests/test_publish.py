import json
from pathlib import Path
import tempfile
import unittest

from build_release import sha256
from publish_release import sync_release


class PublicationTests(unittest.TestCase):
    def make_release(self, root):
        folder = root / 'release'
        (folder / 'data').mkdir(parents=True)
        data = b'{"example":1}'
        data_path = f'data/hymns.{sha256(data)}.json'
        files = {'index.html': b'new frontend', data_path: data, '.nojekyll': b''}
        for name, content in files.items():
            (folder / name).write_bytes(content)
        manifest = {'revision': 'reviewed-commit', 'data_path': data_path,
                    'files': {name: sha256(content) for name, content in files.items()}}
        (folder / 'release.json').write_text(json.dumps(manifest))
        return folder, data_path

    def test_sync_preserves_homepage_and_old_immutable_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release, data_path = self.make_release(root)
            portfolio = root / 'portfolio'
            (portfolio / 'hymns/data').mkdir(parents=True)
            (portfolio / 'index.html').write_text('portfolio homepage')
            (portfolio / 'CNAME').write_text('hellokim.me')
            (portfolio / 'hymns/data/hymns.old.json').write_text('cached payload')
            (portfolio / 'hymns/data/hymns_dataset_updated.json').write_text('obsolete')
            sync_release(release, portfolio)
            self.assertEqual((portfolio / 'index.html').read_text(), 'portfolio homepage')
            self.assertEqual((portfolio / 'CNAME').read_text(), 'hellokim.me')
            self.assertEqual((portfolio / 'hymns/index.html').read_bytes(), b'new frontend')
            self.assertTrue((portfolio / 'hymns' / data_path).exists())
            self.assertTrue((portfolio / 'hymns/data/hymns.old.json').exists())
            self.assertFalse((portfolio / 'hymns/data/hymns_dataset_updated.json').exists())
            # A repeat publication is idempotent.
            sync_release(release, portfolio)

    def test_invalid_payload_and_escape_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release, data_path = self.make_release(root)
            (release / data_path).write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                sync_release(release, root / 'portfolio')
            manifest = json.loads((release / 'release.json').read_text())
            manifest['files']['../index.html'] = sha256(b'other')
            (release / 'release.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                sync_release(release, root / 'portfolio')

    def test_destination_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release, _ = self.make_release(root)
            portfolio = root / 'portfolio'
            portfolio.mkdir()
            (portfolio / 'hymns').symlink_to(root / 'elsewhere')
            with self.assertRaises(ValueError):
                sync_release(release, portfolio)
