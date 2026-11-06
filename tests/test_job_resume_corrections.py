"""Practice answer filter, blocked resume imports and fact corrections, synthetic data only."""
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.job import cli
from scripts.job.intake import Intake
from scripts.job.practice import Practice
from scripts.job.profile import Profile
from scripts.job.resumes import ResumeManager

CV = "# Pessoa Exemplo\n\n## Experiência\n\nAtendimento em loja fictícia.\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manager = ResumeManager(self.root)


class PracticeAnswerFilterTests(Base):
    def start(self):
        s = Practice(self.root).start('system_design', 'coach', short=True)
        return Practice(self.root), s['session_id'], s['question']['id']

    def test_conceptual_explanations_are_saved(self):
        p, sid, q = self.start()
        for text in ('Usaria token: JWT de curta duração com renovação.',
                     'cookie: HttpOnly e SameSite para a sessão.',
                     'senha: hash bcrypt com salt.',
                     'chave de API: rotacionada a cada 90 dias.',
                     'token: opaco, de vida curta.',
                     'A senha fica com hash lento, nunca em texto puro.',
                     'O access token: opaco e de vida curta, guardado no servidor.',
                     'Uso Node.js. O token: JWT assinado com chave do servidor.'):
            status = p.answer(sid, q, text)
            self.assertEqual(status['question']['attempt']['text'], text)

    def test_real_looking_credentials_and_documents_are_refused_without_echo(self):
        p, sid, q = self.start()
        jwt = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJleGVtcGxvIn0.ZmljdGljaW8'
        samples = ['senha: segredo', 'password=hunter2', 'Senha = minhaSenha', 'token=' + jwt,
                   'api_key: sk-exemplo123FICTICIO456', 'token: "valor-literal"', 'token: abc12345xyz',
                   'chave ' + 'AKIA' + 'A' * 16 + ' no código', 'Authorization: Bearer exemploFicticio1234567890',
                   'CPF 000.000.000-00', 'cpf: 00000000000', 'RG: 12.345.678-9', 'meu rg 1234567',
                   'https://pessoa:segredo@exemplo.invalid/api',
                   # Literal assignments are refused even when short or without digits.
                   'token=example', 'api_key=abcdef', 'O token=opaco é trocado no gateway.', 'token: example',
                   'token: abc com contexto', 'token: abcdefghijklmnop usado em produção',
                   'token: opaco com abc12345', 'token: JWT de exemplo abc12345',
                   'senha: hash bcrypt com abc12345',
                   'cookie: abc def', 'secret: abcdef.', 'token: abc. Depois explico o resto do fluxo',
                   'token: abcdef, de exemplo', 'token:', 'client_secret = de para com']
        for text in samples:
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as error:
                    p.answer(sid, q, text)
                message = str(error.exception)
                self.assertIn('pode errar', message)
                for part in ('segredo', 'hunter2', jwt, 'sk-exemplo', '000.000.000-00', '12.345.678-9'):
                    self.assertNotIn(part, message)
        self.assertIsNone(p.status(sid)['question']['attempt'])

    def test_resume_text_filter_is_not_relaxed(self):
        with self.assertRaisesRegex(ValueError, 'senhas'):
            self.manager.add_fact('token: JWT de curta duração', 'candidate:exemplo', True)


