"""Perfil privado versionado; save substitui UMA seção (não faz merge).

identity: {name: str, email: str, phone?: str, location?: str,
timezone?: nome IANA, links?: [URL https/http]}.
preferences: veja policy.py e templates/profile.json.
permissions: {research|register|fill|apply|email_read|email_reply|email_trash|
schedule|assessment: 'allow'|'ask'|'deny', confirmed?: [nomes das ações]}.
Cada allow exige ação em confirmed, declaração explícita do usuário, nunca
inferida pelo chamador. Ações omitidas continuam pendentes no onboarding.
limits: {mode: 'chat', browser_tabs?: int de 1 a 5}, padrão de duas abas próprias.
connections: {accounts: [{provider: str, alias: str, address: str}]}.
Não armazenar senhas/tokens/cookies. Accounts pode ser vazio no modo chat.
Seções parciais podem ser salvas; approve exige todas completas. Status retorna
apenas perguntas e nomes de seções faltantes, sem dados pessoais. A aprovação
é uma chamada explícita para uma versão; qualquer mudança a invalida.
"""
import json
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .policy import obj, string, strings, validate_preferences

from .sources import normalize_sources

SECTIONS = ('identity', 'preferences', 'sources', 'permissions', 'limits', 'connections')
ACTIONS = ('research', 'register', 'fill', 'apply', 'email_read', 'email_reply', 'email_trash', 'schedule', 'assessment', 'profile_publish')
QUESTIONS = {
    'identity': [('name', 'Qual nome você quer colocar no currículo?', 'Pode escrever seu nome como gostaria que a empresa o visse'), ('email', 'Qual e-mail você quer usar para receber contatos das empresas?', 'Digite apenas o endereço, sem senha')],
    'preferences': [('roles', 'Que tipo de trabalho você procura?', 'Pode dizer o cargo ou descrever o que gostaria de fazer; eu ajudo a encontrar os nomes'), ('modalities', 'Você quer trabalhar de casa, no local da empresa, parte em cada lugar ou não tem preferência?', 'Pode escolher uma dessas opções; eu explico as diferenças se precisar')],
    'sources': [('urls', 'Você já tem sites onde quer procurar vagas ou quer ajuda para encontrar opções?', 'Pode colar os endereços, dizer "me ajude a encontrar sites" ou deixar para depois. Vou verificar as opções antes de sugerir; você escolhe quais usar.')],
    'permissions': [],
    'connections': [('accounts', 'Você quer acompanhar os retornos pelo mesmo e-mail de contato?', 'Pode dizer sim, informar outro e-mail ou deixar para depois. O login será feito por você, sem passar a senha')],
}

ACTION_LABELS = {
    'research': 'Procurar vagas', 'register': 'Criar cadastros em sites de vagas',
    'fill': 'Preencher formulários', 'apply': 'Enviar candidaturas',
    'email_read': 'Ler e-mails sobre vagas', 'email_reply': 'Responder recrutadores',
    'email_trash': 'Mover e-mails de vagas sem utilidade para a lixeira',
    'schedule': 'Confirmar entrevistas', 'assessment': 'Ajudar em testes de seleção',
    'profile_publish': 'Aplicar melhorias no LinkedIn e GitHub',
}
PERMISSION_QUESTIONS = {
    'research': 'Posso procurar vagas para você?',
    'register': 'Posso criar seu cadastro em sites de vagas quando for necessário?',
    'fill': 'Posso preencher os formulários com os dados que você confirmou?',
    'apply': 'Posso enviar candidaturas que respeitem suas preferências?',
    'email_read': 'Posso ler os e-mails relacionados às suas vagas?',
    'email_reply': 'Você quer ajuda para responder aos recrutadores?',
    'email_trash': 'Você quer que eu ajude a tirar da caixa de entrada e-mails de vagas sem utilidade?',
    'schedule': 'Você quer ajuda para marcar entrevistas?',
    'assessment': 'Você quer ajuda em testes quando as regras da seleção permitirem?',
    'profile_publish': 'Você quer ajuda para aplicar as melhorias no LinkedIn ou GitHub?',
}
for action in ACTIONS:
    example = 'Pode fazer, pergunte antes ou nunca'
    if action == 'research': example += '. Se preferir, pode dizer "pergunte antes para tudo"'
    if action == 'email_reply': example = 'Você sempre confere e aprova o texto antes do envio. Pode aceitar a ajuda ou recusar'
    if action == 'email_trash': example = 'Vamos combinar quais mensagens podem ir para a lixeira; nada será apagado de vez. Pode aceitar a ajuda ou recusar'
    if action == 'schedule': example = 'Você sempre confirma o horário antes. Pode aceitar a ajuda ou recusar'
    if action == 'assessment': example = 'Entrevistas e respostas pessoais ficam com você. Pode aceitar a ajuda ou recusar'
    if action == 'profile_publish': example = 'Você sempre confere o texto, a conta e o destino antes de cada publicação. Pode aceitar a ajuda ou recusar'
    QUESTIONS['permissions'].append((action, PERMISSION_QUESTIONS[action], example))

