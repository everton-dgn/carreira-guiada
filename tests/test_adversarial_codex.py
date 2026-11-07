"""Executor failures must not release the fictional attack corpus."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.maintainers.adversarial_codex import (
    CATALOG_RESTRICTIONS, DISABLED, ENABLED, SYSTEM,
    configuration, restricted_catalog, thread_params, validate_thread,
)
from scripts.maintainers.adversarial_isolation import valid_gate
from scripts.maintainers.adversarial_lab import Lab, initial
from scripts.maintainers.adversarial_report import valid_client_trace
from scripts.maintainers.adversarial_codex_probe import check_results


def proof():
    return {'kind': 'codex-restricted-v1', 'verified': True,
            'tools': ['mcp__fictional__lab'],
            'servers': [{'name': 'fictional', 'status': 'connected', 'source': 'thread_mcp_inventory'}],
            'profile': 'adversarial', 'instruction_sources': [], 'approval_policy': 'never',
            'web_search': 'disabled', 'disabled_features': {k: False for k in DISABLED},
            'enabled_features': {k: True for k in ENABLED},
            'catalog_restrictions': deepcopy(CATALOG_RESTRICTIONS),
            'catalog_confirmed': True, 'filesystem_boundary_verified': True,
            'excluded_namespaces': ['functions', 'clock', 'collaboration']}


class CodexIsolationTests(unittest.TestCase):
    def test_boundary_needs_positive_control_and_actual_permission_denials(self):
        results = [{'case': 'read_inside', 'exit': 0, 'stdout': 'FICTIONAL-INSIDE', 'stderr': ''}]
        results += [{'case': name, 'exit': 1, 'stdout': '', 'stderr': 'Operation not permitted'}
                    for name in ('read_outside', 'write_inside', 'loopback_network')]
        self.assertTrue(check_results(results, 0, False))
        self.assertFalse(check_results(results, 1, False))
        self.assertFalse(check_results(results, 0, True))
        for change in ({'exit': 0}, {'stderr': 'No such file'}, {'stdout': 'FICTIONAL-OUTSIDE'}):
            altered = deepcopy(results)
            altered[1].update(change)
            self.assertFalse(check_results(altered, 0, False))

    def test_client_trace_must_match_server_and_contain_no_other_tools(self):
        event = {'phase': 1, 'input': {'op': 'context'}, 'output': {'ok': True}}
        trace = {'other_tool_items': [], 'started_tools': [{'server': 'fictional', 'tool': 'lab'}],
                 'calls': [{'server': 'fictional', 'tool': 'lab', 'status': 'completed', 'error': None,
                            'input': event['input'], 'output': event['output']}]}
        session = {'phase': 1, 'client_trace': trace}
        self.assertTrue(valid_client_trace(session, [event]))
        for change in ({'other_tool_items': ['commandExecution']}, {'started_tools': []},
                       {'started_tools': [{'server': 'mail', 'tool': 'send'}]}, {'calls': []},
                       {'calls': [trace['calls'][0] | {'input': {'op': 'stop'}}]},
                       {'calls': [trace['calls'][0] | {'error': {'message': 'failed'}}]}):
            with self.subTest(change=change):
                self.assertFalse(valid_client_trace(session | {'client_trace': trace | change}, [event]))

    def test_catalog_disables_model_driven_capabilities_without_switching_model(self):
        original = {'models': [{'slug': 'requested', 'multi_agent_version': 'v2',
                    'apply_patch_tool_type': 'freeform', 'context_window': 100,
                    'experimental_supported_tools': ['clock'], 'tool_mode': 'code_mode_only'}]}
        result = restricted_catalog(original, 'requested')['models'][0]
        self.assertEqual(result['slug'], 'requested')
        self.assertEqual(result['context_window'], 100)
        self.assertEqual(result['tool_mode'], 'code_mode_only')
        self.assertEqual(result['multi_agent_version'], 'disabled')
        self.assertIsNone(result['apply_patch_tool_type'])
        self.assertEqual(original['models'][0]['multi_agent_version'], 'v2')
        with self.assertRaises(ValueError):
            restricted_catalog(original, 'missing')

    def test_thread_cannot_inherit_unrestricted_orchestrator_configuration(self):
        client = Path('/fictional/client')
        manifest = {'root': '/fictional/project', 'python': '/runtime/python',
                    'state': '/fictional/state.json', 'model': 'requested', 'effort': 'medium'}
        config = configuration(manifest, client, ['mail'])
        params = thread_params({'sandbox': 'danger-full-access', 'model': 'other',
                 'developerInstructions': 'unsafe', 'dynamicTools': [{'name': 'real_mail'}]},
                 manifest, client, config)
        self.assertNotIn('sandbox', params)
        self.assertNotIn('dynamicTools', params)
        self.assertEqual(params['model'], 'requested')
        self.assertEqual(params['developerInstructions'], SYSTEM)
        self.assertEqual(config['mcp_servers']['mail'], {'enabled': False})
        self.assertFalse(config['permissions']['adversarial']['network']['enabled'])
        self.assertEqual(config['permissions']['adversarial']['filesystem'][':root'], 'deny')

    def test_thread_requires_absent_personal_instructions_and_exact_identity(self):
        client = Path('/fictional/client')
        manifest = {'model': 'requested', 'effort': 'medium'}
        result = {'cwd': str(client), 'activePermissionProfile': {'id': 'adversarial'},
                  'instructionSources': [], 'approvalPolicy': 'never',
                  'model': 'requested', 'reasoningEffort': 'medium'}
        validate_thread(result, manifest, client)
        for change in ({'instructionSources': ['/personal/AGENTS.md']},
                       {'activePermissionProfile': {'id': ':danger-full-access'}},
                       {'reasoningEffort': 'high'}, {'model': 'other'}, {'approvalPolicy': 'on-request'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_thread(result | change, manifest, client)

    def test_new_gate_rejects_missing_or_unsafe_capabilities(self):
        self.assertTrue(valid_gate(proof()))
        for key, value in (
            ('instruction_sources', ['/personal/AGENTS.md']), ('catalog_confirmed', False),
            ('filesystem_boundary_verified', False), ('excluded_namespaces', []),
            ('tools', ['mcp__fictional__lab', 'exec_command']),
            ('disabled_features', {**proof()['disabled_features'], 'shell_tool': True}),
            ('catalog_restrictions', {**CATALOG_RESTRICTIONS, 'apply_patch_tool_type': 'freeform'}),
        ):
            with self.subTest(key=key):
                self.assertFalse(valid_gate(proof() | {key: value}))
        for key in proof():
            altered = proof()
            del altered[key]
            self.assertFalse(valid_gate(altered), key)

    def test_legacy_attestation_remains_replayable(self):
        self.assertTrue(valid_gate({'verified': True, 'tools': ['mcp__fictional__lab'],
            'servers': [{'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}]}))

    def test_lab_releases_revision_two_only_after_valid_codex_attestation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state, gate = root / 'state.json', root / 'gate.json'
            state.write_text(json.dumps(initial()), encoding='utf-8')
            with patch.dict('os.environ', {'ADVERSARIAL_GATE': str(gate)}):
                lab = Lab(state, require_gate=True)
                self.assertFalse(lab.call({'op': 'next_case'})['ok'])
                self.assertFalse(any(c['exposed'] for c in lab.data['results'].values()))
                gate.write_text(json.dumps(proof()), encoding='utf-8')
                response = lab.call({'op': 'next_case'})
                self.assertTrue(response['ok'])
                self.assertEqual(response['case_id'], 'case-1')
                self.assertIn('isolation_sha256', lab.data['events'][-1])


if __name__ == '__main__':
    unittest.main()
