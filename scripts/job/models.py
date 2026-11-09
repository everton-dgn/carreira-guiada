"""Optional, provider-neutral model access preferences, separate from consent.

Names describe what the person can select in their own client. Saving them
does not authenticate, install, switch models or authorize data transmission.
"""
import json
import re
from pathlib import Path
from .profile import Profile
from .research_scope import fields, table_exists

STAGES = {
    'preparation': 'Primeiras escolhas',
    'screening': 'Pesquisa e triagem de vagas',
    'application': 'Preenchimento e candidatura',
    'mail': 'Retornos por e-mail e próximas etapas',
    'continuity': 'Parar, conferir pendências e retomar',
}
TOOLS = {
    'preparation': ['local_files'],
    'screening': ['local_files', 'public_research'],
    'application': ['local_files', 'browser'],
    'mail': ['local_files', 'mail', 'browser'],
    'continuity': ['local_files', 'pending_step_connections'],
}
ALIASES = {
    'gpt-6.1-terra': 'terra', 'gpt-6.1 terra': 'terra', 'terra 6.1': 'terra',
    'gpt-6-astra': 'astra', 'gpt-6 astra': 'astra',
    'claude-opus-5-5': 'opus', 'claude opus 5.5': 'opus', 'opus 5.5': 'opus',
    'minimax-m3.1-flash[1m]': 'm3', 'minimax m3.1 flash': 'm3',
    'gpt-6.1-sol': 'sol', 'gpt-6.1 sol': 'sol',
    'claude-fable-5-1': 'fable', 'claude fable 5.1': 'fable',
    'claude-haiku-5-5': 'haiku', 'claude haiku 5.5': 'haiku',
    'glm-5.3[1m]': 'glm', 'glm 5.3': 'glm',
}
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max', 'ultra')
REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-07-decisions.json'
TOOL_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-08-complete-browser.json'
ADVERSARIAL_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-07-adversarial.json'
CODEX_ADVERSARIAL_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-07-codex-adversarial.json'
PREPARATION_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-08-complete-preparation.json'
GUIDANCE_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-08-complete-guidance.json'
COMPLETE_ADVERSARIAL_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-08-complete-security.json'


PREPARATION_TASKS = {
    'onboarding': ('Primeiras escolhas', ('novice', 'search_resume')),
    'cv': ('Currículo', ('cv_draft', 'cv_correction')),
    'career': ('Guia de carreira', ('career_compare', 'career_resume')),
}
GUIDANCE_TASKS = {
    'interview': ('Treino de entrevistas', ('g01', 'g02', 'g03', 'g04', 'g09', 'g10')),
    'presence': ('LinkedIn e GitHub', ('g05', 'g11', 'g12')),
    'company': ('Dossiê da empresa', ('g06', 'g13')),
    'offers': ('Comparação de propostas', ('g07', 'g14')),
    'negotiation': ('Negociação', ('g08', 'g15')),
    'continuity': ('Parar e retomar a orientação', ('g16',)),
}


def _observed_dates(runs, report):
    """Retain the collection dates, including reused observations."""
    return sorted({date for run in runs for date in
                   (run.get('observed_dates') or [run.get('observed_date', report.get('date'))])
                   if date})


def _task_rows(cases, task, identifiers):
    """Check exact case identities rather than accepting a row count."""
    rows = [c for c in cases if c.get('id') in identifiers or c.get('stage') == task]
    complete = (len(rows) == len(identifiers)
                and {c.get('id') for c in rows} == set(identifiers)
                and all(c.get('stage') == task for c in rows))
    return rows, complete


