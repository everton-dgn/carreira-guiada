"""Execute novice conversations through the CLI, without accounts or external AI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='job-journey-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.turns = []

    def tearDown(self):
        destination = os.environ.get('JOB_JOURNEY_REPORT')
        if not destination:
            return
        target = Path(destination) / self._testMethodName
        target.mkdir(parents=True, exist_ok=False)
        (target / 'dialogue.json').write_text(json.dumps(self.turns, ensure_ascii=False, indent=2))
        lines = ['# Simulação com dados fictícios', '',
                 'As perguntas de estado e as gravações passaram pela CLI real. As respostas e interpretações foram preparadas para representar uma pessoa leiga. Nenhuma conta real foi aberta.', '']
        for index, turn in enumerate(self.turns, 1):
            lines.extend([f'## Etapa {index}', '', 'IA: ' + turn['ia'], '', 'Pessoa: ' + turn['pessoa'], ''])
        (target / 'dialogue.md').write_text('\n'.join(lines))
        resumes = self.root / '.job/resumes'
        if resumes.exists():
            shutil.copytree(resumes, target / 'curriculos-ficticios')

    def call(self, *args, data=None, success=True):
        result = subprocess.run([sys.executable, '-m', 'scripts.job.cli', '--root', str(self.root), *args, '--json'],
                                input=json.dumps(data) if data is not None else None,
                                capture_output=True, text=True, cwd=PROJECT, timeout=15)
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def reply(self, words, section, field, value, confirmed=False):
        state = self.call('start')
        self.assertEqual(state['question']['field'], field)
        self.assertEqual(state['next_step'], section)
        self.turns.append({'ia': state['message'], 'pessoa': words})
        self.call('profile', 'answer', section, data={'field': field, 'value': value, 'confirmed': confirmed})

    def preferences_and_permissions(self, *, skip_email=False, first_job=True, ask_all=False, email_account=False, known_salary=False):
        answers = [
            ('roles', 'Quero trabalhar como atendente.', ['Atendente']),
            ('modalities', 'Pode ser presencial.', ['presencial']),
            ('currencies', 'Em reais.', ['BRL']),
            ('levels', 'Quero vagas para quem está começando.' if first_job else 'Não tenho preferência pelo nome do nível.', ['Júnior', 'Entrada'] if first_job else []),
            ('contracts', 'Quero carteira assinada.', ['CLT']),
            ('locations', 'Só na Cidade Exemplo.', ['Cidade Exemplo']),
            ('technologies', 'Não tenho preferência por ferramenta.', []),
            ('languages', 'Só português, minha língua nativa.', [{'name': 'Português', 'level': 6, 'required': False}]),
            ('blocked_companies', 'Nenhuma.', []),
            ('blocked_sectors', 'Nenhum.', []),
            ('blocked_platforms', 'Não conheço esses sites. Pode usar os que você conferir.', []),
            ('missing', 'Se faltar informação, me pergunte.', 'ask'),
            ('salary.floors', 'O menor valor é 3.500 reais por mês, com carteira assinada.' if known_salary else 'Ainda não sei quanto pedir. Deixa sem valor mínimo.', [{'contract': 'CLT', 'currency': 'BRL', 'period': 'month', 'amount': 3500}] if known_salary else []),
            ('salary.public_expectation', 'Pode informar 4.200 reais por mês.' if known_salary else 'Prefiro combinar o valor antes de cada candidatura.', {'currency': 'BRL', 'period': 'month', 'amount': 4200} if known_salary else None),
            ('salary.missing', 'Pode considerar vagas sem salário informado.', 'accept'),
            ('salary.estimated', 'Se for só uma estimativa, confirme antes.', 'ask'),
            ('salary.range', 'Se acontecer, confirme o valor antes.', 'ask'),
        ]
        for field, words, value in answers:
            status = self.call('profile', 'status')
            # Facts already confirmed during the CV conversation are reused.
            if field not in [q['field'] for q in status['questions']]:
                continue
            if field == 'levels' and first_job:
                self.turns.append({'ia': self.call('start')['message'], 'pessoa': 'Não entendo esses níveis. É meu primeiro emprego.'})
                self.turns.append({'ia': 'Os níveis indicam a experiência esperada. Podemos procurar vagas de entrada ou júnior e conferir quais aceitam quem nunca trabalhou. Quer seguir assim?', 'pessoa': 'Isso, pode ser.'})
                self.call('profile', 'answer', 'preferences', data={'field': field, 'value': value})
                continue
            self.reply(words, 'preferences', field, value)
        self.reply('Copiei este endereço do navegador: https://jobs.example.org/', 'sources', 'urls', ['https://jobs.example.org/'])
        from scripts.job.profile import ACTIONS
        if ask_all:
            self.turns.append({'ia': self.call('start')['message'], 'pessoa': 'Prefiro que você me pergunte antes de tudo.'})
            self.call('profile', 'save', 'permissions', data={action: 'ask' for action in ACTIONS})
        # Publishing profiles is optional and gets its own consent when requested.
        for action in (() if ask_all else tuple(a for a in ACTIONS if a != 'profile_publish')):
            value = 'allow' if action in ('research', 'fill') else 'ask'
            words = 'Pode fazer.' if value == 'allow' else 'Me pergunte antes.'
            if action == 'email_read' and skip_email:
                value, words = 'deny', 'Não quero conectar meu e-mail agora.'
            self.reply(words, 'permissions', action, value, confirmed=value == 'allow')
        if not ask_all:
            self.assertNotIn('profile_publish', self.call('profile', 'show')['sections']['permissions'])
        if not skip_email:
            if email_account:
                self.reply('Sim, o mesmo e-mail. Eu uso Gmail.', 'connections', 'accounts', [{'provider': 'gmail', 'alias': 'principal', 'address': 'marina@example.invalid'}])
            else:
                self.reply('Deixa o e-mail para depois.', 'connections', 'accounts', [])
        self.assertEqual(self.call('start')['next_step'], 'profile_approval')
        permissions = 'Todas as ações dependem da sua confirmação.' if ask_all else 'Posso pesquisar e preencher, mas envio e demais ações dependem de você.'
        mail = 'Você escolheu acompanhar o mesmo e-mail pelo Gmail; o login ainda precisa ser conferido.' if email_account else 'O e-mail ficou para depois.'
        salary = 'Seu mínimo privado é R$ 3.500 por mês; para empresas, você autorizou informar R$ 4.200. Faixas que não garantirem o mínimo precisam de confirmação.' if known_salary else 'Ainda não definiu um mínimo salarial.'
        self.turns.append({'ia': 'Você procura atendimento presencial na Cidade Exemplo, com carteira assinada. ' + salary + ' Vagas sem salário podem entrar. ' + permissions + ' ' + mail + ' Está correto?', 'pessoa': 'Sim.'})
        version = self.call('profile', 'show')['version']
        self.call('profile', 'approve', '--version', str(version))

    def finish_resume(self, markdown, fact_ids):
        self.assertEqual(self.call('start')['next_step'], 'resume_approval')
        draft = self.call('resume', 'draft', data={'label': 'Geral', 'markdown': markdown, 'fact_ids': fact_ids})
        self.turns.append({'ia': 'Preparei este rascunho para você conferir:\n\n' + markdown + '\n\nQuer corrigir alguma coisa?', 'pessoa': 'Está certo. Pode aprovar.'})
        self.call('resume', 'approve', draft['id'])
        self.assertTrue(self.call('resume', 'check', draft['id'])['passed'])
        self.assertEqual(self.call('start')['next_step'], 'professional_presence')
        self.turns.append({'ia': 'Quer revisar também o LinkedIn ou GitHub?', 'pessoa': 'Deixa para depois, quero procurar vagas.'})
        self.call('presence', 'choose', data={'decision': 'later', 'topics': [], 'confirmation': 'Deixa para depois, quero procurar vagas.'})
        self.call('practice', 'choose', data={'decision': 'later'})
        state = self.call('start')
        self.assertEqual(state['next_step'], 'execution_readiness')
        self.assertFalse(state['automatic_execution_started'])
        result = self.call('resume', 'show', draft['id'])
        self.assertEqual(set(result['paths']), {'pdf', 'docx', 'md'})
        for path in result['paths'].values():
            self.assertTrue((self.root / path).is_file())
        self.turns.append({'ia': state['message'], 'pessoa': 'Certo. Depois continuamos.'})
        self.assertFalse(self.call('status')['capabilities'])
        self.assertEqual({check['id'] for check in self.call('doctor')['checks']}, {'python', 'uv'})
        return result

    def test_first_job_with_typo_skips_and_restart(self):
        self.turns.append({'ia': self.call('start')['message'], 'pessoa': 'Não tenho currículo e nunca trabalhei. Você faz comigo?'})
        self.call('intake', 'choose', data={'mode': 'create'})
        self.call('intake', 'answer', data={'field': 'experience', 'text': 'Busca do primeiro emprego, sem experiência profissional anterior.'})
        self.reply('Marina Exemplo.', 'identity', 'name', 'Marina Exemplo')
        before = self.call('profile', 'show')
        self.turns.append({'ia': self.call('start')['message'], 'pessoa': 'marina sem arroba'})
        error = self.call('profile', 'answer', 'identity', data={'field': 'email', 'value': 'marina sem arroba'}, success=False)
        self.assertIn('e-mail', error['error'])
        self.assertEqual(before, self.call('profile', 'show'))
        self.turns.append({'ia': 'Esse endereço parece incompleto. Pode conferir se tem @? Seu nome já está salvo.', 'pessoa': 'Ah, entendi.'})
        self.reply('marina@example.invalid', 'identity', 'email', 'marina@example.invalid')
        answers = [
            ('education', 'Terminei o ensino médio em 2024 na Escola Exemplo.', 'Ensino médio concluído em 2024 na Escola Exemplo.'),
            ('skills', 'Não sei o que colocar nisso. Podemos pular?', None),
            ('languages', 'Só português, minha língua nativa.', 'Português nativo.'),
            ('extra', 'Por enquanto é isso.', None),
        ]
        for field, words, value in answers:
            state = self.call('start')
            self.assertEqual(state['next_step'], 'curriculum_intake')
            self.assertEqual(state['question']['field'], field)
            self.turns.append({'ia': state['message'], 'pessoa': words})
            self.call('intake', 'answer', data={'field': field, 'text': value})
            if field == 'skills':
                self.call('stop')
                self.assertTrue(self.call('status')['control']['stopped'])
                self.turns.append({'ia': 'Suas respostas ficaram salvas. Podemos continuar depois.', 'pessoa': 'Voltei. Continuar.'})
                self.call('resume-work')
                self.assertEqual(self.call('start')['question']['field'], 'languages')
            if field == 'languages':
                self.call('profile', 'answer', 'preferences', data={'field': 'languages', 'value': [{'name': 'Português', 'level': 6, 'required': False}]})
        self.preferences_and_permissions()
        intake = self.call('intake', 'status')
        markdown = '# Marina Exemplo\n\nmarina@example.invalid\n\n## Objetivo\n\nPrimeiro emprego em atendimento.\n\n## Formação\n\nEnsino médio concluído em 2024 na Escola Exemplo.\n\n## Idiomas\n\nPortuguês nativo.'
        self.finish_resume(markdown, intake['fact_ids'])
        saved = self.call('intake', 'show')['answers']
        self.assertIsNone(saved['skills']['text'])
        self.assertEqual(len(self.call('resume', 'facts')), 3)

    def test_pasted_curriculum_can_continue_without_creating_a_public_file(self):
        self.call('intake', 'choose', data={'mode': 'import'})
        self.call('profile', 'answer', 'identity', data={'field': 'name', 'value': 'Pessoa Exemplo'})
        self.call('profile', 'answer', 'identity', data={'field': 'email', 'value': 'pessoa@example.invalid'})
        self.assertEqual(self.call('start')['next_step'], 'curriculum_input')
        self.call('intake', 'choose', data={'mode': 'create'})
        self.call('intake', 'answer', data={'field': 'education', 'text': 'Curso fictício de atendimento.'})
        self.assertEqual(self.call('start')['question']['field'], 'experience')
        self.assertEqual(len(self.call('resume', 'facts')), 1)
        self.assertEqual({path.name for path in self.root.iterdir()}, {'.job'})

    def test_existing_cv_correction_and_no_email_connection(self):
        from docx import Document
        source = self.root / 'curriculo.docx'
        document = Document()
        document.add_heading('Marina Exemplo', 0)
        document.add_paragraph('marina@example.invalid')
        document.add_paragraph('Atendimento na Loja Exemplo, de 2021 a 2023.')
        document.save(source)
        original = source.read_bytes()
        self.turns.append({'ia': self.call('start')['message'], 'pessoa': 'Já tenho. Anexei o Word.'})
        self.call('intake', 'choose', data={'mode': 'import'})
        imported = self.call('resume', 'import', data={'file': str(source), 'label': 'Geral'})
        self.assertIn('2021', imported['text'])
        self.turns.append({'ia': 'Li Marina Exemplo, o e-mail e atendimento na Loja Exemplo de 2021 a 2023. Esses dados estão certos?', 'pessoa': 'O nome e o e-mail estão certos, mas comecei na loja em 2020.'})
        self.call('profile', 'answer', 'identity', data={'field': 'name', 'value': 'Marina Exemplo'})
        self.call('profile', 'answer', 'identity', data={'field': 'email', 'value': 'marina@example.invalid'})
        fact = self.call('resume', 'fact', data={'text': 'Atendimento na Loja Exemplo, de 2020 a 2023.', 'source': 'candidate:correcao-da-data', 'confirmed': True})
        self.assertEqual(self.call('start')['next_step'], 'preferences')
        self.preferences_and_permissions(skip_email=True, first_job=False, known_salary=True)
        salary = self.call('profile', 'show')['sections']['preferences']['salary']
        self.assertEqual(salary['floors'][0]['amount'], 3500)
        self.assertEqual(salary['public_expectation']['amount'], 4200)
        self.finish_resume('# Marina Exemplo\n\nmarina@example.invalid\n\n## Experiência\n\nAtendimento na Loja Exemplo, de 2020 a 2023.', [fact['id']])
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual((self.root / imported['original_path']).read_bytes(), original)

    def test_unreadable_file_minimal_cv_and_email_login_pending(self):
        from datetime import datetime, timezone
        broken = self.root / 'curriculo.pdf'
        broken.write_bytes(b'arquivo ficticio ilegivel')
        self.turns.append({'ia': self.call('start')['message'], 'pessoa': 'Tenho este PDF, mas não sei se ele abre.'})
        self.call('intake', 'choose', data={'mode': 'import'})
        error = self.call('resume', 'import', '--file', str(broken), '--label', 'Geral', success=False)
        self.assertIn('outra cópia', error['error'])
        self.assertEqual(broken.read_bytes(), b'arquivo ficticio ilegivel')
        self.assertFalse(self.call('resume', 'sources'))
        self.turns.append({'ia': 'Não consegui ler esse arquivo. Você pode anexar outra cópia, colar o texto ou criar o currículo comigo.', 'pessoa': 'Vamos criar. Por enquanto só quero colocar meu contato e o trabalho que procuro.'})
        self.call('intake', 'choose', data={'mode': 'create'})
        self.reply('Marina Exemplo', 'identity', 'name', 'Marina Exemplo')
        self.reply('marina@example.invalid', 'identity', 'email', 'marina@example.invalid')
        for field in ('education', 'experience', 'skills', 'languages', 'extra'):
            self.assertEqual(self.call('start')['question']['field'], field)
            self.call('intake', 'answer', data={'field': field, 'text': None})
        self.turns.append({'ia': 'Salvei sua escolha de deixar esses tópicos para depois. Vamos combinar o trabalho que você procura.', 'pessoa': 'Certo.'})
        self.preferences_and_permissions(ask_all=True, email_account=True)
        self.assertEqual(self.call('intake', 'status')['fact_ids'], [])
        objective = self.call('resume', 'fact', data={'text': 'Objetivo profissional confirmado: trabalhar em atendimento.', 'source': 'candidate:objetivo-confirmado', 'confirmed': True})
        self.finish_resume('# Marina Exemplo\n\nmarina@example.invalid\n\n## Objetivo\n\nTrabalhar em atendimento.', [objective['id']])
        self.call('capability', data={'kind': 'mail', 'provider': 'gmail', 'account': 'principal', 'status': 'auth_required', 'checked_at': datetime.now(timezone.utc).isoformat(), 'evidence': 'Cenário fictício: conexão exige login; nenhuma conta real foi aberta'})
        report = self.call('doctor')
        self.assertFalse(report['ready']['effects'])
        self.assertFalse(report['sessions'][0]['usable'])
        self.turns.append({'ia': 'O currículo e o perfil estão salvos. O acesso ao e-mail ficou pendente de login. Você faz o login diretamente no aplicativo; nunca precisa me passar a senha.', 'pessoa': 'Deixo o login para depois.'})


if __name__ == '__main__':
    unittest.main()