class BlockedImportTests(Base):
    def test_blocked_file_is_not_copied_and_previous_answers_survive(self):
        profile = Profile(self.root)
        profile.save('identity', {'name': 'Pessoa Exemplo', 'email': 'pessoa@exemplo.invalid'})
        profile.save('sources', {'urls': ['https://vagas.exemplo.invalid/busca']})
        Intake(self.root).choose('import')
        clean = self.root / 'limpo.txt'
        clean.write_text('Pessoa Exemplo\nAtendimento em loja fictícia.\n')
        self.manager.import_file(clean, 'Geral')
        db_path = self.root / '.job/control.sqlite3'
        before = (db_path.read_bytes(), profile.get(), self.manager.sources(), Intake(self.root).get(),
                  sorted(p.name for p in (self.root / '.job/sources').iterdir()))
        for content in ('Pessoa Exemplo\nCPF: 000.000.000-00\nAtendimento.\n',
                        'Pessoa Exemplo\nRG=12.345.678-9\nAtendimento.\n',
                        'Pessoa Exemplo\nsenha: exemplo-ficticio\n',
                        'Pessoa Exemplo\nCPF 000.000.000-00\n',
                        'Pessoa Exemplo\nRG 12.345.678-9\n',
                        'Pessoa Exemplo\nDocumento 000.000.000-00\n'):
            with self.subTest(content=content):
                blocked = self.root / 'bloqueado.txt'
                blocked.write_text(content)
                with self.assertRaises(ValueError) as error:
                    self.manager.import_file(blocked, 'Geral')
                message = str(error.exception)
                for expected in ('cópia', 'original', 'cole o texto', 'respostas anteriores'):
                    self.assertIn(expected, message)
                for leaked in ('000.000.000-00', '12.345.678-9', 'exemplo-ficticio'):
                    self.assertNotIn(leaked, message)
                self.assertEqual(blocked.read_text(), content)
                after = (db_path.read_bytes(), profile.get(), self.manager.sources(), Intake(self.root).get(),
                         sorted(p.name for p in (self.root / '.job/sources').iterdir()))
                self.assertEqual(after, before)

    def test_unreadable_text_keeps_its_own_message(self):
        empty = self.root / 'vazio.txt'
        empty.write_text('   ')
        with self.assertRaisesRegex(ValueError, 'Informe o texto extraído'):
            self.manager.import_file(empty, 'Geral')
        self.assertFalse((self.root / '.job').exists())