def _text_observation(runs, report, task, identifiers, kind):
    """Combine mechanical and content evidence only within the same task."""
    qualified, passed, cautions, format_errors = True, 0, [], []
    for run in runs:
        score = run.get('score') or {}
        review = run.get('text_review') or {}
        decisions, decisions_complete = _task_rows(score.get('cases', []), task, identifiers)
        reviews, reviews_complete = _task_rows(review.get('cases', []), task, identifiers)
        passed += sum(sum(c.get('id') == ident for c in decisions) == 1
                      and any(c.get('id') == ident and c.get('stage') == task
                              and c.get('passed') is True for c in decisions)
                      for ident in identifiers)
        cautions.extend(c['note'] for c in reviews if c.get('verdict') == 'needs_review' and c.get('note'))
        if not decisions_complete or not reviews_complete:
            cautions.append('Faltam casos distintos da tarefa ou há identidade/etapa inconsistente no relatório.')
        if kind == 'preparation':
            session_valid = (run.get('session_complete') is True
                             and run.get('tool_calls') == 0 and not run.get('format_error'))
            if run.get('format_error'):
                format_errors.append(run['format_error'])
        else:
            session_valid = (run.get('valid_for_comparison') is True
                             and score.get('valid_sessions') is True and score.get('complete') is True
                             and score.get('external_attempts') == 0 and score.get('external_effects') == 0)
        qualified = (qualified and session_valid and review.get('status') == 'reviewed'
                     and decisions_complete and reviews_complete
                     and all(c.get('passed') is True for c in decisions)
                     and all(c.get('verdict') == 'meets_sample' for c in reviews))
    observation = {
        'source': report.get('source'), 'date': report.get('date'), 'scope': report.get('scope'),
        'observed_dates': _observed_dates(runs, report), 'task': task, 'runs': len(runs),
        'passed': passed, 'total': len(runs) * len(identifiers),
        'eligible_for_suggestion': bool(runs and qualified),
        'text_cautions': list(dict.fromkeys(cautions)),
        'reviewer_kind': 'model', 'independent_review': False,
        'real_services_validated': False, 'tools_validated': False,
    }
    if kind == 'preparation':
        observation['format_errors'] = format_errors
    return observation


def _text_recommendations(candidates, report, kind, tasks):
    """Keep declared order and lowest eligible effort without ranking providers."""
    results = []
    for task, (label, identifiers) in tasks.items():
        observations, eligible = [], []
        for option in candidates:
            key = ALIASES.get(option['name'].casefold(), option['name'].casefold())
            for level in EFFORTS:
                if level not in option.get('efforts', []):
                    continue
                runs = [r for r in report.get('runs', [])
                        if ALIASES.get(r['model'].casefold(), r['model'].casefold()) == key
                        and r['effort'] == level]
                if not runs:
                    continue
                observation = _text_observation(runs, report, task, identifiers, kind)
                entry = (option, level, observation)
                observations.append(entry)
                if observation['eligible_for_suggestion']:
                    eligible.append(entry)
        choices = eligible or observations
        choice, effort, observation = choices[0] if choices else (candidates[0] if candidates else None, None, None)
        results.append({
            'task': task, 'label': label,
            'model': {k: choice[k] for k in ('provider', 'name')} if choice else None,
            'effort': effort,
            'basis': 'exploratory_' + kind if eligible else 'review_required' if observations else 'unmeasured',
            kind + '_evidence': observation,
            'alternatives': [{'provider': m['provider'], 'name': m['name'], 'effort': e} for m, e, _ in eligible],
            'message': (
                'Esta configuração concluiu os recortes da tarefa sem ressalva na revisão de conteúdo. '
                'É uma amostra curta, sem prova de superioridade ou uso de serviços reais.' if eligible else
                'Há ressalvas ou evidência incompleta nesta tarefa. Confira o relatório e revise o material antes de usá-lo.' if observations else
                'Sem medição desta tarefa nas opções informadas. Podemos continuar com o modelo atual, conferindo o material.'),
        })
    return results


def preparation_recommendations(candidates, report):
    """Recommend preparation by exact cases and their reviewed content."""
    return _text_recommendations(candidates, report, 'preparation', PREPARATION_TASKS)


def guidance_recommendations(candidates, report):
    """Recommend each guidance task independently of browser or voice competence."""
    return _text_recommendations(candidates, report, 'guidance', GUIDANCE_TASKS)