QUESTIONS['preferences'] += [
    ('currencies', 'Em quais moedas você aceita receber?', 'Por exemplo, reais ou euros'),
    ('levels', 'Você quer limitar as vagas a algum nível de experiência?', 'Pode dizer iniciante, pleno, sênior ou sem preferência; eu explico as diferenças se precisar'),
    ('contracts', 'Você tem preferência pelo tipo de contratação?', 'Por exemplo, carteira assinada, prestação de serviço ou sem preferência'),
    ('locations', 'Você procura trabalho no Brasil, em outros países ou nos dois?', 'Diga os lugares que aceita ou sem preferência. Se for internacional, vamos distinguir trabalhar daqui de mudar de país'),
    ('technologies', 'Existe alguma ferramenta que precisa fazer parte do trabalho?', 'Diga quais ou responda que não tem essa exigência'),
    ('languages', 'Quais idiomas você consegue usar no trabalho?', 'Descreva o que consegue ler, escrever ou conversar; eu ajudo a registrar o nível'),
    ('blocked_companies', 'Há empresas em que você não quer trabalhar?', 'Diga os nomes ou responda nenhuma'),
    ('blocked_sectors', 'Há setores em que você não quer trabalhar?', 'Diga quais ou responda nenhum'),
    ('blocked_platforms', 'Há algum site de candidatura que você quer evitar?', 'Diga o nome ou endereço, ou responda nenhum'),
    ('missing', 'Quando faltar uma informação importante na vaga, como quer seguir?', 'Posso perguntar a você, considerar a vaga mesmo assim ou deixá-la de fora'),
]

SALARY_QUESTIONS = [
    ('floors', 'Qual é o menor valor que você aceita receber?', 'Diga o valor, a moeda e se é por mês, ano ou hora. Pode variar por contrato; se ainda não sabe, deixamos esse valor em aberto'),
    ('public_expectation', 'Se a empresa perguntar quanto você quer ganhar, que valor posso informar?', 'Pode ser diferente do seu mínimo. Se preferir combinar o valor antes de cada candidatura, diga isso'),
    ('missing', 'Podemos considerar vagas que não informam o salário?', 'Sim, pergunte a cada caso ou descarte essas vagas'),
    ('estimated', 'E quando o valor foi calculado pelo site, sem confirmação da empresa?', 'Posso confirmar o salário antes, deixar a vaga de fora ou considerar esse valor só para escolher vagas; ele não garante quanto a empresa vai pagar'),
    ('range', 'Se a faixa salarial começar abaixo do seu mínimo e terminar acima, como seguimos?', 'Podemos deixar pendente até confirmar o valor ou descartar. O teto da faixa não é uma oferta garantida'),
]

def pending_questions(section, data):
    """Seleciona campos não respondidos; listas opcionais vazias são respostas.

    Roles e currencies precisam ser não vazias; modalities pode ser vazia.
    Perguntas agrupadas são separadas para não repetir campos já persistidos.
    """
    questions = []
    for field, question, example in QUESTIONS.get(section, []):
        answered = field in data
        if section == 'preferences' and field in ('roles', 'currencies'):
            answered = bool(data.get(field))
        if not answered:
            questions.append({'field': field, 'question': question, 'example': example})
    if section == 'preferences':
        for field, question, example in SALARY_QUESTIONS:
            if field not in data.get('salary', {}):
                questions.append({'field': 'salary.' + field, 'question': question, 'example': example})
    return questions


