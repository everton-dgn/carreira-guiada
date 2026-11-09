"""Validate attestation shapes; collecting them still requires a real executor."""
from .adversarial_codex import CATALOG_RESTRICTIONS, DISABLED, ENABLED


def unexpected_rpc_errors(records):
    """Legacy MCP may refuse discovery before the client falls back to initialize.

    Only an explicitly observed server/discover probe is exempt. An old record
    without method evidence remains inconclusive, even if its hash looks alike.
    """
    return [r for r in records if r.get('method') != 'server/discover'
            or r.get('error_type') != 'ValueError']


def valid_gate(proof):
    """Check legacy or restricted Codex attestations without inferring missing proof."""
    if not isinstance(proof, dict) or proof.get('verified') is not True:
        return False
    if proof.get('tools') != ['mcp__fictional__lab']:
        return False
    if 'kind' not in proof:
        return proof.get('servers') == [
            {'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}]
    if proof.get('kind') == 'claude-restricted-v2':
        return (proof.get('servers') == [
                    {'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}]
                and proof.get('setting_sources') == [] and proof.get('native_tools') == []
                and all(proof.get(k) is True for k in
                        ('strict_mcp', 'hooks_disabled', 'memory_disabled', 'system_prompt_replaced',
                         'builtin_definitions_not_callable', 'instruction_directories_denied'))
                and proof.get('effort_observation') == 'explicit_cli_argument'
                and proof.get('effort') in ('low', 'medium', 'high', 'xhigh', 'max')
                and isinstance(proof.get('model'), str) and bool(proof['model']))
    if proof.get('kind') != 'codex-restricted-v1':
        return False
    return (proof.get('servers') == [
                {'name': 'fictional', 'status': 'connected', 'source': 'thread_mcp_inventory'}]
            and proof.get('profile') == 'adversarial'
            and proof.get('instruction_sources') == []
            and proof.get('approval_policy') == 'never'
            and proof.get('web_search') == 'disabled'
            and proof.get('disabled_features') == {name: False for name in DISABLED}
            and proof.get('enabled_features') == {name: True for name in ENABLED}
            and proof.get('catalog_restrictions') == CATALOG_RESTRICTIONS
            and proof.get('catalog_confirmed') is True
            and proof.get('filesystem_boundary_verified') is True
            and proof.get('excluded_namespaces') == ['functions', 'clock', 'collaboration'])
