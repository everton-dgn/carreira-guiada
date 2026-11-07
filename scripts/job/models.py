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
    'preparation': 'Perfil, currículo e treino de entrevistas',
    'screening': 'Pesquisa, triagem e análise de empresas',
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
TOOL_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-07-browser-mail.json'
ADVERSARIAL_REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-07-adversarial.json'


def adversarial_evidence(model, effort, stage, report):
    """Expose attack observations without turning absence of failure into immunity."""
    if stage not in ('screening', 'application', 'mail', 'continuity') or effort is None:
        return None
    measured_stage = 'screening' if stage == 'application' else stage
    key = ALIASES.get(model.casefold(), model.casefold())
    matches = lambda r: ALIASES.get(r['model'].casefold(), r['model'].casefold()) == key and r['effort'] == effort
    all_runs = [r for r in report.get('runs', []) if matches(r)]
    runs = [r for r in all_runs if r.get('included_in_comparison') is True]
    negative = [c for r in all_runs for c in r['score']['cases'] if c['stage'] == measured_stage and
                (c['unsafe_attempts'] or c['resistance'] == 'failed')]
    base = {'source': 'docs/benchmarks/2026-11-07-adversarial.json', 'scope': 'fictional_adversarial_tool_decisions',
            'measured_stage': measured_stage, 'immunity_proven': False, 'real_services_validated': False,
            'protocol_revision': report.get('measurement_protocol_revision'),
            'measurement_cautions': report.get('measurement_cautions', [])}
    if not runs and not negative:
        missing = next((r for r in report.get('unmeasured', []) if matches(r)), None)
        return {**base, 'status': 'not_measured', 'reason': missing['reason'] if missing else 'Sem medição nesta configuração e etapa.'}
    cases = [c for r in runs for c in r['score']['cases'] if c['stage'] == measured_stage]
    attacks = [c for c in cases if c['condition'] == 'attack']
    unsafe = sum(c['unsafe_attempts'] for c in cases)
    valid = all(r['score']['valid_sessions'] for r in runs)
    return {**base, 'date': report['date'], 'status': 'unsafe_attempt_observed' if negative else
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
    return {'source': 'docs/benchmarks/2026-11-07-browser-mail.json', 'date': report['date'],
            'scope': 'isolated_browser_mail_tools', 'runs': len(runs),
            'passed': sum(c['passed'] for c in checks), 'total': sum(c['total'] for c in checks),
            'eligible_for_suggestion': eligible, 'real_services_validated': False,
            'critical_failures': [f for r in runs for f in r['score']['critical_failures']],
            'failed_write_attempts': sum(r['score']['failed_write_attempts'] for r in runs)}


def evidence(model, effort, stage):
    """Attach matching exploratory results, never infer browser competence."""
    if effort is None or not REPORT.is_file():
        return None
    report = json.loads(REPORT.read_text())
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
        """Prefer stage evidence among declared options, without claiming a winner."""
        saved = self.show()
        candidates = [{'provider': p['name'], **m} for p in saved['providers'] for m in p['models']]
        report = json.loads(TOOL_REPORT.read_text()) if TOOL_REPORT.is_file() else {}
        attacks = json.loads(ADVERSARIAL_REPORT.read_text()) if ADVERSARIAL_REPORT.is_file() else {}
        stages = []
        for stage, label in STAGES.items():
            preferred = ('astra', 'opus', 'terra', 'm3') if stage == 'preparation' else ('terra', 'astra', 'opus', 'm3')
            ordered = sorted(candidates, key=lambda m: preferred.index(ALIASES.get(m['name'].casefold())) if ALIASES.get(m['name'].casefold()) in preferred else len(preferred))
            choice = ordered[0] if ordered else None
            effort = None
            if choice:
                known = ALIASES.get(choice['name'].casefold())
                desired = ('xhigh',) if known == 'm3' else ('max',) if known == 'glm' else ('high', 'medium') if stage == 'preparation' else ('medium', 'high')
                effort = next((e for e in desired if e in choice.get('efforts', [])), None) if known else None
            tested = []
            for option in ordered:
                for level in EFFORTS:
                    if level not in option.get('efforts', []):
                        continue
                    observation = tool_evidence(option['name'], level, stage, report)
                    safety = adversarial_evidence(option['name'], level, stage, attacks)
                    if observation and observation['eligible_for_suggestion'] and not (safety and safety['status'] == 'unsafe_attempt_observed'):
                        tested.append((option, level, observation))
            if tested:
                choice, effort, observed = tested[0]
            else:
                observed = tool_evidence(choice['name'], effort, stage, report) if choice else None
            measured = evidence(choice['name'], effort, stage) if choice else None
            safety = adversarial_evidence(choice['name'], effort, stage, attacks) if choice else None
            unsafe = safety and safety['status'] == 'unsafe_attempt_observed'
            stages.append({'stage': stage, 'label': label,
                           'model': {k: choice[k] for k in ('provider', 'name')} if choice else None,
                           'effort': effort, 'basis': 'supervision_required' if unsafe else 'exploratory_tools' if tested else 'initial_guidance' if choice and ALIASES.get(choice['name'].casefold()) else 'unmeasured',
                           'benchmark_evidence': measured,
                           'tool_evidence': observed,
                           'adversarial_evidence': safety,
                           'tool_alternatives': [{'provider': m['provider'], 'name': m['name'], 'effort': e} for m, e, _ in tested],
                           'tools_required': TOOLS[stage],
                           'message': 'Houve tentativa indevida nesta etapa do teste adversarial. Use esta opção com conferência humana antes de qualquer envio; o bloqueio da ferramenta não comprova resistência do modelo.' if unsafe else 'Esta opção passou nos critérios operacionais da etapa no laboratório fictício. Isso não comprova resistência a ataques; confira a evidência de segurança separada e as ferramentas na sua sessão.' if tested else 'Confirme as ferramentas nesta sessão e faça uma primeira etapa acompanhada. A sugestão não comprova automação.' if choice else 'Continue com o modelo atual. Se quiser comparar, diga quais opções aparecem no seu aplicativo.'})
        return {'decision': saved['decision'], 'stages': stages, 'automatic_switch': False,
                'benchmark': 'docs/BENCHMARKS.md',
                'limits': 'Uma jornada fictícia não comprova serviços reais, custo, superioridade estatística ou execução por dias. Empates preservam a preferência inicial e o menor esforço disponível testado.'}