def validate(section, data, complete=False):
    if section not in SECTIONS:
        raise ValueError('Seção desconhecida.')
    if section == 'preferences':
        validate_preferences(data, complete)
    elif section == 'sources':
        obj(data, ('urls',), ('urls',) if complete else ())
        if 'urls' in data: normalize_sources(data['urls'])
    elif section == 'identity':
        obj(data, ('name', 'email', 'phone', 'location', 'timezone', 'links'), ('name', 'email') if complete else ())
        for key, value in data.items():
            if key != 'links': string(value)
        if 'email' in data and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', data['email']):
            raise ValueError('Informe um e-mail válido.')
        if 'timezone' in data:
            try: ZoneInfo(data['timezone'])
            except (ZoneInfoNotFoundError, ValueError): raise ValueError('Fuso horário IANA inválido.') from None
        if 'links' in data:
            strings(data['links'])
            for url in data['links']:
                parsed = urlsplit(url)
                if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
                    raise ValueError('Link deve ser HTTP/HTTPS, sem credenciais.')
    elif section == 'permissions':
        # Existing profiles keep their approval; the new action defaults to ask.
        obj(data, ACTIONS + ('confirmed',), tuple(a for a in ACTIONS if a != 'profile_publish') if complete else ())
        confirmed = data.get('confirmed', [])
        strings(confirmed)
        if set(confirmed) - set(ACTIONS): raise ValueError('Confirmação de ação desconhecida.')
        for action in ACTIONS:
            mode = data.get(action, 'ask')
            if mode not in ('allow', 'ask', 'deny'): raise ValueError('Permissão inválida.')
            if mode == 'allow' and action not in confirmed:
                raise ValueError('Allow exige consentimento confirmado para ' + action + '.')
    elif section == 'limits':
        obj(data, ('mode', 'browser_tabs'), ('mode',))
        if data['mode'] != 'chat':
            raise ValueError('O Carreira Guiada funciona neste chat. Use mode=chat, sem executor externo.')
        if type(data.get('browser_tabs', 2)) is not int or not 1 <= data.get('browser_tabs', 2) <= 5:
            raise ValueError('Use de uma a cinco abas de trabalho; o padrão é duas.')
    else:
        obj(data, ('accounts',), ('accounts',) if complete else ())
        accounts = data.get('accounts', [])
        if not isinstance(accounts, list): raise ValueError('Accounts deve ser uma lista.')
        aliases = set()
        for account in accounts:
            obj(account, ('provider', 'alias', 'address'), ('provider', 'alias', 'address'))
            for value in account.values(): string(value)
            if account['alias'] in aliases: raise ValueError('Alias duplicado.')
            aliases.add(account['alias'])