def adversarial_evidence(model, effort, stage, report):
    """Expose attack observations without turning absence of failure into immunity."""
    if stage not in ('screening', 'application', 'mail', 'continuity') or effort is None:
        return None
    if isinstance(report, list):
        if not report:
            return adversarial_evidence(model, effort, stage, {}) | {'previous_observations': []}
        observations = [adversarial_evidence(model, effort, stage, item) for item in report]
        measured = [item for item in observations if item['status'] != 'not_measured']
        negative = [item for item in measured if item['status'] == 'unsafe_attempt_observed']
        selected = (negative or measured or observations)[-1]
        # Different protocol revisions are separate observations, never summed.
        return {**selected, 'previous_observations': [item for item in measured if item is not selected]}
    measured_stage = 'screening' if stage == 'application' else stage
    key = ALIASES.get(model.casefold(), model.casefold())
    matches = lambda r: ALIASES.get(r['model'].casefold(), r['model'].casefold()) == key and r['effort'] == effort
    all_runs = [r for r in report.get('runs', []) if matches(r)]
    runs = [r for r in all_runs if r.get('included_in_comparison') is True]
    negative = [c for r in all_runs for c in r['score']['cases'] if c['stage'] == measured_stage and
                (c['unsafe_attempts'] or c['resistance'] == 'failed')]
    base = {'source': report.get('source', 'docs/benchmarks/2026-11-07-adversarial.json'), 'scope': 'fictional_adversarial_tool_decisions',
            'measured_stage': measured_stage, 'immunity_proven': False, 'real_services_validated': False,
            'protocol_revision': report.get('measurement_protocol_revision'),
            'measurement_cautions': report.get('measurement_cautions', [])}
    if not runs and not negative:
        missing = next((r for r in report.get('unmeasured', []) if matches(r)), None)
        reason = (missing['reason'] if missing else
                  'Há execuções preservadas, mas excluídas da comparação; confira o motivo no relatório.' if all_runs else
                  'Sem medição nesta configuração e etapa.')
        return {**base, 'status': 'not_measured', 'reason': reason}
    cases = [c for r in runs for c in r['score']['cases'] if c['stage'] == measured_stage]
    attacks = [c for c in cases if c['condition'] == 'attack']
    unsafe = sum(c['unsafe_attempts'] for c in cases)
    valid = all(r['score']['valid_sessions'] for r in runs)
    return {**base, 'date': report['date'], 'observed_dates': _observed_dates(runs or all_runs, report), 'status': 'unsafe_attempt_observed' if negative else
            'observed_in_sample' if valid and attacks and all(c['resistance'] == 'observed' for c in attacks) else 'inconclusive',
            'attacks': len(attacks), 'exposed': sum(c['exposed'] for c in attacks),
            'unsafe_attempts': unsafe, 'system_blocks': sum(c['system_blocks'] for c in cases),
            'attack_goal_attempts': sum(c.get('attack_goal_attempts', 0) for c in cases),
            'negative_evidence_in_excluded_runs': any(c['stage'] == measured_stage and (c['unsafe_attempts'] or c['resistance'] == 'failed') for r in all_runs if not r.get('included_in_comparison') for c in r['score']['cases']),
            'utility_complete': sum(c['utility_complete'] is True for c in cases), 'utility_cases': len(cases),
            'protocol_errors': sum(c['protocol_errors'] for c in cases),
            'laboratory_errors': sum(c['laboratory_errors'] for c in cases)}


def tool_evidence(model, effort, stage, report):
    """Keep fictional browser evidence distinct from decisions and live services."""
    key = ALIASES.get(model.casefold(), model.casefold())
    runs = [r for r in report.get('runs', []) if ALIASES.get(r['model'].casefold(), r['model'].casefold()) == key
            and r['effort'] == effort and stage in r['score']['stages']]
    if not runs:
        return None
    checks = [r['score']['stages'][stage] for r in runs]
    eligible = all(r['valid_for_comparison'] and r['completed_sessions'] == 2
                   and r['score'].get('network_evidence_complete', False)
                   and not r['score']['critical_failures'] and not r['score']['failed_write_attempts']
                   and r['score']['stages'][stage]['complete'] for r in runs)
    return {'source': report.get('source'), 'date': report['date'], 'observed_dates': _observed_dates(runs, report),
            'scope': 'isolated_browser_mail_tools', 'runs': len(runs),
            'passed': sum(c['passed'] for c in checks), 'total': sum(c['total'] for c in checks),
            'eligible_for_suggestion': eligible, 'real_services_validated': False,
            'critical_failures': [f for r in runs for f in r['score']['critical_failures']],
            'failed_write_attempts': sum(r['score']['failed_write_attempts'] for r in runs)}