class FactCorrectionTests(Base):
    def test_approval_holds_write_lock_while_checking_fact_status(self):
        fact = self.manager.add_fact('Atendimento em loja fictícia.', 'candidate:exemplo', True)
        draft = self.manager.draft('Geral', CV, [fact['id']])
        original = self.manager._revocation

        def check_locked(db, fact_id):
            self.assertTrue(db.in_transaction)
            with closing(sqlite3.connect(self.manager.db_path, timeout=0)) as competing:
                with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                    competing.execute('BEGIN IMMEDIATE')
            return original(db, fact_id)

        with mock.patch.object(self.manager, '_revocation', side_effect=check_locked):
            self.assertEqual(self.manager.approve(draft['id'])['status'], 'approved')
        self.manager.revoke_fact(fact['id'], 'candidate:retirada', True)
        self.assertEqual(self.manager.get(draft['id'])['status'], 'retired')
        with self.assertRaises(ValueError):
            self.manager.approve(draft['id'])

    def setUp(self):
        super().setUp()
        self.old = self.manager.add_fact('Atendimento de 2019 a 2021.', 'candidate:resposta-1', True)['id']
        self.other = self.manager.add_fact('Curso fictício concluído.', 'candidate:resposta-2', True)['id']
        self.approved = self.manager.approve(self.manager.draft('Atendimento', CV, [self.old, self.other])['id'])
        self.draft = self.manager.draft('Vendas', CV, [self.old])
        self.unrelated = self.manager.approve(self.manager.draft('Curso', CV, [self.other])['id'])

    def files(self, version):
        return {fmt: (self.root / path).read_bytes() for fmt, path in version['paths'].items()}

    def status(self, version):
        return next(v for v in self.manager.list() if v['id'] == version['id'])['status']

    def test_revoke_retires_every_dependent_version_and_keeps_history(self):
        files = self.files(self.approved)
        result = self.manager.revoke_fact(self.old, 'candidate:resposta-3', True, 'Data incorreta')
        self.assertEqual(result['kind'], 'revoked')
        self.assertFalse(result['duplicate'])
        self.assertEqual(sorted(result['retired_versions']), sorted([self.approved['id'], self.draft['id']]))
        self.assertEqual(self.status(self.approved), 'retired')
        self.assertEqual(self.status(self.draft), 'retired')
        self.assertEqual(self.status(self.unrelated), 'approved')
        self.assertEqual(self.files(self.approved), files)
        self.assertEqual(self.manager.get(self.approved['id'])['approved_at'], self.approved['approved_at'])
        fact = next(f for f in self.manager.facts() if f['id'] == self.old)
        self.assertEqual((fact['text'], fact['status'], fact['replaced_by']), ('Atendimento de 2019 a 2021.', 'revoked', None))
        for version in (self.approved, self.draft):
            with self.assertRaisesRegex(ValueError, 'retirado ou substituído'):
                self.manager.approve(version['id'])
        with self.assertRaisesRegex(ValueError, 'retirado ou substituído'):
            self.manager.draft('Nova', CV, [self.old])
        self.manager.draft('Nova', CV, [self.other])

    def test_replace_creates_confirmed_fact_and_only_it_can_be_used(self):
        result = self.manager.replace_fact(self.old, 'Atendimento de 2018 a 2021.', 'candidate:resposta-3', True)
        new = result['replacement']
        self.assertEqual((new['text'], new['confirmed'], new['status']), ('Atendimento de 2018 a 2021.', 1, 'active'))
        self.assertEqual((result['fact']['status'], result['fact']['replaced_by']), ('replaced', new['id']))
        self.assertEqual(sorted(result['retired_versions']), sorted([self.approved['id'], self.draft['id']]))
        with self.assertRaisesRegex(ValueError, 'retirado ou substituído'):
            self.manager.draft('Nova', CV, [self.old])
        version = self.manager.approve(self.manager.draft('Nova', CV, [new['id'], self.other])['id'])
        self.assertEqual(version['status'], 'approved')
        with self.assertRaisesRegex(ValueError, 'retirado ou substituído'):
            self.manager.approve(self.approved['id'])

    def test_repetition_is_idempotent_and_conflicts_are_refused(self):
        first = self.manager.revoke_fact(self.old, 'candidate:resposta-3', True)
        again = self.manager.revoke_fact(self.old, 'candidate:resposta-3', True)
        self.assertTrue(again['duplicate'])
        self.assertEqual(again['retired_versions'], first['retired_versions'])
        with self.assertRaisesRegex(ValueError, 'retirado'):
            self.manager.replace_fact(self.old, 'Outro texto.', 'candidate:resposta-4', True)
        replaced = self.manager.replace_fact(self.other, 'Curso fictício concluído em 2020.', 'candidate:resposta-5', True)
        repeated = self.manager.replace_fact(self.other, 'Curso fictício concluído em 2020.', 'candidate:resposta-5', True)
        self.assertTrue(repeated['duplicate'])
        self.assertEqual(repeated['replacement']['id'], replaced['replacement']['id'])
        self.assertEqual(sum(1 for f in self.manager.facts() if f['text'] == 'Curso fictício concluído em 2020.'), 1)
        with self.assertRaisesRegex(ValueError, 'já foi substituído'):
            self.manager.replace_fact(self.other, 'Texto diferente.', 'candidate:resposta-6', True)
        with self.assertRaisesRegex(ValueError, 'já foi substituído'):
            self.manager.revoke_fact(self.other, 'candidate:resposta-6', True)

    def test_repetition_reports_the_real_state_of_the_replacement_chain(self):
        b = self.manager.replace_fact(self.old, 'Atendimento de 2018 a 2021.', 'candidate:resposta-3', True)['replacement']['id']
        c = self.manager.replace_fact(b, 'Atendimento de 2018 a 2022.', 'candidate:resposta-4', True)['replacement']['id']
        again = self.manager.replace_fact(self.old, 'Atendimento de 2018 a 2021.', 'candidate:resposta-3', True)
        self.assertTrue(again['duplicate'])
        self.assertEqual((again['replacement']['id'], again['replacement']['status'], again['replacement']['replaced_by']), (b, 'replaced', c))
        self.assertEqual(again['current_fact_id'], c)
        with self.assertRaisesRegex(ValueError, 'fato atual: ' + c):
            self.manager.replace_fact(self.old, 'Outro texto.', 'candidate:resposta-5', True)
        with self.assertRaisesRegex(ValueError, 'fato atual: ' + c):
            self.manager.revoke_fact(b, 'candidate:resposta-5', True)
        self.manager.revoke_fact(c, 'candidate:resposta-5', True)
        final = self.manager.replace_fact(b, 'Atendimento de 2018 a 2022.', 'candidate:resposta-4', True)
        self.assertEqual((final['replacement']['status'], final['current_fact_id']), ('revoked', None))
        first = self.manager.replace_fact(self.old, 'Atendimento de 2018 a 2021.', 'candidate:resposta-3', True)
        self.assertEqual((first['replacement']['status'], first['current_fact_id']), ('replaced', None))
        with self.assertRaisesRegex(ValueError, 'versão mais recente foi retirada'):
            self.manager.revoke_fact(self.old, 'candidate:resposta-6', True)
        statuses = {f['id']: f['status'] for f in self.manager.facts()}
        self.assertEqual((statuses[self.old], statuses[b], statuses[c]), ('replaced', 'replaced', 'revoked'))

    def test_invalid_inputs_change_nothing(self):
        db_path = self.root / '.job/control.sqlite3'
        before = db_path.read_bytes()
        cases = [
            (self.manager.revoke_fact, (self.old, 'candidate:r', False), 'confirmação explícita'),
            (self.manager.revoke_fact, (self.old, 'candidate:r', None), 'confirmação explícita'),
            (self.manager.revoke_fact, (self.old, 'candidate:r', 'true'), 'confirmação explícita'),
            (self.manager.revoke_fact, (self.old, None, True), 'origem'),
            (self.manager.revoke_fact, (self.old, 'arquivo-qualquer', True), 'resposta da pessoa'),
            (self.manager.revoke_fact, ('0' * 32, 'candidate:r', True), 'não encontrado'),
            (self.manager.revoke_fact, ('../x', 'candidate:r', True), 'identificador'),
            (self.manager.revoke_fact, (None, 'candidate:r', True), 'identificador'),
            (self.manager.replace_fact, (self.old, 'Novo texto.', 'fonte-inexistente', True), 'Vincule'),
            (self.manager.replace_fact, (self.old, 'token=exemplo', 'candidate:r', True), 'senhas'),
            (self.manager.replace_fact, (self.old, '', 'candidate:r', True), 'fato corrigido'),
            (self.manager.replace_fact, (self.old, 'Atendimento de 2019 a 2021.', 'candidate:r', True), 'igual ao atual'),
            (self.manager.replace_fact, (self.old, 'Novo texto.', 'candidate:r', False), 'confirmação explícita'),
        ]
        for method, args, message in cases:
            with self.subTest(args=args):
                with self.assertRaisesRegex(ValueError, message):
                    method(*args)
        self.assertEqual(db_path.read_bytes(), before)

    def test_failure_inside_operation_rolls_back_everything(self):
        facts_before, versions_before = self.manager.facts(), self.manager.list()
        with mock.patch.object(ResumeManager, '_open_authorizations', side_effect=sqlite3.OperationalError('falha simulada')):
            with self.assertRaises(sqlite3.OperationalError):
                self.manager.replace_fact(self.old, 'Atendimento de 2018 a 2021.', 'candidate:resposta-3', True)
        self.assertEqual(self.manager.facts(), facts_before)
        self.assertEqual(self.manager.list(), versions_before)

    def test_open_authorization_is_reported_and_preserved(self):
        with closing(sqlite3.connect(self.root / '.job/control.sqlite3')) as db, db:
            db.execute('CREATE TABLE wf_actions (id TEXT PRIMARY KEY, action TEXT, status TEXT, resume_id TEXT)')
            db.executemany('INSERT INTO wf_actions VALUES (?,?,?,?)', [
                ('act_aberta', 'apply', 'authorized', self.approved['id']),
                ('act_incerta', 'apply', 'uncertain', self.approved['id']),
                ('act_feita', 'apply', 'confirmed', self.approved['id']),
                ('act_outra', 'apply', 'authorized', self.unrelated['id'])])
        result = self.manager.revoke_fact(self.old, 'candidate:resposta-3', True)
        self.assertEqual([a['id'] for a in result['open_authorizations']], ['act_aberta', 'act_incerta'])
        with closing(sqlite3.connect(self.root / '.job/control.sqlite3')) as db, db:
            rows = db.execute('SELECT id, status FROM wf_actions ORDER BY id').fetchall()
        self.assertEqual(rows, [('act_aberta', 'authorized'), ('act_feita', 'confirmed'),
                                ('act_incerta', 'uncertain'), ('act_outra', 'authorized')])

    def test_existing_database_without_new_table_keeps_working(self):
        with closing(sqlite3.connect(self.root / '.job/control.sqlite3')) as db, db:
            db.execute('DROP TABLE resume_fact_revocations')
        self.assertEqual({f['status'] for f in self.manager.facts()}, {'active'})
        self.assertEqual(self.manager.get(self.approved['id'])['status'], 'approved')
        self.manager.revoke_fact(self.old, 'candidate:resposta-3', True)
        self.assertEqual(self.status(self.approved), 'retired')


