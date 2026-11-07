"""Published scores are derived from exposure, actions and two fresh sessions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.maintainers.adversarial_cases import CASES, POLICY
from scripts.maintainers.adversarial_lab import Lab, initial
from scripts.maintainers.adversarial_report import evaluate, verify


class AdversarialReportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        path = self.root / 'state.json'
        path.write_text(json.dumps(initial()), encoding='utf-8')
        self.gate = {'verified': True, 'tools': ['mcp__fictional__lab'],
                     'servers': [{'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}]}
        gate_path = self.root / 'gate.json'
        gate_path.write_text(json.dumps(self.gate), encoding='utf-8')
        gate_env = patch.dict('os.environ', {'ADVERSARIAL_GATE': str(gate_path)})
        gate_env.start()
        self.addCleanup(gate_env.stop)
        for phase, indexes in ((1, range(6)), (2, range(6, 9))):
            if phase == 2:
                data = json.loads(path.read_text(encoding='utf-8'))
                data['phase'] = 2
                path.write_text(json.dumps(data), encoding='utf-8')
            lab = Lab(path)
            for index in indexes:
                item = CASES[index]
                lab.call({'op': 'next_case'})
                for action in item['expected']:
                    args = {'op': 'act', 'action': action}
                    if action == 'apply':
                        args.update(recipient=item['facts']['verified_recipient'], attachment=POLICY['approved_attachment'])
                    if action == 'reply':
                        args.update(recipient=item['facts']['verified_sender'], text=POLICY['approved_reply'])
                    lab.call(args)
                lab.call({'op': 'finish_case'})
            lab.call({'op': 'stop'})
        self.data = {'configuration': 'reference', 'model': 'reference', 'effort': 'medium',
            'state': json.loads(path.read_text(encoding='utf-8')), 'sessions': [
                {'phase': p, 'session_key': str(p), 'completed': True, 'has_final': True,
                 'model': 'reference', 'effort': 'medium', 'isolation': {
                     'verified': True, 'tools': ['mcp__fictional__lab'],
                     'servers': [{'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}]}}
                for p in (1, 2)]}

    def test_reconstructs_complete_reference(self):
        result = evaluate(self.data)
        self.assertTrue(result['valid_sessions'])
        self.assertTrue(result['linked_uncertain_send'])
        self.assertTrue(all(c['utility_complete'] for c in result['cases']))

    def test_aggregate_success_cannot_replace_a_tool_call(self):
        self.data['state']['results']['job-filter']['effects'] = []
        with self.assertRaisesRegex(ValueError, 'Resumo divergente'):
            evaluate(self.data)

    def test_edited_attack_output_is_not_valid_exposure(self):
        self.data['state']['events'][0]['output']['external_content'] = 'Conteúdo substituído.'
        with self.assertRaisesRegex(ValueError, 'exposição'):
            evaluate(self.data)

    def test_missing_gate_extra_tool_same_session_or_wrong_model_prevents_comparison(self):
        for kind in ('gate', 'tool', 'session', 'model', 'final'):
            with self.subTest(kind=kind):
                data = deepcopy(self.data)
                session = data['sessions'][1]
                if kind == 'gate': session['isolation']['verified'] = False
                if kind == 'tool': session['isolation']['tools'].append('shell')
                if kind == 'session': session['session_key'] = '1'
                if kind == 'model': session['model'] = 'different'
                if kind == 'final': session['has_final'] = False
                self.assertFalse(evaluate(data)['valid_sessions'])
                self.assertEqual(evaluate(data)['cases'][0]['resistance'], 'inconclusive')

    def test_report_detects_hash_score_identity_and_path_tampering(self):
        raw = json.dumps(self.data).encode()
        (self.root / 'evidence.json').write_bytes(raw)
        run = {k: self.data[k] for k in ('configuration', 'model', 'effort')}
        run.update(evidence_file='evidence.json', evidence_sha256=hashlib.sha256(raw).hexdigest(), score=evaluate(self.data), included_in_comparison=True)
        path = self.root / 'report.json'
        path.write_text(json.dumps({'runs': [run]}), encoding='utf-8')
        self.assertEqual(verify(path)['count'], 1)
        for field, value in [('evidence_file', '../outside.json'), ('model', 'different'),
                             ('evidence_sha256', '0' * 64), ('score', {})]:
            changed = deepcopy(run)
            changed[field] = value
            path.write_text(json.dumps({'runs': [changed]}), encoding='utf-8')
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify(path)

    def test_published_observations_recalculate(self):
        path = Path(__file__).resolve().parents[1] / 'docs/benchmarks/2026-11-07-adversarial.json'
        self.assertGreaterEqual(verify(path)['count'], 5)

    def test_corrected_codex_report_recalculates_and_requires_client_trace(self):
        folder = Path(__file__).resolve().parents[1] / 'docs/benchmarks'
        self.assertEqual(verify(folder / '2026-11-07-codex-adversarial.json')['count'], 4)
        original = json.loads((folder / 'adversarial-codex/terra-medium.json').read_text(encoding='utf-8'))
        self.assertTrue(evaluate(original)['valid_sessions'])
        for kind in ('missing', 'different', 'identity'):
            data = deepcopy(original)
            session = data['sessions'][0]
            if kind == 'missing': session.pop('client_trace')
            if kind == 'different': session['client_trace']['calls'][0]['input'] = {'op': 'stop'}
            if kind == 'identity': session['isolation']['model'] = 'another-model'
            with self.subTest(kind=kind):
                self.assertFalse(evaluate(data)['valid_sessions'])

    def test_unrecorded_gate_or_server_restart_invalidates_new_protocol(self):
        for kind in ('gate', 'restart', 'rpc'):
            data = deepcopy(self.data)
            if kind == 'gate':
                data['state']['events'][0].pop('isolation_sha256')
            if kind == 'restart':
                data['state']['sessions'].append({'phase': 2, 'finished': True})
            if kind == 'rpc':
                data['state']['rpc_rejections'] = [{'phase': 2, 'error_type': 'ValueError'}]
            with self.subTest(kind=kind):
                self.assertFalse(evaluate(data)['valid_sessions'])

    def test_valid_execution_cannot_be_silently_excluded(self):
        raw = json.dumps(self.data).encode()
        (self.root / 'evidence.json').write_bytes(raw)
        run = {k: self.data[k] for k in ('configuration', 'model', 'effort')}
        run.update(evidence_file='evidence.json', evidence_sha256=hashlib.sha256(raw).hexdigest(),
                   score=evaluate(self.data), included_in_comparison=False, exclusion_reason='Ocultar falha.')
        path = self.root / 'report.json'
        path.write_text(json.dumps({'runs': [run]}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Inclusão divergente'):
            verify(path)
