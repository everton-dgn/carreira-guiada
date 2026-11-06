import tempfile
import unittest
from pathlib import Path

from scripts.job.due_diligence import DueDiligence


def sample(**changes):
    data = dict(kind='site', subject='Site', url='https://example.com/', checked_at='2020-01-01T00:00:00+00:00', identity='confirmed', official_origin='confirmed', data_requests='ordinary', red_flags=[], uncertainties=[], evidence=[dict(url='https://example.com/', observation='Origem observada', kind='official'), dict(url='https://independent.example/', observation='Referência observada', kind='independent')])
    data.update(changes)
    return data


class DueDiligenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.service = DueDiligence(self.root)

    def test_read_only(self):
        self.assertEqual(self.service.list(), [])
        self.assertIsNone(self.service.get('missing'))
        self.assertEqual(self.service.suggestions(), [])
        self.assertFalse((self.root / '.job').exists())

    def test_unknown_and_suspicious(self):
        self.assertEqual(self.service.save(sample(identity='unknown'))['outcome'], 'pending')
        self.assertEqual(self.service.save(sample(red_flags=['Pagamento solicitado']))['outcome'], 'avoid')
        self.assertEqual(self.service.suggestions(), [])

    def test_latest_revocation_and_distinct_vacancy(self):
        first = self.service.save(sample())
        self.assertEqual(len(self.service.suggestions()), 1)
        self.service.save(sample(kind='vacancy', red_flags=['Pagamento solicitado']))
        self.assertEqual(len(self.service.suggestions()), 1)
        self.service.save(sample(identity='contradictory'))
        self.assertEqual(self.service.suggestions(), [])
        self.assertEqual(self.service.get(first['id']), first)

    def test_old_review_import_cannot_restore_a_revoked_suggestion(self):
        self.service.save(sample(identity='contradictory', checked_at='2021-01-01T00:00:00Z'))
        self.service.save(sample(checked_at='2020-12-31T20:00:00-03:00'))
        self.assertEqual(self.service.suggestions(), [])

    def test_profile_unchanged(self):
        before = self.service.profile.get()
        self.service.save(sample())
        self.assertEqual(self.service.profile.get(), before)

    def test_invalid_and_secret(self):
        for change in ({'url': 'https://example.com/?token=abc'}, {'subject': 'senha: abc'}, {'checked_at': '2099-01-01T00:00:00Z'}, {'evidence': []}, {'uncertainties': 'unknown'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.service.save(sample(**change))
        self.assertFalse((self.root / '.job').exists())
