"""Client, MCP and backend records must agree before an operational suggestion."""
from copy import deepcopy
import hashlib
import json
import unittest

from scripts.maintainers.benchmark_browser_report import valid_sessions
from tests.test_adversarial_codex import proof


class BrowserClientEvidenceTests(unittest.TestCase):
    def setUp(self):
        """Describe two completed isolated sessions and their actual backend effects."""
        gate = {**proof(), 'model': 'fixture', 'effort': 'medium'}
        digest = hashlib.sha256(json.dumps(gate, sort_keys=True).encode()).hexdigest()
        self.evidence = {'model': 'fixture', 'effort': 'medium', 'events': [], 'client_sessions': []}
        for phase in (1, 2):
            action = {'op': 'context'}
            result = {'ok': True, 'phase': phase}
            wire = {'request_json': json.dumps(action)}
            output = {'results': [result]}
            self.evidence['events'].append({'phase': phase, 'input': action, 'output': result})
            self.evidence['client_sessions'].append({
                'phase': phase, 'session_key': str(phase), 'completed': True, 'has_final': True,
                'model': 'fixture', 'effort': 'medium', 'isolation': deepcopy(gate),
                'transport_rejections': [],
                'transport': [{'input': wire, 'operation': action, 'output': output,
                               'isolation_sha256': digest}],
                'client_trace': {
                    'calls': [{'server': 'fictional', 'tool': 'lab', 'status': 'completed',
                               'error': None, 'input': wire, 'output': output}],
                    'started_tools': [{'server': 'fictional', 'tool': 'lab'}],
                    'other_tool_items': [],
                },
            })

    def test_matching_records_qualify(self):
        """Recorded initialization and completed calls are all required."""
        self.assertTrue(valid_sessions(self.evidence))

    def test_backend_success_does_not_erase_missing_or_extra_client_actions(self):
        """Do not recommend a failed, contaminated or untraceable model session."""
        for mutation in ('unfinished', 'identity', 'extra_tool', 'backend', 'client', 'gate'):
            evidence = deepcopy(self.evidence)
            session = evidence['client_sessions'][0]
            if mutation == 'unfinished': session['completed'] = False
            elif mutation == 'identity': session['isolation']['model'] = 'other'
            elif mutation == 'extra_tool': session['client_trace']['other_tool_items'] = ['shell']
            elif mutation == 'backend': evidence['events'].append({'phase': 1, 'input': {'op': 'send'}, 'output': {}})
            elif mutation == 'client': session['client_trace']['calls'] = []
            else: session['transport'][0]['isolation_sha256'] = 'changed'
            with self.subTest(mutation=mutation):
                self.assertFalse(valid_sessions(evidence))

    def test_forged_decoding_and_missing_wire_operation_are_rejected(self):
        """Matching client and transport text cannot launder another backend action."""
        for mutation in ('different', 'missing'):
            evidence = deepcopy(self.evidence)
            session = evidence['client_sessions'][0]
            if mutation == 'different':
                wire = {'request_json': '{"op":"send"}'}
                session['transport'][0]['input'] = wire
                session['client_trace']['calls'][0]['input'] = wire
            else:
                session['transport'][0].pop('operation')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                valid_sessions(evidence)

    def test_only_observed_discovery_negotiation_is_exempt(self):
        """An unclassified RPC rejection still invalidates comparison."""
        self.evidence['client_sessions'][0]['transport_rejections'] = [
            {'method': 'server/discover', 'error_type': 'ValueError'}]
        self.assertTrue(valid_sessions(self.evidence))
        self.evidence['client_sessions'][0]['transport_rejections'][0].pop('method')
        self.assertFalse(valid_sessions(self.evidence))


if __name__ == '__main__':
    unittest.main()
