import copy
import json
from pathlib import Path
import unittest

from build_dataset import parse_hymn_html, build_dataset
from unittest.mock import patch
import update_chorales as mapping

ROOT = Path(__file__).resolve().parents[1]


def fixture(n):
    return (ROOT / f'tests/fixtures/hymn-{n}.html').read_bytes()


class ScraperTests(unittest.TestCase):
    def test_hymn_five_malformed_html_and_explicit_links(self):
        hymn = parse_hymn_html(5, fixture(5))
        self.assertEqual(hymn['verse_count'], 7)
        self.assertEqual([r['kds_code'] for r in hymn['recordings']], ['424', '563'])
        self.assertEqual(hymn['recording_melodies'], ['Johann Balthasar König 1738', 'Hamburg 1690'])
        self.assertEqual(hymn['first_line'], 'Fixture verse 1')

    def test_scripture_and_other_numbers_are_not_verse_markers(self):
        html = fixture(180).decode()
        hymn = parse_hymn_html(180, html)
        self.assertEqual(hymn['verse_count'], 8)
        # Navigation, scripture and author dates must not change the count.
        self.assertEqual(parse_hymn_html(180, '<p>1 Kor 15,12-20</p><p>2003</p>' + html)['verse_count'], 8)

    def test_no_manual_override_doubles_count(self):
        self.assertEqual(parse_hymn_html(285, fixture(285))['verse_count'], 4)

    def test_missing_lyrics_are_unknown_not_one_or_zero(self):
        hymn = parse_hymn_html(13, fixture(13))
        self.assertIsNone(hymn['verse_count'])
        self.assertEqual(hymn['verse_count_source'], 'unavailable_on_website')

    def test_long_secondary_melody_and_wrapped_lines(self):
        self.assertIn('Det er så yndigt at følges ad (Thomas Laub)', parse_hymn_html(131, fixture(131))['melodies'])
        self.assertEqual(parse_hymn_html(504, fixture(504))['melodies'], ['Bryd frem, mit hjertes trang at lindre'])
        self.assertEqual(parse_hymn_html(734, fixture(734))['melodies'], ['Førreformatorisk Thomissøn 1569'])

    def test_instructions_are_not_melodies(self):
        self.assertEqual(parse_hymn_html(191, fixture(191))['melodies'], ['Vor Herres Jesu mindefest'])
        self.assertEqual(len(parse_hymn_html(219, fixture(219))['melodies']), 1)

    def test_nonnumeric_liturgical_recordings(self):
        for n in [438, 440]:
            self.assertIsNone(parse_hymn_html(n, fixture(n))['recordings'][0]['kds_code'])

    def test_bad_page_and_nonsequential_verses_fail(self):
        with self.assertRaises(ValueError):
            parse_hymn_html(6, fixture(5))
        with self.assertRaises(ValueError):
            parse_hymn_html(5, fixture(5).replace(b'<strong>3</strong>', b'<strong>9</strong>'))
        with self.assertRaises(ValueError):
            parse_hymn_html(5, '<html>Temporarily unavailable</html>')

    def test_build_fails_on_fetch_failure(self):
        with patch('build_dataset.parse_hymn_page', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                build_dataset()


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = mapping.parse_chorale_register(mapping.CHORALE_REGISTER_PDF)
        cls.references = mapping.parse_melody_reference_pdf(mapping.MELODY_REFERENCE_PDF)
        cls.raw = json.loads(mapping.HYMNS_JSON_PATH.read_text())
        cls.dataset, cls.audit = mapping.update_hymn_dataset(cls.raw, cls.register, cls.references)

    def codes(self, n):
        return [o['display_kds'] for o in self.dataset[str(n)]['chorale_options']]

    def test_full_dataset_integrity(self):
        mapping.validate_dataset(self.dataset, self.register, self.references)
        self.assertEqual(len(self.audit['by_hymn']), 791)
        for key, hymn in self.dataset.items():
            with self.subTest(hymn=key):
                self.assertTrue(hymn['chorale_options'] or hymn.get('special_reference'))
                self.assertNotIn('\ufffd', json.dumps(hymn, ensure_ascii=False))
                self.assertTrue(all(r['kds_code'] is None or mapping.kds_base(r['kds_code']) in self.register for r in hymn['recordings']))
                if self.raw[key]['verse_count'] is not None:
                    self.assertEqual(hymn['verse_count'], self.raw[key]['verse_count'])
                else:
                    self.assertEqual(hymn['verse_count'], self.references[key]['verse_count'])

    def test_committed_outputs_are_reproducible(self):
        self.assertEqual(json.loads(mapping.OUTPUT_JSON_PATH.read_text()), self.dataset)
        self.assertEqual(json.loads(mapping.AUDIT_JSON_PATH.read_text()), self.audit)

    def test_required_hymn_five_regression(self):
        self.assertEqual(self.dataset['5']['verse_count'], 7)
        self.assertEqual(self.codes(5), ['424', '563'])

    def test_secondary_melody_missing_from_both_title_match_and_pdf(self):
        self.assertEqual(self.codes(735), ['396', '364', '109'])

    def test_reference_columns_continuations_and_variants(self):
        for n, codes, verses in [(1, ['178', '179'], 3), (16, ['2a', '2b'], 6),
                                  (33, ['476', '126'], 7), (60, ['294', '295'], 4),
                                  (93, ['228', '369'], 2), (380, ['439', '311'], 6)]:
            with self.subTest(hymn=n):
                self.assertEqual(self.references[str(n)]['kds_codes'], codes)
                self.assertEqual(self.references[str(n)]['verse_count'], verses)
        self.assertEqual(self.codes(16), ['2a', '2b'])
        self.assertIsNone(self.references['419']['verse_count'])
        self.assertGreater(self.dataset['419']['verse_count'], 0)

    def test_every_explicit_reference_is_preserved_except_reviewed_corrections(self):
        corrections = json.loads(mapping.CORRECTIONS_PATH.read_text())
        for key, audit in self.audit['by_hymn'].items():
            if key in corrections:
                self.assertEqual(self.codes(key), corrections[key]['kds_codes'])
                continue
            self.assertTrue(set(audit['reference_kds_codes']) <= set(self.codes(key)))
            self.assertTrue({mapping.kds_base(c) for c in audit['website_kds_codes']} <= {mapping.kds_base(c) for c in self.codes(key)})

    def test_false_title_matches_and_conflicts(self):
        for n, expected in [(239, ['531']), (380, ['439', '311']), (432, ['202']),
                            (433, ['201']), (597, ['493', '63']), (790, ['156', '158a', '158b'])]:
            self.assertEqual(self.codes(n), expected)
        self.assertEqual(self.dataset['369']['verse_count'], 6)
        self.assertEqual(self.dataset['380']['verse_count'], 6)
        self.assertEqual(self.codes(438), [])
        self.assertEqual(self.codes(440), ['416'])
        self.assertEqual(self.dataset['438']['book_page'], 568)
        self.assertEqual(self.dataset['440']['book_page'], 570)
        self.assertIsNone(self.dataset['440']['chorale_options'][0]['recording_url'])
        for n in [438, 440]:
            self.assertTrue(self.dataset[str(n)]['special_reference'])

    def test_register_headers_footers_and_page_continuation(self):
        self.assertEqual(set(self.register), set(map(str, range(1, 569))))
        self.assertEqual(self.register['568']['chorale_title'], 'Ånden opgav enkesønnen')
        self.assertEqual(self.register['294']['chorale_title'], 'Jesus, min drot (Mariavise / Prahl og Heinebuch)')
        for entry in self.register.values():
            self.assertNotIn('---', entry['chorale_title'])
            self.assertNotIn('REGISTER', entry['chorale_title'])

    def test_recordings_use_codes_not_order_or_equal_lengths(self):
        raw = copy.deepcopy(self.raw)
        raw['5']['recordings'].reverse()
        raw['5']['melodies'].reverse()
        updated, _ = mapping.update_hymn_dataset(raw, self.register, self.references)
        assigned = {o['display_kds']: o['recording_melody'] for o in updated['5']['chorale_options']}
        self.assertEqual(assigned, {'424': 'Johann Balthasar König 1738', '563': 'Hamburg 1690'})
        # PDF-only chorale 124 cannot receive Balle's /125 recording by position.
        by_code = {o['display_kds']: o for o in self.dataset['66']['chorale_options']}
        self.assertIsNone(by_code['124']['recording_melody'])
        self.assertEqual(by_code['125']['recording_melody'], 'Carl C. N. Balle 1855')

    def test_validation_rejects_partial_data_and_wrong_recordings(self):
        bad = copy.deepcopy(self.dataset)
        del bad['791']
        with self.assertRaises(ValueError):
            mapping.validate_dataset(bad, self.register, self.references)
        bad = copy.deepcopy(self.dataset)
        bad['5']['chorale_options'][0]['recording_url'] = bad['5']['recordings'][1]['url']
        with self.assertRaises(ValueError):
            mapping.validate_dataset(bad, self.register, self.references)


if __name__ == '__main__':
    unittest.main()
