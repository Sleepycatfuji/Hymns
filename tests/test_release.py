import json
from pathlib import Path
import tempfile
import unittest

from build_release import release_files, sha256, write_release
from verify_release import verify_files


class ReleaseTests(unittest.TestCase):
    def test_bundle_pairs_frontend_with_exact_dataset(self):
        files = release_files('test-revision')
        manifest = json.loads(files['release.json'])
        data = files[manifest['data_path']]
        html = files['index.html'].decode()
        self.assertIn(f'const DATA_PATH = "./{manifest["data_path"]}";', html)
        self.assertIn(f'const DATA_SHA256 = "{sha256(data)}";', html)
        self.assertEqual(len(json.loads(data)), 791)
        for name, expected_hash in manifest['files'].items():
            self.assertEqual(sha256(files[name]), expected_hash)
        verify_files(files.__getitem__, 'test-revision')

    def test_verifier_rejects_stale_frontend_dataset_and_revision(self):
        files = release_files('test-revision')
        data_path = json.loads(files['release.json'])['data_path']
        for name in ['index.html', data_path, 'release.json']:
            bad = {**files, name: b'stale release'}
            with self.subTest(file=name), self.assertRaisesRegex(ValueError, 'Release mismatch'):
                verify_files(bad.__getitem__, 'test-revision')
        with self.assertRaises(ValueError):
            verify_files(files.__getitem__, 'another-commit')

    def test_live_verification_does_not_require_host_control_dotfile(self):
        files = release_files('test-revision')
        del files['.nojekyll']
        verify_files(files.__getitem__, 'test-revision', check_host_markers=False)
        with self.assertRaises(KeyError):
            verify_files(files.__getitem__, 'test-revision')

    def test_release_directory_must_be_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'release'
            write_release(folder, 'test-revision')
            self.assertTrue((folder / 'release.json').exists())
            with self.assertRaises(FileExistsError):
                write_release(folder, 'test-revision')
