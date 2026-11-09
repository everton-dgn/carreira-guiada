"""A misconfigured client must never release the fictional attack corpus."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.maintainers.adversarial_codex import configuration, system_instructions
from scripts.maintainers.adversarial_isolation import valid_gate, unexpected_rpc_errors
from scripts.maintainers.benchmark_claude import arguments, attest


class BenchmarkExecutorTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {'root': '/fictional/project', 'python': '/runtime/python',
                         'state': '/fictional/state.json', 'model': 'requested-model',
                         'effort': 'max', 'client_version': 'fixture'}
        self.client = Path('/fictional/client')
        self.event = {'type': 'system', 'subtype': 'init', 'model': 'requested-model',
                      'tools': ['mcp__fictional__lab'],
                      'mcp_servers': [{'name': 'fictional', 'status': 'connected'}]}

    def test_launch_exposes_only_fixed_tools_and_replaces_settings(self):
        args = arguments(self.manifest, self.client)
        self.assertEqual(args[args.index('--tools') + 1], '')
        self.assertEqual(args[args.index('--setting-sources') + 1], '')
        self.assertIn('--strict-mcp-config', args)
        mcp = json.loads(args[args.index('--mcp-config') + 1])
        self.assertEqual(set(mcp['mcpServers']), {'fictional'})
        settings = json.loads(args[args.index('--settings') + 1])
        self.assertTrue(settings['disableAllHooks'])
        self.assertFalse(settings['autoMemoryEnabled'])
        self.assertEqual(args[args.index('--effort') + 1], 'max')

    def test_observed_catalog_and_model_are_required_before_gate(self):
        self.assertTrue(valid_gate(attest(self.event, self.manifest)))
        for field, value in [('tools', []), ('tools', ['mcp__fictional__lab', 'Bash']),
                             ('model', 'another-model'), ('plugins', ['external']),
                             ('mcp_servers', [{'name': 'email', 'status': 'connected'}])]:
            with self.subTest(field=field, value=value):
                altered = deepcopy(self.event)
                altered[field] = value
                with self.assertRaises(ValueError):
                    attest(altered, self.manifest)

    def test_missing_restrictions_in_attestation_do_not_authorize_exposure(self):
        proof = attest(self.event, self.manifest)
        for key in ('setting_sources', 'native_tools', 'strict_mcp', 'hooks_disabled',
                    'memory_disabled', 'system_prompt_replaced', 'effort', 'model'):
            with self.subTest(key=key):
                altered = deepcopy(proof)
                del altered[key]
                self.assertFalse(valid_gate(altered))

    def test_lab_selection_cannot_name_an_arbitrary_module(self):
        for kind in ('browser', 'preparation', 'guidance'):
            manifest = {**self.manifest, 'laboratory_kind': kind}
            server = configuration(manifest, self.client, ['real-mail'])['mcp_servers']
            self.assertFalse(server['real-mail']['enabled'])
            self.assertEqual(server['fictional']['enabled_tools'], ['lab'])
            self.assertIn('scripts.maintainers.benchmark_mcp', server['fictional']['args'])
        for factory in (arguments, lambda m, p: configuration(m, p, [])):
            with self.assertRaises(ValueError):
                factory({**self.manifest, 'laboratory_kind': 'os'}, self.client)

    def test_text_only_preparation_has_no_conflicting_tool_instruction(self):
        manifest = {**self.manifest, 'laboratory_kind': 'preparation'}
        instruction = system_instructions(manifest)
        self.assertIn('Não use ferramentas', instruction)
        self.assertNotIn('por context', instruction)
        args = arguments(manifest, self.client)
        self.assertEqual(args[args.index('--system-prompt') + 1], instruction)

    def test_only_observed_legacy_discovery_probe_is_exempt(self):
        discovery = {'method':'server/discover', 'error_type':'ValueError', 'sha256':'fixture'}
        self.assertEqual(unexpected_rpc_errors([discovery]), [])
        for changed in ({'method':'tools/call'}, {'method':None}, {'error_type':'TypeError'}):
            record = {**discovery, **changed}
            self.assertEqual(unexpected_rpc_errors([record]), [record])


if __name__ == '__main__':
    unittest.main()
