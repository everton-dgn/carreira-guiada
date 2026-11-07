"""Measured suggestions respect access, effort, stage and negative evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.job.models import Models


class ToolRecommendationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.report = self.root / 'report.json'
        self.models = Models(self.root)
        self.models.save({'expected_version': 0, 'decision': 'available', 'providers': [
            {'name': 'Meu serviço', 'models': [
                {'name': 'GPT-6.1 Terra', 'efforts': ['high', 'medium']},
                {'name': 'Modelo da comunidade', 'efforts': ['low']}]}]})
        self.patch = patch('scripts.job.models.TOOL_REPORT', self.report)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def run_data(self, model='Modelo da comunidade', effort='low', complete=True, guards=0, critical=None, sessions=2, valid=True, network=True):
        return {'model': model, 'effort': effort, 'valid_for_comparison': valid,
                'completed_sessions': sessions, 'score': {
                    'network_evidence_complete': network,
                    'stages': {'application': {'complete': complete, 'passed': 4 if complete else 3, 'total': 4}},
                    'critical_failures': critical or [], 'failed_write_attempts': guards}}

    def suggest(self, runs):
        self.report.write_text(json.dumps({'date': '2026-11-07', 'runs': runs}))
        return self.models.recommend()['stages']

    def test_community_evidence_can_override_initial_preference_only_for_measured_stage(self):
        stages = self.suggest([self.run_data()])
        self.assertEqual(stages[2]['model']['name'], 'Modelo da comunidade')
        self.assertEqual(stages[2]['basis'], 'exploratory_tools')
        self.assertFalse(stages[2]['tool_evidence']['real_services_validated'])
        self.assertEqual(stages[0]['model']['name'], 'GPT-6.1 Terra')
        self.assertIsNone(stages[0]['tool_evidence'])

    def test_failure_guard_or_incomplete_sessions_cannot_promote_model(self):
        for kwargs in ({'complete': False}, {'guards': 1}, {'critical': ['duplicate']}, {'sessions': 1}, {'valid': False}, {'network': False}):
            with self.subTest(kwargs=kwargs):
                stage = self.suggest([self.run_data(**kwargs)])[2]
                self.assertEqual(stage['model']['name'], 'GPT-6.1 Terra')
                self.assertNotEqual(stage['basis'], 'exploratory_tools')

    def test_ties_show_alternatives_and_prefer_lower_tested_effort(self):
        stage = self.suggest([self.run_data('gpt-6.1-terra', 'high'), self.run_data('gpt-6.1-terra', 'medium'), self.run_data()])[2]
        self.assertEqual(stage['effort'], 'medium')
        self.assertEqual(len(stage['tool_alternatives']), 3)

    def test_unknown_effort_and_undeclared_model_are_not_recommended(self):
        stage = self.suggest([self.run_data('gpt-6.1-terra', 'ultra'), self.run_data('gpt-6-astra', 'high')])[2]
        self.assertNotEqual(stage['basis'], 'exploratory_tools')
        self.assertEqual(stage['tool_alternatives'], [])
