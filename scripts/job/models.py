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
}
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max', 'ultra')
REPORT = Path(__file__).resolve().parents[2] / 'docs/benchmarks/2026-11-07-decisions.json'


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
        """Suggest only declared models; defaults are guidance, not a benchmark ranking."""
        saved = self.show()
        candidates = [{'provider': p['name'], **m} for p in saved['providers'] for m in p['models']]
        stages = []
        for stage, label in STAGES.items():
            preferred = ('astra', 'opus', 'terra', 'm3') if stage == 'preparation' else ('terra', 'astra', 'opus', 'm3')
            ordered = sorted(candidates, key=lambda m: preferred.index(ALIASES.get(m['name'].casefold())) if ALIASES.get(m['name'].casefold()) in preferred else len(preferred))
            choice = ordered[0] if ordered else None
            effort = None
            if choice:
                known = ALIASES.get(choice['name'].casefold())
                desired = ('xhigh',) if known == 'm3' else ('high', 'medium') if stage == 'preparation' else ('medium', 'high')
                effort = next((e for e in desired if e in choice.get('efforts', [])), None) if known else None
            measured = evidence(choice['name'], effort, stage) if choice else None
            stages.append({'stage': stage, 'label': label,
                           'model': {k: choice[k] for k in ('provider', 'name')} if choice else None,
                           'effort': effort, 'basis': 'initial_guidance' if choice and ALIASES.get(choice['name'].casefold()) else 'unmeasured',
                           'benchmark_evidence': measured,
                           'tools_required': TOOLS[stage],
                           'message': 'Confirme as ferramentas nesta sessão e faça uma primeira etapa acompanhada. A sugestão não comprova automação.' if choice else 'Continue com o modelo atual. Se quiser comparar, diga quais opções aparecem no seu aplicativo.'})
        return {'decision': saved['decision'], 'stages': stages, 'automatic_switch': False,
                'benchmark': 'docs/BENCHMARKS.md',
                'limits': 'As sugestões iniciais não são um ranking. Testes de decisões não comprovam navegação, custo ou execução contínua.'}
