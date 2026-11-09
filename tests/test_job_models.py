"""Optional access choices must never change permissions or gate preparation."""
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from scripts.job.models import Models
from scripts.job.cli import dispatch, parser
from scripts.job.profile import Profile
from scripts.job.resumes import ResumeManager
from scripts.maintainers.model_benchmark import load_cases, prompt, score
from tests import test_job_workflow as workflow_tests


class ModelGuidanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.models = Models(self.root)

    def start(self):
        return dispatch(parser().parse_args(['--root', str(self.root), 'start']))

    def save(self, decision='available', providers=None, version=0):
        return self.models.save({'expected_version': version, 'decision': decision, 'providers': providers or []})

    def test_empty_start_is_read_only_and_model_choice_is_optional(self):
        start = self.start()
        self.assertEqual(start['next_step'], 'curriculum_input')
        self.assertTrue(start['model_setup']['optional'])
        self.assertIn('Quais aplicativos', start['model_setup']['question'])
        self.assertFalse((self.root/'.job').exists())

    def test_unknown_and_later_persist_across_sessions_without_reasking(self):
        for index, choice in enumerate(('unknown', 'later')):
            self.save(choice, version=index)
            self.assertEqual(Models(self.root).show()['decision'], choice)
            self.assertIsNone(self.start()['model_setup']['question'])
            self.assertEqual(self.start()['next_step'], 'curriculum_input')

    def test_arbitrary_provider_and_model_are_supported(self):
        self.save(providers=[{'name': 'Serviço da comunidade', 'models': [{'name': 'Modelo local 42'}]}])
        suggestion = self.models.recommend()['stages'][0]
        self.assertEqual(suggestion['model']['name'], 'Modelo local 42')
        self.assertEqual(suggestion['basis'], 'unmeasured')
        self.assertIsNone(suggestion['effort'])

    def test_subscription_does_not_imply_model_access(self):
        self.save(providers=[{'name': 'OpenAI', 'models': []}])
        self.assertTrue(all(s['model'] is None for s in self.models.recommend()['stages']))

    def test_stage_choice_uses_only_available_models_and_efforts(self):
        self.save(providers=[{'name': 'Meu aplicativo', 'models': [
            {'name': 'GPT-6.1 Terra', 'efforts': ['medium']},
            {'name': 'GPT-6 Astra', 'efforts': ['high']}]}])
        result = self.models.recommend()
        self.assertEqual(result['stages'][0]['model']['name'], 'GPT-6.1 Terra')
        self.assertEqual(result['stages'][0]['effort'], 'medium')
        self.assertEqual(result['stages'][0]['preparation_evidence']['task'], 'onboarding')
        self.assertEqual(result['stages'][0]['preparation_evidence']['total'], 2)
        self.assertEqual(result['stages'][2]['model']['name'], 'GPT-6.1 Terra')
        self.assertEqual(result['stages'][2]['effort'], 'medium')
        self.assertEqual(result['stages'][2]['benchmark_evidence']['passed'], 4)
        self.assertFalse(result['stages'][2]['benchmark_evidence']['browser_validated'])
        self.assertTrue(result['stages'][3]['benchmark_evidence']['text_cautions'])
        self.assertFalse(result['automatic_switch'])

    def test_observed_failures_are_disclosed_instead_of_hidden_by_suggestion(self):
        self.save(providers=[{'name': 'MiniMax', 'models': [{'name': 'MiniMax-M3.1-Flash[1m]', 'efforts': ['xhigh']}]}])
        measured = self.models.recommend()['stages'][0]['benchmark_evidence']
        self.assertEqual(measured['critical_failures'], 2)
        self.assertEqual(measured['passed'], 4)
        self.assertEqual(measured['total'], 6)

    def test_guidance_uses_the_task_evidence_instead_of_the_preparation_choice(self):
        """Interview advice must not inherit a successful curriculum suggestion."""
        self.save(providers=[{'name': 'Serviço informado', 'models': [
            {'name': 'GPT-6.1 Terra', 'efforts': ['medium']},
            {'name': 'GPT-6.1 Sol', 'efforts': ['medium']}]}])
        result = self.models.recommend()
        preparation = {r['task']: r for r in result['preparation_by_task']}
        guidance = {r['task']: r for r in result['guidance_by_task']}
        self.assertEqual(preparation['cv']['model']['name'], 'GPT-6.1 Terra')
        self.assertEqual(guidance['interview']['model']['name'], 'GPT-6.1 Sol')
        self.assertEqual(guidance['interview']['basis'], 'exploratory_guidance')
        self.assertEqual(guidance['interview']['guidance_evidence']['total'], 6)
        self.assertFalse(guidance['interview']['guidance_evidence']['real_services_validated'])
        self.assertFalse(result['automatic_switch'])

    def test_profile_approval_and_saved_resume_survive_model_change(self):
        helper = workflow_tests.WorkflowTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        helper.approve_profile()
        resume = helper.approved_resume()
        before = Profile(helper.root).get()
        Models(helper.root).save({'expected_version': 0, 'decision': 'later', 'providers': []})
        self.assertEqual(Profile(helper.root).get(), before)
        self.assertTrue(Profile(helper.root).status()['approved'])
        self.assertEqual(ResumeManager(helper.root).get(resume['id'])['status'], 'approved')

    def test_invalid_or_stale_choice_preserves_previous_value(self):
        self.save('later')
        before = self.models.show()
        with self.assertRaises(ValueError):
            self.save('unknown')
        for providers in ([{'name': 'OpenAI', 'models': [], 'api_key': 'not-a-secret'}],
                          [{'name': 'https://example.invalid', 'models': []}],
                          [{'name': 'X', 'models': [{'name': 'Y', 'efforts': ['unsupported']}]}]):
            with self.assertRaises(ValueError):
                self.save(providers=providers, version=1)
        self.assertEqual(self.models.show(), before)

    def test_bad_optional_record_does_not_block_start(self):
        self.save('later')
        with Profile(self.root)._db(True) as db:
            db.execute("UPDATE job_model_access SET value='{}'")
        self.assertEqual(self.start()['next_step'], 'curriculum_input')
        self.assertEqual(self.start()['model_setup']['decision'], 'repair_needed')


