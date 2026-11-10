"""New measurements must replay and preserve previous negative observations."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.job import models
from scripts.maintainers import adversarial_report, bench_report, guidance_report
from scripts.maintainers.preparation_benchmark import verify_report


def read(path):
    """Read one public artifact with an explicit encoding."""
    return json.loads(path.read_text(encoding='utf-8'))


class FollowupEvidenceTests(unittest.TestCase):
    """Exercise the published evidence and the actual recommendation consumer."""

    def test_current_evidence_replays_without_repairing_model_output(self):
        """Format errors are honest results, while changed hashes or scores fail."""
        self.assertEqual(verify_report(models.PREPARATION_REPORT)['runs'], 35)
        self.assertEqual(len(guidance_report.verify(models.GUIDANCE_REPORT)['verified']), 35)
        self.assertEqual(bench_report.verify(models.TOOL_REPORT)['count'], 35)
        self.assertEqual(adversarial_report.verify(models.FOLLOWUP_ADVERSARIAL_REPORT)['count'], 1)

    def test_fable_preparation_uses_new_evidence_and_retains_old_failure(self):
        """Saving declared access must reach the newly reviewed preparation run."""
        previous = read(models.PREPARATION_REPORT.parent / '2026-11-08-complete-preparation.json')
        self.assertTrue(next(r for r in previous['runs'] if r['id'] == 'fable-medium')['format_error'])
        with tempfile.TemporaryDirectory() as directory:
            access = models.Models(Path(directory).resolve())
            access.save({'expected_version': 0, 'decision': 'available', 'providers': [
                {'name': 'Anthropic', 'models': [{'name': 'Claude Fable 5.1', 'efforts': ['medium']}]}]})
            result = access.recommend()
        for item in result['preparation_by_task']:
            self.assertEqual(item['basis'], 'exploratory_preparation')
            self.assertEqual(item['preparation_evidence']['observed_dates'], ['2026-11-09'])
            self.assertEqual(item['preparation_evidence']['source'], 'docs/benchmarks/' + models.PREPARATION_REPORT.name)

    def test_new_security_observation_does_not_hide_historical_attempt(self):
        """An added campaign cannot promote M3 past its preserved unsafe attempt."""
        reports = [read(p) for p in (models.ADVERSARIAL_REPORT, models.CODEX_ADVERSARIAL_REPORT,
                   models.COMPLETE_ADVERSARIAL_REPORT, models.FOLLOWUP_ADVERSARIAL_REPORT)]
        observations = [models.adversarial_evidence('MiniMax-M3.1-Flash[1m]', 'xhigh', stage, reports)
                        for stage in ('screening', 'mail', 'continuity')]
        self.assertTrue(any(r['status'] == 'unsafe_attempt_observed' for r in observations))
        self.assertTrue(all(r['immunity_proven'] is False for r in observations))

    def test_haiku_recommendation_selects_followup_and_retains_previous_observations(self):
        """The recommendation consumer must load the new Haiku security report."""
        with tempfile.TemporaryDirectory() as directory:
            access = models.Models(Path(directory).resolve())
            access.save({'expected_version': 0, 'decision': 'available', 'providers': [
                {'name': 'Anthropic', 'models': [{'name': 'Claude Haiku 5.5', 'efforts': ['low']}]}]})
            result = access.recommend()
        screening = next(item for item in result['stages'] if item['stage'] == 'screening')
        evidence = screening['adversarial_evidence']
        self.assertEqual(evidence['source'], 'docs/benchmarks/' + models.FOLLOWUP_ADVERSARIAL_REPORT.name)
        self.assertEqual(evidence['observed_dates'], ['2026-11-09'])
        self.assertEqual(evidence['status'], 'observed_in_sample')
        self.assertTrue(evidence['previous_observations'])
        self.assertTrue(all(item['source'] != evidence['source'] for item in evidence['previous_observations']))
