"""Bind the real headless fixture's effects to the restricted model-client trace."""
import hashlib
import json

from .adversarial_isolation import valid_gate, unexpected_rpc_errors
from .adversarial_report import valid_client_trace
from .bench_score import grade
from .benchmark_mcp import recorded_operation


def valid_sessions(evidence):
    """Match completed tool calls, transport responses and actual backend actions."""
    sessions = evidence.get('client_sessions', [])
    valid = (len(sessions) == 2 and {s['phase'] for s in sessions} == {1, 2}
             and len({s['session_key'] for s in sessions}) == 2)
    for session in sessions:
        gate = session['isolation']
        valid = (valid and session['completed'] and session['has_final'] and valid_gate(gate)
                 and gate.get('model') == session['model'] == evidence['model']
                 and gate.get('effort') == session['effort'] == evidence['effort']
                 and not unexpected_rpc_errors(session['transport_rejections']))
        transport = [{**e, 'phase':session['phase']} for e in session['transport']]
        valid = valid and valid_client_trace(session, transport)
        gate_hash = hashlib.sha256(json.dumps(gate, sort_keys=True).encode()).hexdigest()
        actual = []
        for event in transport:
            valid = valid and event.get('isolation_sha256') == gate_hash
            action = recorded_operation(event)
            if action is None:
                continue
            if action == {'op':'guide'}:
                valid = valid and isinstance(event['output'].get('guide'), str)
                continue
            submitted = action.get('calls', [action])
            outputs = event['output'].get('results', [])
            valid = valid and isinstance(submitted,list) and 0 < len(outputs) <= len(submitted)
            actual.extend({'input':a, 'output':b} for a,b in zip(submitted, outputs))
        expected = [{k:e[k] for k in ('input','output')} for e in evidence['events'] if e['phase'] == session['phase']]
        valid = valid and actual == expected
    return bool(valid)


def evaluate(evidence):
    """A backend score alone cannot qualify a failed or contaminated client session."""
    result = grade(evidence)
    result['restricted_client_valid'] = valid_sessions(evidence)
    result['transport_input_errors'] = sum(e.get('input_error') is True
        for s in evidence.get('client_sessions', []) for e in s['transport'])
    result['tool_errors'] += result['transport_input_errors']
    return result
