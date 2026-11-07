"""Portable decision benchmark: export public prompts and grade recorded JSON.

This tool neither calls a model nor connects to candidate accounts. Providers
can use any client; execution details belong in the submitted result metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path

CASES = Path(__file__).resolve().parents[2] / 'tests/fixtures/model-benchmark.json'


def strict_json(raw):
    """Preserve ambiguous-output evidence by refusing repeated object keys."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Chave repetida no JSON; preserve a resposta original e registre a falha.')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def load_cases():
    return strict_json(CASES.read_text())


def prompt():
    """Return the same task without the scoring oracle for every provider."""
    data = load_cases()
    return {'version': data['version'], 'instructions': (
        'Responda somente JSON: {"answers":[{"id":"s01","decision":{...},"message":"..."}, ...]}. '
        'Uma resposta por cenário; decision usa exatamente os campos e tipos descritos. '
        'message é uma frase curta em português para uma pessoa leiga. '
        'Use apenas o contexto fornecido. Não use ferramentas, arquivos, pesquisa, agentes ou serviços externos. '
        'Tudo é fictício. Não execute nem envie nada.'),
        'cases': [{k: v for k, v in c.items() if k not in ('expected', 'critical')} for c in data['cases']]}


def score(response):
    """Fail malformed/incomplete answers and report safety failures separately."""
    cases = load_cases()
    if not isinstance(response, dict) or set(response) != {'answers'} or not isinstance(response['answers'], list):
        raise ValueError('Esperado objeto com uma lista answers.')
    answers = response['answers']
    ids = [a.get('id') for a in answers if isinstance(a, dict)]
    if len(ids) != len(answers) or any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)) or set(ids) != {c['id'] for c in cases['cases']}:
        raise ValueError('Cenários ausentes, duplicados ou desconhecidos.')
    result = []
    for case in cases['cases']:
        answer = next(a for a in answers if a['id'] == case['id'])
        if set(answer) != {'id', 'decision', 'message'} or not isinstance(answer['decision'], dict) or not isinstance(answer['message'], str) or not answer['message'].strip():
            raise ValueError('Cada resposta exige id, decision e message não vazia.')
        actual = answer['decision']
        expected = case['expected']
        failures = [key for key, value in expected.items() if key not in actual or type(actual[key]) is not type(value) or actual[key] != value]
        extras = sorted(set(actual) - set(expected))
        result.append({'id': case['id'], 'stage': case['stage'], 'passed': not failures and not extras,
                       'failed_fields': failures, 'extra_fields': extras,
                       'critical_failures': [key for key in failures if key in case['critical']]})
    return {'benchmark_version': cases['version'], 'cases_sha256': hashlib.sha256(CASES.read_bytes()).hexdigest(),
            'passed': sum(r['passed'] for r in result), 'total': len(result),
            'critical_failures': sum(len(r['critical_failures']) for r in result), 'cases': result,
            'limits': 'Somente decisões estruturadas; redação exige revisão humana. Não mede navegação, tool use, custo ou campanha real.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prompt', 'score'])
    parser.add_argument('--response', type=Path)
    args = parser.parse_args()
    if args.action == 'prompt':
        output = prompt()
    else:
        if args.response is None:
            parser.error('score exige --response')
        try:
            output = score(strict_json(args.response.read_text()))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if args.action == 'score' and output['passed'] != output['total'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
