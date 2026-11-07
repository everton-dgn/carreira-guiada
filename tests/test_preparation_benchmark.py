import copy
import importlib.util
import json
from pathlib import Path

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

    def test_tampered_report_is_rejected(self):
        original = json.loads((PATH.parents[2] / 'docs/benchmarks/2026-11-07-preparation.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            for change in ('hash', 'score', 'quote', 'coverage', 'traversal'):
                with self.subTest(change=change):
                    report = copy.deepcopy(original)
                    run = report['runs'][0]
                    if change == 'hash': run['response_sha256'] = '0' * 64
                    if change == 'score': run['score']['passed'] = 0
                    if change == 'quote': run['text_review']['cases'][0]['evidence'] = ['trecho ausente fictício']
                    if change == 'coverage': run['text_review']['cases'].pop()
                    if change == 'traversal': run['response_path'] = '../../outside.txt'
                    path.write_text(json.dumps(report), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        bench.verify_report(path)
