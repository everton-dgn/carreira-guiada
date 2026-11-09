"""Recompute a published browser benchmark from its fictional evidence files."""
import argparse
import hashlib
import json
from pathlib import Path

from .bench_score import grade


def verify(path):
    """Replay historical effects or the newer client-bound evidence format."""
    path = path.resolve()
    report = json.loads(path.read_text(encoding='utf-8'))
    checked = []
    for run in report['runs']:
        evidence_path = (path.parent / run['evidence_file']).resolve()
        if not evidence_path.is_relative_to(path.parent):
            raise ValueError('A evidência precisa estar na pasta do relatório.')
        raw = evidence_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != run['evidence_sha256']:
            raise ValueError('Hash divergente: ' + run['configuration'])
        evidence = json.loads(raw)
        if 'client_sessions' in evidence:
            from .benchmark_browser_report import evaluate
            if any(run[k] != evidence[k] for k in ('configuration', 'model', 'effort')):
                raise ValueError('Identidade divergente da execução.')
            actual = evaluate(evidence)
            eligible = actual['restricted_client_valid'] and actual.get('session_timing_valid', False)
            if run['valid_for_comparison'] is not eligible:
                raise ValueError('Validade da comparação divergente.')
        else:
            actual = grade(evidence)
        if actual != run['score']:
            raise ValueError('Pontuação divergente: ' + run['configuration'])
        checked.append(run['configuration'])
    return {'verified': checked, 'count': len(checked), 'scope': 'published_fictional_evidence'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.report), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
