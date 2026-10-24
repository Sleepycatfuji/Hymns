import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_mobile import ROOT, write_mobile


class MobileBundleTests(unittest.TestCase):
    def test_offline_bundle_is_the_validated_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'www'
            write_mobile(target, 'test-revision')
            payloads = list((target / 'data').glob('*.json'))
            self.assertEqual(len(payloads), 1)
            payload = payloads[0].read_bytes()
            self.assertEqual(payload, (ROOT / 'data/hymns_dataset_updated.json').read_bytes())
            html = (target / 'index.html').read_text()
            self.assertIn(f'./data/{payloads[0].name}', html)
            self.assertIn(hashlib.sha256(payload).hexdigest(), html)
            self.assertIn('Privatliv / Privacy', html)
            self.assertEqual(len(json.loads(payload)), 791)
            self.assertFalse((target / 'release.json').exists())
            with self.assertRaises(FileExistsError):
                write_mobile(target, 'another-revision')

    def test_local_app_origin_has_no_remote_server_override(self):
        config = json.loads((ROOT / 'capacitor.config.json').read_text())
        self.assertNotIn('server', config)
        self.assertEqual(config['webDir'], 'mobile-www')
        self.assertFalse(config['android']['allowMixedContent'])