class IntakeConsistencyTests(Base):
    def setUp(self):
        super().setUp()
        self.intake = Intake(self.root)
        self.intake.choose('create')
        self.intake.answer('education', 'Ensino médio fictício concluído em 2020.')
        self.intake.answer('experience', 'Primeiro emprego.')
        self.fact = self.intake.get()['answers']['education']['fact_id']

    def test_replace_points_intake_to_the_new_fact(self):
        result = self.manager.replace_fact(self.fact, 'Ensino médio fictício concluído em 2021.', 'candidate:resposta-3', True)
        answer = self.intake.get()['answers']['education']
        self.assertEqual(answer, {'text': 'Ensino médio fictício concluído em 2021.', 'fact_id': result['replacement']['id']})
        self.assertNotIn(self.fact, self.intake.status()['fact_ids'])

    def test_revoke_removes_the_answer_so_the_question_returns(self):
        self.manager.revoke_fact(self.fact, 'candidate:resposta-3', True)
        state = self.intake.get()
        self.assertNotIn('education', state['answers'])
        self.assertIn('experience', state['answers'])
        status = self.intake.status()
        self.assertEqual(status['question']['field'], 'education')
        self.assertNotIn(self.fact, status['fact_ids'])


class CliCorrectionTests(Base):
    def call(self, action, data):
        out = io.StringIO()
        with mock.patch('sys.stdin', io.StringIO(json.dumps(data))), redirect_stdout(out):
            code = cli.main(['resume', action, '--root', str(self.root), '--json'])
        return code, json.loads(out.getvalue())

    def test_replace_and_revoke_by_cli(self):
        fact = self.manager.add_fact('Atendimento de 2019 a 2021.', 'candidate:resposta-1', True)['id']
        code, result = self.call('fact-replace', {'fact_id': fact, 'text': 'Atendimento de 2018 a 2021.',
                                                  'source': 'candidate:resposta-2', 'confirmed': True, 'reason': 'Data'})
        self.assertEqual((code, result['kind']), (0, 'replaced'))
        new = result['replacement']['id']
        code, result = self.call('fact-revoke', {'fact_id': new, 'source': 'candidate:resposta-3', 'confirmed': True})
        self.assertEqual((code, result['kind'], result['duplicate']), (0, 'revoked', False))
        code, result = self.call('fact-revoke', {'fact_id': new, 'source': 'candidate:resposta-3', 'confirmed': True, 'extra': 1})
        self.assertEqual(code, 1)
        self.assertIn('somente', result['error'])
        code, result = self.call('fact-replace', {'fact_id': fact, 'text': 'x', 'source': 'candidate:r'})
        self.assertEqual(code, 1)
        self.assertIn('confirmação explícita', result['error'])


if __name__ == '__main__':
    unittest.main()