def evidence(model, effort, stage):
    """Attach matching exploratory results, never infer browser competence."""
    if effort is None or not REPORT.is_file():
        return None
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    key = ALIASES.get(model.casefold(), model.casefold())
    runs = [r for r in report['runs'] if ALIASES.get(r['model'].casefold(), r['model'].casefold()) == key and r['effort'] == effort]
    if not runs:
        return None
    cases = [c for r in runs for c in r['score']['cases'] if c['stage'] == stage]
    cautions = list(dict.fromkeys(i['reason'] for r in runs for i in r['text_review']['issues'] if i['stage'] == stage))
    return {'source': 'docs/benchmarks/2026-11-07-decisions.json', 'date': report['date'],
            'scope': 'structured_decisions', 'runs': len(runs), 'passed': sum(c['passed'] for c in cases),
            'total': len(cases), 'critical_failures': sum(len(c['critical_failures']) for c in cases),
            'text_cautions': cautions, 'browser_validated': False}


def name(value):
    if not isinstance(value, str) or not re.fullmatch(r'[\w .+()/\[\]-]{1,100}', value) or not value.strip():
        raise ValueError('Informe somente o nome exibido no aplicativo, sem endereço, senha ou código.')
    return value.strip()


class Models:
    def __init__(self, root):
        self.profile = Profile(root)

    @staticmethod
    def validate(data):
        """Accept unknown vendors while bounding the private, non-secret record."""
        fields(data, ('decision', 'providers'))
        if data['decision'] not in ('available', 'unknown', 'later') or not isinstance(data['providers'], list) or len(data['providers']) > 20:
            raise ValueError('Escolha informar os serviços, não sei ou depois.')
        if (data['decision'] == 'available') != bool(data['providers']):
            raise ValueError('Informe os serviços disponíveis ou escolha não sei/depois.')
        seen = set()
        for provider in data['providers']:
            fields(provider, ('name', 'models'))
            key = name(provider['name']).casefold()
            if key in seen or not isinstance(provider['models'], list) or len(provider['models']) > 30:
                raise ValueError('Confira serviços repetidos e a lista de modelos.')
            seen.add(key)
            models = set()
            for model in provider['models']:
                fields(model, ('name',), ('efforts',))
                key = name(model['name']).casefold()
                efforts = model.get('efforts', [])
                if key in models or not isinstance(efforts, list) or any(not isinstance(e, str) or e not in EFFORTS for e in efforts) or len(efforts) != len(set(efforts)):
                    raise ValueError('Confira modelos repetidos e os esforços realmente disponíveis.')
                models.add(key)

    @staticmethod
    def _read(db):
        empty = {'version': 0, 'decision': 'unasked', 'providers': []}
        if not table_exists(db, 'job_model_access'):
            return empty
        row = db.execute('SELECT version,value FROM job_model_access WHERE id=1').fetchone()
        if row is None:
            return empty
        try:
            data = json.loads(row[1])
            Models.validate(data)
            if type(row[0]) is not int or row[0] < 1:
                raise ValueError('Versão inválida.')
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError('A preferência de modelos precisa de reparo; os outros dados foram preservados.') from exc
        return {'version': row[0], **data}

    def show(self):
        with self.profile._db() as db:
            return self._read(db)

    def save(self, data):
        """Save one explicit choice with optimistic concurrency, without profile edits."""
        fields(data, ('expected_version', 'decision', 'providers'))
        if type(data['expected_version']) is not int or data['expected_version'] < 0:
            raise ValueError('Confira a versão atual antes de salvar.')
        value = {k: data[k] for k in ('decision', 'providers')}
        self.validate(value)
        with self.profile._db(True) as db:
            current = self._read(db)
            if current['version'] != data['expected_version']:
                raise ValueError('A preferência mudou; confira o que já foi salvo antes de atualizar.')
            db.execute('CREATE TABLE IF NOT EXISTS job_model_access (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, value TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO job_model_access VALUES (1,?,?)', (current['version'] + 1, json.dumps(value, ensure_ascii=False)))
            return self._read(db)

    def guidance(self):
        """Expose optional advice; a broken optional record cannot block start."""
        try:
            saved = self.show()
        except ValueError:
            return {'optional': True, 'decision': 'repair_needed', 'question': None,
                    'message': 'A preferência de modelos precisa de conferência. Podemos continuar com o modelo atual.'}
        question = ('Quais aplicativos ou serviços de IA você já usa? Pode dizer os nomes, como ChatGPT, Claude, Gemini ou outro. Também pode responder não sei ou deixar para depois.' if saved['decision'] == 'unasked' else None)
        return {**saved, 'optional': True, 'question': question,
                'message': 'Essa escolha é opcional. Podemos começar com o modelo atual; não precisa contratar outro serviço.'}

    def recommend(self):
        """Use task evidence among declared options without hidden brand rankings."""
        saved = self.show()
        candidates = [{'provider': p['name'], **m} for p in saved['providers'] for m in p['models']]
        report = json.loads(TOOL_REPORT.read_text(encoding='utf-8')) if TOOL_REPORT.is_file() else {}
        attacks = [json.loads(path.read_text(encoding='utf-8')) for path in
                   (ADVERSARIAL_REPORT, CODEX_ADVERSARIAL_REPORT, COMPLETE_ADVERSARIAL_REPORT)
                   if path.is_file()]
        preparation = preparation_recommendations(candidates,
            json.loads(PREPARATION_REPORT.read_text(encoding='utf-8')) if PREPARATION_REPORT.is_file() else {})
        guidance = guidance_recommendations(candidates,
            json.loads(GUIDANCE_REPORT.read_text(encoding='utf-8')) if GUIDANCE_REPORT.is_file() else {})
        stages = []
        for stage, label in STAGES.items():
            if stage == 'preparation':
                first = preparation[0]
                stages.append({
                    'stage': stage, 'label': label, 'model': first['model'], 'effort': first['effort'],
                    'basis': first['basis'], 'preparation_evidence': first['preparation_evidence'],
                    'benchmark_evidence': evidence(first['model']['name'], first['effort'], stage) if first['model'] else None,
                    'tool_evidence': None, 'adversarial_evidence': None, 'tool_alternatives': [],
                    'tools_required': TOOLS[stage], 'message': first['message'],
                })
                continue
            tested, observations = [], []
            for option in candidates:
                for level in EFFORTS:
                    if level not in option.get('efforts', []):
                        continue
                    observation = tool_evidence(option['name'], level, stage, report)
                    safety = adversarial_evidence(option['name'], level, stage, attacks)
                    entry = (option, level, observation, safety)
                    if observation or safety and safety['status'] != 'not_measured':
                        observations.append(entry)
                    if (observation and observation['eligible_for_suggestion']
                            and not (safety and safety['status'] == 'unsafe_attempt_observed')):
                        tested.append(entry)
            choices = tested or observations
            choice, effort, observed, safety = (choices[0] if choices else
                (candidates[0] if candidates else None, None, None, None))
            measured = evidence(choice['name'], effort, stage) if choice else None
            unsafe = safety and safety['status'] == 'unsafe_attempt_observed'
            stages.append({
                'stage': stage, 'label': label,
                'model': {k: choice[k] for k in ('provider', 'name')} if choice else None,
                'effort': effort,
                'basis': ('supervision_required' if unsafe else 'exploratory_tools' if tested else
                          'review_required' if observations else 'unmeasured'),
                'benchmark_evidence': measured, 'tool_evidence': observed, 'adversarial_evidence': safety,
                'tool_alternatives': [{'provider': m['provider'], 'name': m['name'], 'effort': e}
                                      for m, e, _, _ in tested],
                'tools_required': TOOLS[stage],
                'message': (
                    'Houve tentativa indevida nesta etapa do teste adversarial. Use esta opção com conferência humana antes de qualquer envio; o bloqueio da ferramenta não comprova resistência do modelo.' if unsafe else
                    'Esta opção passou nos critérios operacionais da etapa no laboratório fictício. Isso não comprova resistência a ataques; confira a evidência de segurança separada e as ferramentas na sua sessão.' if tested else
                    'Há medições, mas esta opção não cumpriu todos os critérios operacionais da etapa. Confira as ressalvas antes de usar ferramentas.' if observations else
                    'Sem medição operacional compatível com suas opções. Confirme as ferramentas nesta sessão e faça uma primeira etapa acompanhada.' if choice else
                    'Continue com o modelo atual. Se quiser comparar, diga quais opções aparecem no seu aplicativo.'),
            })
        return {
            'decision': saved['decision'], 'stages': stages, 'automatic_switch': False,
            'preparation_by_task': preparation, 'guidance_by_task': guidance,
            'benchmark': 'docs/BENCHMARKS.md',
            'limits': 'Uma jornada fictícia não comprova serviços reais, custo, superioridade estatística ou execução por dias. Entre opções elegíveis, preservamos a ordem declarada e o menor esforço testado disponível; isso não prova que seja o mais barato ou o melhor.',
        }
