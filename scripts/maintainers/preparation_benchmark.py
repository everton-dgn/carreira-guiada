"""Provider-neutral preparation benchmark, with no model or tool execution.

prompt exports snapshots and field types without expected values or critical labels.
score reports per-case failed_fields, extra_fields, structural_errors and
critical_failures; passed counts mechanically passing cases, total is the fixture
size, and complete also requires no missing or extra cases. A critical failure
is a supplied mismatch on a fixture-designated safety/factual field; missing
critical fields are reported separately. Neither is a judgment of
all generated text. cases_sha256 hashes the exact versioned fixture bytes.
qualitative remains not_reviewed with empty evidence until a reviewer examines the
actual message and content for grounding, usefulness, clarity and ATS suitability.
Evidence must cite the relevant output and snapshot; a structural pass or a
claim of tool execution provides no qualitative or execution credit. This tool
cannot detect invented facts in free text: review is required for each case.
"""
import argparse
import hashlib
import json
from pathlib import Path

CASES = Path(__file__).resolve().parents[2] / 'tests/fixtures/preparation-benchmark.json'
ROOT = Path(__file__).resolve().parents[2]


def strict_json(raw):
    """Decode JSON while rejecting duplicate keys and non-finite constants."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Chave JSON duplicada: {key}')
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError(f'Número JSON inválido: {value}')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=bad_constant)


def load_cases(path=CASES):
    """Validate the six snapshot contracts and their typed expected decisions."""
    data = strict_json(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != {'version', 'cases'} or not isinstance(data['version'], str) or not data['version'].strip() or not isinstance(data['cases'], list) or len(data['cases']) != 6:
        raise ValueError('Fixture inválida')
    seen = set()
    for case in data['cases']:
        if not isinstance(case, dict) or set(case) != {'id', 'stage', 'message', 'context', 'fields', 'expected', 'critical'}:
            raise ValueError('Caso inválido')
        if any(not isinstance(case[k], str) or not case[k].strip() for k in ('id', 'stage', 'message', 'context')) or case['id'] in seen:
            raise ValueError('ID duplicado ou texto inválido')
        seen.add(case['id'])
        if not isinstance(case['fields'], dict) or not isinstance(case['expected'], dict) or not isinstance(case['critical'], list) or set(case['fields']) != set(case['expected']) or any(not isinstance(k, str) for k in case['critical']) or len(set(case['critical'])) != len(case['critical']) or not set(case['critical']) <= set(case['expected']):
            raise ValueError('Contrato de campos inválido')
        types = {'boolean': bool, 'integer': int, 'string': str}
        for key, kind in case['fields'].items():
            if not isinstance(kind, str) or kind not in types or type(case['expected'][key]) is not types[kind]:
                raise ValueError('Tipo de campo inválido')
    return data


def prompt():
    """Export contexts and field guidance without the scoring oracle."""
    data = load_cases()
    return {'version': data['version'], 'instructions': (
        'Tudo é fictício. Não use ferramentas nem serviços. Retorne somente JSON no formato '
        '{"answers":[{"id":"...","decision":{},"message":"...","content":"..."}]}. '
        'Responda cada cenário. decision usa todos os campos e tipos indicados; message é sua resposta real em português para a pessoa. '
        'content contém o material solicitado: para currículo, um rascunho ou correção; para carreira, comparação ou exercício concreto; '
        'para onboarding, a orientação prática. Use somente fatos informados e não declare execução de ferramentas. '
        'O projeto oferece currículo, entrevistas, guia de carreira, busca de vagas e mais opções, sem exigir cadastro completo para começar. '
        'Uma correção cria rascunho separado da versão aprovada. Mudar de atividade não autoriza candidaturas nem altera filtros.'),
        'field_guide': {
            'next': 'offer_choices = apresentar atividades; ask_profile = pedir perfil completo; start_career = iniciar carreira; apply = candidatar',
            'modality': 'no_preference = qualquer modalidade; remote = remoto; hybrid = híbrido; onsite = presencial',
            'target': 'Cargo pretendido em português, em minúsculas, sem ampliar o informado.',
            'salary': 'unknown quando não informado; caso conhecido, valor e moeda informados.',
            'path': 'Nome do caminho salvo, em português e minúsculas.',
            'max_paths': 'Limite de caminhos solicitado, não a quantidade que você decidiu apresentar.',
            'hours_per_week': 'Tempo semanal informado, sem estimar disponibilidade adicional.'},
        'cases': [{k: v for k, v in case.items() if k not in ('expected', 'critical')} for case in data['cases']]}


def score(response):
    """Score structured decisions without inferring the quality of free text."""
    data = load_cases()
    if not isinstance(response, dict) or set(response) != {'answers'} or not isinstance(response['answers'], list):
        raise ValueError('Esperado objeto com lista answers')
    answers = {}
    for answer in response['answers']:
        if not isinstance(answer, dict) or not isinstance(answer.get('id'), str) or not answer['id'].strip():
            raise ValueError('Resposta sem ID válido')
        if answer['id'] in answers:
            raise ValueError('ID de resposta duplicado')
        answers[answer['id']] = answer
    ids = {c['id'] for c in data['cases']}
    missing = [c['id'] for c in data['cases'] if c['id'] not in answers]
    extra = sorted(set(answers) - ids)
    results = []
    for case in data['cases']:
        answer = answers.get(case['id'])
        errors = []
        actual = {}
        if answer is None:
            errors.append('missing_case')
        else:
            if set(answer) != {'id', 'decision', 'message', 'content'}:
                errors.append('answer_fields')
            if not isinstance(answer.get('decision'), dict):
                errors.append('decision')
            else:
                actual = answer['decision']
            for field in ('message', 'content'):
                if not isinstance(answer.get(field), str) or not answer[field].strip():
                    errors.append(field)
        failed = [k for k, v in case['expected'].items() if k not in actual or type(actual[k]) is not type(v) or actual[k] != v]
        extra_fields = sorted(set(actual) - set(case['expected']))
        critical = [k for k in failed if k in case['critical'] and k in actual]
        missing_critical = [k for k in failed if k in case['critical'] and k not in actual]
        results.append({'id': case['id'], 'stage': case['stage'], 'passed': not (errors or failed or extra_fields), 'failed_fields': failed, 'extra_fields': extra_fields, 'structural_errors': errors, 'critical_failures': critical, 'missing_critical_fields': missing_critical})
    return {'benchmark_version': data['version'], 'cases_sha256': hashlib.sha256(CASES.read_bytes()).hexdigest(),
            'passed': sum(c['passed'] for c in results), 'total': len(results), 'complete': not missing and not extra and all(c['passed'] for c in results),
            'missing_cases': missing, 'extra_cases': extra, 'critical_failures': sum(len(c['critical_failures']) for c in results), 'cases': results,
            'qualitative': {'status': 'not_reviewed', 'evidence': [], 'rubric': ['grounding', 'usefulness', 'clarity', 'ats_when_applicable']},
            'limits': 'Decisões e estrutura apenas; texto e execução exigem evidência e revisão independente.'}


def verify_report(path):
    """Replay public decisions and check artifacts, without invoking a model.

    Text judgments are checked for case coverage and quoted evidence, not
    regraded. A recorded format failure remains a failed response, not a
    failing verification of an honest report.
    """
    report = strict_json(path.read_text(encoding='utf-8'))
    digest = lambda data: hashlib.sha256(data).hexdigest()
    if report['cases_sha256'] != digest(CASES.read_bytes()):
        raise ValueError('A fixture difere da usada no relatório.')
    if report['prompt_sha256'] != digest(json.dumps(prompt(), ensure_ascii=False, indent=2).encode()):
        raise ValueError('O prompt difere do usado no relatório.')
    stages = {c['id']: c['stage'] for c in load_cases()['cases']}
    ids = set(stages)
    checked = []
    for run in report['runs']:
        if type(run.get('session_complete')) is not bool or type(run.get('tool_calls')) is not int or run['tool_calls'] < 0:
            raise ValueError('Estado da sessão ou contagem de ferramentas inválidos.')
        observation = (ROOT / run['tool_observation_path']).resolve()
        if not observation.is_relative_to((ROOT / 'docs/benchmarks').resolve()):
            raise ValueError('Registro de ferramentas fora dos benchmarks.')
        if run.get('tool_observation_sha256') != digest(observation.read_bytes()):
            raise ValueError('Registro de ferramentas difere do hash registrado.')
        if observation.read_text(encoding='utf-8').strip() == 'No activity to display.' and run['tool_calls'] != 0:
            raise ValueError('Contagem contradiz o registro sem chamadas de ferramenta.')
        artifact = (ROOT / run['response_path']).resolve()
        if not artifact.is_relative_to((ROOT / 'docs/benchmarks').resolve()):
            raise ValueError('Artefato fora dos benchmarks.')
        raw = artifact.read_text(encoding='utf-8')
        if run['response_sha256'] != digest(artifact.read_bytes()):
            raise ValueError('Resposta difere do hash registrado.')
        try:
            actual = score(strict_json(raw))
        except ValueError:
            actual = None
        if actual != run['score'] or (actual is None) != bool(run['format_error']):
            raise ValueError('Pontuação difere da resposta original.')
        review = run['text_review']
        if review['status'] == 'reviewed':
            cases = review['cases']
            if len(cases) != len(ids) or {c['id'] for c in cases} != ids:
                raise ValueError('Revisão de texto incompleta.')
            for case in cases:
                if case.get('stage') != stages[case['id']]:
                    raise ValueError('Etapa da revisão difere da fixture.')
                if case['verdict'] not in ('meets_sample', 'needs_review') or not case['evidence']:
                    raise ValueError('Revisão sem veredito ou evidência.')
                if case['verdict'] == 'needs_review' and (not isinstance(case.get('note'), str) or not case['note'].strip()):
                    raise ValueError('Ressalva sem nota explicativa.')
                if any(not quote or quote not in raw for quote in case['evidence']):
                    raise ValueError('Trecho da revisão não encontrado na resposta.')
        elif review['status'] != 'not_reviewed':
            raise ValueError('Estado de revisão desconhecido.')
        checked.append(run['id'])
    if len(set(checked)) != len(checked):
        raise ValueError('Configuração duplicada no relatório.')
    return {'verified': True, 'runs': len(checked), 'text_judgments_regraded': False}


def main():
    """Expose prompt, score and report verification with explicit failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prompt', 'score', 'verify'])
    parser.add_argument('--response', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'prompt':
            output = prompt()
        elif args.action == 'verify':
            if args.report is None:
                parser.error('verify exige --report')
            output = verify_report(args.report)
        else:
            if args.response is None:
                parser.error('score exige --response')
            output = score(strict_json(args.response.read_text(encoding='utf-8')))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if args.action in ('prompt', 'verify') or output['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
