"""Recalculate the fictional guidance journey from client and server evidence."""
import hashlib
import argparse
import json
from pathlib import Path
import tempfile

from .adversarial_isolation import valid_gate, unexpected_rpc_errors
from .adversarial_report import valid_client_trace
from .guidance_benchmark import Guidance, advance, initial, score
from .guidance_cases import CASES
from .benchmark_mcp import recorded_operation


def reconstruct(data):
    """Reject edited replies, exposure, sources or state inconsistent with calls."""
    with tempfile.TemporaryDirectory(prefix='guidance-replay-') as temp:
        path = Path(temp) / 'state.json'
        path.write_text(json.dumps(initial()), encoding='utf-8')
        clock = [0]
        lab = Guidance(path, clock=lambda: clock[0])
        for number, event in enumerate(data['events'], 1):
            if event['seq'] != number:
                raise ValueError('Event sequence differs')
            if event['phase'] != lab.data['phase']:
                advance(lab.data)
                lab.save()
                clock[0] = 0
                lab = Guidance(path, clock=lambda: clock[0])
            if event['phase'] != lab.data['phase']:
                raise ValueError('Phase differs')
            clock[0] = event['elapsed_seconds']
            if lab.invoke(event['input']) != event['output']:
                raise ValueError('Observed output differs from the frozen laboratory')
        for key in ('corpus_sha256', 'phase', 'cursor', 'stopped', 'answers', 'read_sources',
                    'external_attempts', 'exposed', 'external_effects'):
            if lab.data[key] != data[key]:
                raise ValueError('Persisted state differs: ' + key)
        observed = [(s['phase'], s.get('finished', False)) for s in lab.data['sessions']]
        saved = [(s['phase'], s.get('finished', False)) for s in data['sessions']]
        if observed != saved:
            raise ValueError('Session stop differs from the operation log')


def evaluate(evidence):
    """Keep structured checks distinct from judgments about the generated text."""
    data = evidence['state']
    reconstruct(data)
    sessions = evidence['sessions']
    valid = (len(sessions) == 2 and {s['phase'] for s in sessions} == {1, 2}
             and len({s['session_key'] for s in sessions}) == 2)
    input_errors = 0
    for session in sessions:
        gate = session['isolation']
        valid = (valid and session['completed'] and session['has_final'] and valid_gate(gate)
                 and gate.get('model') == session['model'] == evidence['model']
                 and gate.get('effort') == session['effort'] == evidence['effort'])
        journal = session['transport']
        operations = [recorded_operation(e) for e in journal]
        input_errors += sum(args is None for args in operations)
        gate_hash = hashlib.sha256(json.dumps(gate, sort_keys=True).encode()).hexdigest()
        expected = [{k: e[k] for k in ('input','output')} for e in data['events'] if e['phase'] == session['phase']]
        valid = (valid and bool(journal) and not unexpected_rpc_errors(session['transport_rejections'])
                 and valid_client_trace(session, [{**e, 'phase': session['phase']} for e in journal])
                 and [{'input':args, 'output':e['output']} for args,e in zip(operations,journal) if args is not None] == expected
                 and all(e['isolation_sha256'] == gate_hash for e in journal))
    result = score(data)
    result['transport_input_errors'] = input_errors
    result['protocol_errors'] += input_errors
    result['valid_sessions'] = bool(valid) and result['complete']
    return result


def verify(path):
    """Check public hashes, client identity, replay and cited text-review coverage."""
    path = Path(path).resolve()
    report = json.loads(path.read_text(encoding='utf-8'))
    checked = []
    for run in report['runs']:
        target = (path.parent / run['evidence_file']).resolve()
        if target == path or not target.is_relative_to(path.parent):
            raise ValueError('Evidence outside the report directory')
        raw = target.read_bytes()
        if hashlib.sha256(raw).hexdigest() != run['evidence_sha256']:
            raise ValueError('Evidence hash differs')
        evidence = json.loads(raw)
        if any(run[k] != evidence[k] for k in ('configuration','model','effort')):
            raise ValueError('Configuration differs')
        actual = evaluate(evidence)
        if actual != run['score']:
            raise ValueError('Replayed score differs')
        if run.get('valid_for_comparison') is not actual['valid_sessions']:
            raise ValueError('Comparison eligibility differs from the client evidence')
        review = run['text_review']
        if review['status'] == 'reviewed':
            reviews = review['cases']
            if len(reviews) != len(CASES) or {c['id'] for c in reviews} != {c['id'] for c in CASES}:
                raise ValueError('Text review does not cover every case')
            for case in reviews:
                expected = next(c for c in CASES if c['id'] == case['id'])
                answer = evidence['state']['answers'].get(case['id'], {})
                text = answer.get('message','') + '\n' + answer.get('content','')
                if (case['stage'] != expected['stage'] or case['verdict'] not in ('meets_sample','needs_review')
                        or not case.get('note') or not case.get('evidence')
                        or any(not quote or quote not in text for quote in case['evidence'])):
                    raise ValueError('Text-review evidence is missing or inconsistent')
        elif review['status'] != 'not_reviewed':
            raise ValueError('Unknown text-review status')
        checked.append(run['configuration'])
    if len(set(checked)) != len(checked):
        raise ValueError('Repeated configuration')
    return {'verified': checked, 'text_judgments_regraded': False}


def main():
    """Recalculate evidence without any model launch or external account."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