class Profile:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()

    @contextmanager
    def _db(self, write=False):
        # Traverse using directory descriptors: every ancestor rejects symlinks.
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        db = None
        dbfd = None
        try:
            for part in self.root.parts[1:]:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
            if write:
                try: os.mkdir('.job', 0o700, dir_fd=fd)
                except FileExistsError: pass
            try: nxt = os.open('.job', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                yield None
                return
            os.close(fd)
            fd = nxt
            if os.fstat(fd).st_mode & 0o077:
                raise ValueError('Diretório .job exige permissões 0700.')
            for suffix in ('', '-journal', '-wal', '-shm'):
                try: info = os.stat('control.sqlite3' + suffix, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError: continue
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
                    raise ValueError('Arquivo de estado inseguro: use arquivo regular privado, sem links.')
            try:
                dbfd = os.open('control.sqlite3', os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if write else 0), 0o600, dir_fd=fd)
            except FileNotFoundError:
                yield None
                return
            # SQLite uses the canonical path; identity is checked again before use.
            path = self.root / '.job' / 'control.sqlite3'
            db = sqlite3.connect(path.as_uri() + ('?mode=rw' if write else '?mode=ro'), uri=True, timeout=10)
            info = os.stat(path, follow_symlinks=False)
            original = os.fstat(dbfd)
            if (info.st_dev, info.st_ino) != (original.st_dev, original.st_ino):
                raise ValueError('Arquivo de estado foi substituído durante a abertura.')
            if write:
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE IF NOT EXISTS job_profile (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, approved_version INTEGER, sections TEXT NOT NULL)')
            yield db
            if write: db.commit()
        except OSError as exc:
            raise ValueError('Não foi possível acessar estado privado sem seguir links: ' + str(exc)) from exc
        finally:
            if db is not None: db.close()
            if dbfd is not None: os.close(dbfd)
            os.close(fd)

    @staticmethod
    def _read(db):
        empty = {'version': 0, 'approved_version': None, 'sections': {}}
        if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='job_profile'").fetchone(): return empty
        row = db.execute('SELECT version, approved_version, sections FROM job_profile WHERE id=1').fetchone()
        return {'version': row[0], 'approved_version': row[1], 'sections': json.loads(row[2])} if row else empty

    def get(self):
        with self._db() as db: return self._read(db)

    def save(self, section: str, data: dict):
        validate(section, data)
        with self._db(True) as db:
            return self._save(db, self._read(db), section, data)

    def _save(self, db, current, section, data):
        data = json.loads(json.dumps(data, allow_nan=False))
        if section == 'sources' and 'urls' in data:
            data['urls'] = normalize_sources(data['urls'])
        if section == 'permissions':
            data.setdefault('confirmed', [])
        if section == 'preferences' and data.get('salary', {}).get('floors') == []:
            data['salary'].setdefault('range', 'ask')
        before = json.dumps(current['sections'], sort_keys=True)
        current['sections'][section] = data
        current['sections'].setdefault('limits', {'mode': 'chat'})
        if current['sections'].get('permissions', {}).get('email_read') == 'deny':
            current['sections'].setdefault('connections', {'accounts': []})
        if json.dumps(current['sections'], sort_keys=True) != before:
            db.execute('INSERT OR REPLACE INTO job_profile VALUES (1, ?, NULL, ?)', (current['version'] + 1, json.dumps(current['sections'], ensure_ascii=False)))
        return self._read(db)

    def answer(self, section, field, value, *, confirmed=False):
        """Merge one translated answer atomically, preserving previous answers."""
        if section not in SECTIONS or not isinstance(field, str) or type(confirmed) is not bool:
            raise ValueError('Resposta inválida. Confira a pergunta atual.')
        with self._db(True) as db:
            current = self._read(db)
            data = json.loads(json.dumps(current['sections'].get(section, {})))
            if section == 'preferences' and field.startswith('salary.') and field.count('.') == 1:
                data.setdefault('salary', {})[field.split('.')[1]] = value
            else:
                data[field] = value
            if section == 'permissions' and field in ACTIONS:
                actions = set(data.get('confirmed', []))
                actions.discard(field)
                if value == 'allow':
                    if not confirmed:
                        raise ValueError('Confirme a autorização da pessoa antes de permitir esta ação.')
                    actions.add(field)
                data['confirmed'] = [action for action in ACTIONS if action in actions]
            validate(section, data)
            return self._save(db, current, section, data)

    @staticmethod
    def _missing(sections):
        missing = []
        for section in SECTIONS:
            try:
                if section not in sections: raise ValueError('Ausente')
                validate(section, sections[section], True)
            except ValueError: missing.append(section)
        return missing

    def status(self):
        current = self.get()
        missing = self._missing(current['sections'])
        next_section = missing[0] if missing else None
        return {'next_section': next_section, 'missing': missing, 'approved': not missing and current['approved_version'] == current['version'], 'version': current['version'], 'questions': pending_questions(next_section, current['sections'].get(next_section, {}))}

    def approve(self, version: int):
        if type(version) is not int or version < 1: raise ValueError('Versão deve ser inteiro positivo.')
        with self._db(True) as db:
            current = self._read(db)
            if version != current['version']: raise ValueError('A versão mudou; revise o perfil atual.')
            if self._missing(current['sections']): raise ValueError('Complete as etapas antes de aprovar.')
            db.execute('UPDATE job_profile SET approved_version=? WHERE id=1', (version,))
            return self._read(db)
