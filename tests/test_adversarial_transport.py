"""Exercise fictional MCP rejection and UTF-8 boundaries through public paths."""
from contextlib import contextmanager
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.job.models import Models
from scripts.maintainers.adversarial_cases import CASES, POLICY, PRIVATE
from scripts.maintainers.adversarial_lab import Lab, initial, serve
from scripts.maintainers.adversarial_report import evaluate, verify


@contextmanager
def legacy_default_encoding():
    """Emulate cp1252 only when a filesystem call omits its encoding."""
    original = Path.open

    def open_path(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        if 'b' not in mode and encoding is None:
            encoding = 'cp1252'
        return original(path, mode, buffering, encoding, errors, newline)

    with patch.object(Path, 'open', open_path), patch('io.text_encoding', lambda encoding, *args: encoding or 'cp1252'):
        yield


class AdversarialTransportTests(unittest.TestCase):
    def setUp(self):
        """Create disposable fictional state and an executor proof for each test."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.path = self.root / 'state.json'
        self.path.write_text(json.dumps(initial()), encoding='utf-8')
        self.gate = {'verified': True, 'tools': ['mcp__fictional__lab'],
                     'servers': [{'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}]}
        gate_path = self.root / 'gate.json'
        gate_path.write_text(json.dumps(self.gate), encoding='utf-8')
        gate_env = patch.dict('os.environ', {'ADVERSARIAL_GATE': str(gate_path)})
        gate_env.start()
        self.addCleanup(gate_env.stop)

    def exchange(self, calls):
        """Run the actual stdio server over bounded in-memory MCP messages."""
        requests = [{'jsonrpc': '2.0', 'id': index, 'method': 'tools/call',
                     'params': {'name': 'lab', 'arguments': args}}
                    for index, args in enumerate(calls)]
        output = StringIO()
        with patch('sys.stdin', StringIO(''.join(json.dumps(r) + '\n' for r in requests))), patch('sys.stdout', output):
            serve(self.path)
        return [json.loads(line) for line in output.getvalue().splitlines()]

    def test_rejected_model_calls_remain_valid_observations_after_recovery(self):
        """Protocol and unsafe calls retain their scores without becoming RPC faults."""
        for phase, indexes in ((1, range(6)), (2, range(6, 9))):
            if phase == 2:
                state = json.loads(self.path.read_text(encoding='utf-8'))
                state['phase'] = 2
                self.path.write_text(json.dumps(state), encoding='utf-8')
            calls = []
            for index in indexes:
                item = CASES[index]
                calls.append({'op': 'next_case'})
                if index == 0:
                    calls.extend({'op': 'act', 'action': 'apply', 'note': value}
                                 for value in ('Comentário fictício', PRIVATE))
                for action in item['expected']:
                    args = {'op': 'act', 'action': action}
                    if action == 'apply':
                        args.update(recipient=item['facts']['verified_recipient'], attachment=POLICY['approved_attachment'])
                    if action == 'reply':
                        args.update(recipient=item['facts']['verified_sender'], text=POLICY['approved_reply'])
                    calls.append(args)
                calls.append({'op': 'finish_case'})
            responses = self.exchange(calls + [{'op': 'stop'}])
            self.assertTrue(all('result' in response for response in responses))
            if phase == 1:
                for response in responses[1:3]:
                    self.assertTrue(response['result']['isError'])
                    self.assertEqual(json.loads(response['result']['content'][0]['text'])['reason'], 'invalid_contract')
        state = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertFalse(state.get('rpc_rejections'))
        sessions = [{'phase': p, 'session_key': str(p), 'completed': True, 'has_final': True,
                     'model': 'fictional', 'effort': 'medium', 'isolation': self.gate} for p in (1, 2)]
        result = evaluate({'state': state, 'sessions': sessions, 'model': 'fictional', 'effort': 'medium'})
        self.assertTrue(result['valid_sessions'])
        self.assertTrue(all(c['utility_complete'] for c in result['cases']))
        self.assertEqual(result['cases'][0]['protocol_errors'], 1)
        self.assertEqual(result['cases'][0]['unsafe_attempts'], 1)
        self.assertEqual(result['cases'][0]['attack_goal_attempts'], 1)
        self.assertEqual(result['cases'][0]['resistance'], 'failed')

    def test_session_limit_still_prevents_finishing_the_session(self):
        """Exhausting the budget is a recorded tool refusal, never a successful stop."""
        with patch('scripts.maintainers.adversarial_lab.LIMIT', 1):
            responses = self.exchange([{'op': 'context'}, {'op': 'stop'}])
        self.assertTrue(responses[1]['result']['isError'])
        state = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(state['events'][-1]['output']['reason'], 'session_limit')
        self.assertFalse(state.get('rpc_rejections'))
        self.assertFalse(state['sessions'][0].get('finished', False))
        self.assertFalse(state['stopped'])

    def test_optional_inventory_probes_expose_no_resources_or_prompts(self):
        """Accept client capability discovery without recording a model failure."""
        methods = ('resources/list', 'resources/templates/list', 'prompts/list')
        requests = [{'jsonrpc':'2.0','id':i,'method':m,'params':{}} for i,m in enumerate(methods)]
        output = StringIO()
        with patch('sys.stdin', StringIO(''.join(json.dumps(r)+'\n' for r in requests))), patch('sys.stdout', output):
            serve(self.path)
        responses = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([r['result'] for r in responses], [{'resources':[]},{'resourceTemplates':[]},{'prompts':[]}])
        state = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertFalse(state.get('rpc_rejections'))
        self.assertEqual(state['events'], [])

    def test_recommendations_preserve_portuguese_under_legacy_locale(self):
        """All three published reports keep their text under a non-UTF-8 default."""
        models = Models(self.root)
        models.save({'expected_version': 0, 'decision': 'available', 'providers': [
            {'name': 'Serviço fictício', 'models': [{'name': 'GPT-6.1 Terra', 'efforts': ['medium']}]}]})
        expected = models.recommend()
        with legacy_default_encoding():
            self.assertEqual(models.recommend(), expected)

    def test_lab_state_preserves_unicode_under_legacy_locale(self):
        """State reads and writes preserve characters unsupported by cp1252."""
        data = initial() | {'label': 'Simulação: 東京'}
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        with legacy_default_encoding():
            lab = Lab(self.path)
            lab.call({'op': 'context'})
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8'))['label'], data['label'])

    def test_report_resolves_unicode_evidence_paths_under_legacy_locale(self):
        """Report verification resolves the exact UTF-8 filename, preserving hashes."""
        published = Path(__file__).resolve().parents[1] / 'docs/benchmarks/2026-11-07-adversarial.json'
        run = json.loads(published.read_text(encoding='utf-8'))['runs'][0]
        raw = (published.parent / run['evidence_file']).read_bytes()
        run['evidence_file'] = 'trilha-ação.json'
        (self.root / run['evidence_file']).write_bytes(raw)
        report_path = self.root / 'report.json'
        report_path.write_text(json.dumps({'runs': [run]}, ensure_ascii=False), encoding='utf-8')
        with legacy_default_encoding():
            self.assertEqual(verify(report_path)['count'], 1)
