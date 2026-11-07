"""Validate attestation shapes; collecting them still requires a real executor."""
from .adversarial_codex import CATALOG_RESTRICTIONS, DISABLED, ENABLED


def valid_gate(proof):
    if not isinstance(proof, dict) or proof.get('verified') is not True:
        return False
    if proof.get('tools') != ['mcp__fictional__lab']:
        return False
    if 'kind' not in proof:
        return proof.get('servers') == [
            {'name': 'fictional', 'status': 'connected', 'source': 'dynamic'}]
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