class BenchmarkContractTests(unittest.TestCase):
    def answers(self):
        return {'answers': [{'id': c['id'], 'decision': c['expected'], 'message': 'Próxima etapa fictícia.'} for c in load_cases()['cases']]}

    def test_export_omits_oracle_and_scoring_exposes_critical_failure(self):
        self.assertTrue(all('expected' not in c and 'critical' not in c for c in prompt()['cases']))
        answers = self.answers()
        self.assertEqual(score(answers)['passed'], 10)
        answers['answers'][4]['decision']['first'] = 'resubmit'
        failed = score(answers)
        self.assertEqual(failed['passed'], 9)
        self.assertEqual(failed['critical_failures'], 1)

    def test_incomplete_duplicate_and_wrong_types_cannot_pass(self):
        for mutate in (lambda a: a['answers'].pop(), lambda a: a['answers'].append(a['answers'][0])):
            a = self.answers()
            mutate(a)
            with self.assertRaises(ValueError): score(a)
        a = self.answers()
        a['answers'][4]['decision']['count_confirmed'] = False
        self.assertEqual(score(a)['passed'], 9)

    def test_published_results_match_raw_answers_and_current_cases(self):
        from scripts.job.models import REPORT
        report = json.loads(REPORT.read_text())
        self.assertEqual(len(report['runs']), 8)
        for run in report['runs']:
            with self.subTest(configuration=run['configuration']):
                self.assertEqual(score(run['response']), run['score'])

    def test_cli_rejects_contradictory_duplicate_keys_before_scoring(self):
        raw = json.dumps(self.answers()).replace('"first": "verify_destination"', '"first": "resubmit", "first": "verify_destination"')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'response.json'
            path.write_text(raw)
            result = subprocess.run([sys.executable, '-m', 'scripts.maintainers.model_benchmark', 'score', '--response', str(path)],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Chave repetida', result.stderr)
        self.assertNotIn('"passed"', result.stdout)
