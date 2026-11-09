import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import unittest
import tempfile

PATH = Path(__file__).resolve().parents[1] / 'scripts/maintainers/preparation_benchmark.py'
spec = importlib.util.spec_from_file_location('preparation_benchmark', PATH)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def sample():
    return {'answers': [{'id': c['id'], 'decision': copy.deepcopy(c['expected']),
                         'message': 'Vamos continuar com uma etapa de cada vez.',
                         'content': 'Conteúdo fictício para revisão humana.'}
                        for c in bench.load_cases()['cases']]}


class PreparationBenchmarkTests(unittest.TestCase):
    def test_documented_command_verifies_fresh_evidence_outside_checkout(self):
        """The documented script entry point resolves its own package imports."""
        report = PATH.parents[2] / 'docs/benchmarks/2026-11-08-complete-preparation.json'
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(PATH), 'verify', '--report', str(report)],
                cwd=directory, env={**os.environ, 'PYTHONPATH': ''},
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['runs'], 35)

    def test_valid_and_oracle_hidden(self):
        result = bench.score(sample())
        assert result['passed'] == result['total'] == 6
        assert result['critical_failures'] == 0
        assert result['qualitative']['status'] == 'not_reviewed'
        assert all('expected' not in c and 'critical' not in c for c in bench.prompt()['cases'])


    def test_unsafe_facts_and_consent(self):
        response = sample()
        response['answers'][1]['decision']['resume_campaign'] = True
        response['answers'][2]['decision']['invent_achievement'] = True
        report = bench.score(response)
        assert report['passed'] == 4
        assert report['critical_failures'] == 2


    def test_missing_extra_and_empty_content(self):
        response = sample()
        response['answers'].pop()
        response['answers'][0]['content'] = ' '
        response['answers'].append({'id': 'unknown', 'decision': {}, 'message': 'x', 'content': 'x'})
        report = bench.score(response)
        assert report['passed'] == 4
        assert report['missing_cases'] == ['career_resume']
        assert report['extra_cases'] == ['unknown']
        assert not report['complete']


    def test_strict_json_and_duplicate_case_ids(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        tmp_path = Path(directory.name)
        with self.assertRaises(ValueError):
            bench.strict_json('{"answers": [], "answers": []}')
        data = bench.load_cases()
        data['cases'][1]['id'] = data['cases'][0]['id']
        path = tmp_path / 'cases.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            bench.load_cases(path)
        response = sample()
        response['answers'][1]['id'] = response['answers'][0]['id']
        with self.assertRaises(ValueError):
            bench.score(response)


    def test_qualitative_not_inferred_from_structural_pass(self):
        result = bench.score(sample())
        assert result['passed'] == 6
        assert result['qualitative']['status'] == 'not_reviewed'
        assert result['qualitative']['evidence'] == []

    def test_published_report_replays_raw_responses_and_evidence(self):
        report = PATH.parents[2] / 'docs/benchmarks/2026-11-07-preparation.json'
        self.assertEqual(bench.verify_report(report)['runs'], 9)

    def test_fresh_client_evidence_rejects_unfinished_tools_and_changed_identity(self):
        """A successful score cannot replace the actual client completion or reply."""
        from tests.test_adversarial_codex import proof
        run = {'model':'fixture', 'effort':'medium', 'session_complete':True, 'tool_calls':0}
        evidence = {'model':'fixture', 'effort':'medium', 'session':{
            'model':'fixture', 'effort':'medium', 'completed':True, 'has_final':True,
            'isolation':{**proof(), 'model':'fixture', 'effort':'medium'},
            'final_text':'Resposta original.',
            'client_trace':{'calls':[], 'started_tools':[], 'other_tool_items':[]}}}
        bench.verify_client(evidence,run,'Resposta original.')
        for change in ('identity','unfinished_tool','gate','completion','reply'):
            altered=copy.deepcopy(evidence);session=altered['session']
            if change=='identity': session['model']='other'
            elif change=='unfinished_tool': session['client_trace']['started_tools']=[{'server':'fictional','tool':'lab'}]
            elif change=='gate': session['isolation']['verified']=False
            elif change=='completion': session['completed']=False
            else: session['final_text']='Edited'
            with self.subTest(change=change), self.assertRaises(ValueError):
                bench.verify_client(altered,run,'Resposta original.')

    def test_tampered_report_is_rejected(self):
        original = json.loads((PATH.parents[2] / 'docs/benchmarks/2026-11-07-preparation.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            for change in ('hash', 'score', 'quote', 'cross_case_quote', 'coverage', 'traversal', 'stage',
                           'note', 'tool_hash', 'tool_traversal', 'tool_count',
                           'tool_count_type', 'session_type'):
                with self.subTest(change=change):
                    report = copy.deepcopy(original)
                    run = report['runs'][0]
                    if change == 'hash': run['response_sha256'] = '0' * 64
                    if change == 'score': run['score']['passed'] = 0
                    if change == 'quote': run['text_review']['cases'][0]['evidence'] = ['trecho ausente fictício']
                    if change == 'cross_case_quote':
                        raw=(PATH.parents[2]/run['response_path']).read_text(encoding='utf-8')
                        answers=bench.strict_json(raw)['answers']
                        target=run['text_review']['cases'][0]['id']
                        current=next(a for a in answers if a['id']==target)
                        quote=next(a['message'] for a in answers if a['id']!=target)
                        self.assertNotIn(quote,current['message']+'\n'+current['content'])
                        run['text_review']['cases'][0]['evidence']=[quote]
                    if change == 'coverage': run['text_review']['cases'].pop()
                    if change == 'traversal': run['response_path'] = '../../outside.txt'
                    if change == 'stage': run['text_review']['cases'][0]['stage'] = 'cv'
                    if change == 'note':
                        case = run['text_review']['cases'][0]
                        case['verdict'] = 'needs_review'
                        case.pop('note', None)
                    if change == 'tool_hash': run['tool_observation_sha256'] = '0' * 64
                    if change == 'tool_traversal': run['tool_observation_path'] = '../../outside.txt'
                    if change == 'tool_count': run['tool_calls'] = 1
                    if change == 'tool_count_type': run['tool_calls'] = True
                    if change == 'session_type': run['session_complete'] = 'true'
                    path.write_text(json.dumps(report), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        bench.verify_report(path)
