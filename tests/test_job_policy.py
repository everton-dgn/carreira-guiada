import json
import unittest
from pathlib import Path
from scripts.job.policy import evaluate


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((Path(__file__).resolve().parents[1] / 'templates/profile.json').read_text())['sections']['preferences']
        self.p.update(roles=['Função sintética'], modalities=['remote'], currencies=['BRL'])
        self.p['salary']['floors'] = [{'contract': 'CLT', 'currency': 'BRL', 'period': 'month', 'amount': 1000}]
        self.v = {'role': 'Função sintética', 'modality': 'remote', 'contract': 'CLT', 'languages': [], 'salary': {'min': 1200, 'max': 1600, 'currency': 'BRL', 'period': 'month', 'estimated': False}}

    def decision(self): return evaluate(self.p, self.v)['decision']

    def test_ranges_missing_currency_and_estimate(self):
        self.assertEqual(self.decision(), 'eligible')
        self.v['salary']['min'] = 800
        self.assertEqual(self.decision(), 'blocked')
        self.p['salary']['range'] = 'minimum'
        self.assertEqual(self.decision(), 'discarded')
        self.p['salary']['range'] = 'maximum'
        self.assertEqual(self.decision(), 'blocked')
        self.v['salary']['currency'] = 'USD'
        self.assertEqual(self.decision(), 'discarded')
        self.v['salary'] = None
        self.assertEqual(self.decision(), 'blocked')

    def test_hourly_and_yearly(self):
        self.v['salary'].update(min=10, max=10, period='hour')
        self.assertEqual(self.decision(), 'blocked')
        self.v['salary']['guaranteed_hours_per_month'] = 160
        self.assertEqual(self.decision(), 'eligible')
        self.v['salary'].update(min=12000, max=12000, period='year')
        self.assertEqual(self.decision(), 'eligible')
        self.v['salary']['estimated'] = True
        self.assertEqual(self.decision(), 'blocked')

    def test_languages_required_and_optional(self):
        self.v['languages'] = [{'name': 'Idioma sintético', 'level': 3, 'required': False}]
        self.assertEqual(self.decision(), 'eligible')
        self.v['languages'][0]['required'] = True
        self.assertEqual(self.decision(), 'discarded')
        self.p['languages'] = [{'name': 'Idioma sintético', 'level': 3, 'required': False}]
        self.assertEqual(self.decision(), 'eligible')

    def test_unmentioned_languages_only_block_an_active_language_filter(self):
        self.v.pop('languages')
        for missing in ('ask', 'reject', 'accept'):
            self.p['missing'] = missing
            self.assertEqual(self.decision(), 'eligible')
        self.p['languages'] = [{'name': 'Português', 'level': 6, 'required': False}]
        self.p['missing'] = 'ask'
        self.assertEqual(self.decision(), 'eligible')
        self.p['languages'][0]['required'] = True
        self.assertEqual(self.decision(), 'blocked')

    def test_filters_and_absence(self):
        for pref, field in [('levels', 'level'), ('contracts', 'contract'), ('locations', 'location')]:
            with self.subTest(field=field):
                self.setUp()
                self.p[pref] = ['Permitido']
                self.v[field] = 'Diferente'
                self.assertEqual(self.decision(), 'discarded')
        self.setUp()
        self.p['blocked_companies'] = ['Bloqueada']
        self.assertEqual(self.decision(), 'blocked')
        self.v['company'] = 'Bloqueada'
        self.assertEqual(self.decision(), 'discarded')

    def test_strict_types(self):
        for value in [True, float('nan'), -1, '1200']:
            with self.subTest(value=value):
                self.v['salary']['min'] = value
                with self.assertRaises(ValueError): self.decision()
        self.setUp()
        self.v['languages'] = 'English'
        with self.assertRaises(ValueError): self.decision()

    def test_maximum_never_proves_minimum(self):
        self.p['salary']['range'] = 'maximum'
        for low, high in ((None, 1000), (None, 1600), (800, 1000), (800, 1600)):
            with self.subTest(low=low, high=high):
                self.v['salary'].update(min=low, max=high)
                self.assertEqual(self.decision(), 'blocked')
        self.v['salary'].update(min=1000, max=1600)
        self.assertEqual(self.decision(), 'eligible')

    def test_normalized_blocklists_are_exact(self):
        for pref, field, blocked, incoming in (
            ('blocked_companies', 'company', 'Empresa Árvore', 'EMPRESA ARVORE'),
            ('blocked_sectors', 'sector', 'Educação', 'EDUCACAO'),
            ('blocked_platforms', 'platform', 'jobs.example.invalid', 'JOBS.EXAMPLE.INVALID'),
        ):
            with self.subTest(field=field):
                self.setUp()
                self.p[pref] = [blocked]
                self.v[field] = incoming
                self.assertEqual(self.decision(), 'discarded')
                self.v[field] = 'Outra ' + incoming
                self.assertEqual(self.decision(), 'eligible')

    def test_normalized_contract_does_not_bypass_floor(self):
        self.v['contract'] = 'clt'
        self.v['salary'].update(min=800, max=900, currency='brl')
        self.assertEqual(self.decision(), 'discarded')
        self.v['salary'].update(min=1000, max=1200)
        self.v['role'] = 'FUNCAO SINTETICA'
        self.v['modality'] = 'REMOTE'
        self.assertEqual(self.decision(), 'eligible')

    def test_distinct_domain_accents_are_not_folded(self):
        self.p['blocked_platforms'] = ['cafe.example.invalid']
        self.v['platform'] = 'café.example.invalid'
        self.assertEqual(self.decision(), 'eligible')
