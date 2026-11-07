"""Recompute a published browser benchmark from its fictional evidence files."""
import argparse
import hashlib
import json
from pathlib import Path

from .bench_score import grade


def verify(path):
    path = path.resolve()
    report = json.loads(path.read_text())
    checked = []
    for run in report['runs']:
        evidence_path = (path.parent / run['evidence_file']).resolve()
        if not evidence_path.is_relative_to(path.parent):
            raise ValueError('A evidência precisa estar na pasta do relatório.')
        raw = evidence_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != run['evidence_sha256']:
            raise ValueError('Hash divergente: ' + run['configuration'])
        actual = grade(json.loads(raw))
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
