"""Scripted novice journeys through the real CLI and entirely local fake services."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_job_workflow as support
from scripts.job.profile import Profile

PROJECT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


class FakeServices:
    """No network, browser or mail client. Receipts exist only in this object."""
    def __init__(self):
        self.effects = []
        self.fields = {}
        self.receipts = {}

    def perform(self, authorization, kind, *, key=None, content=None):
        if authorization.get('status') != 'authorized' or authorization['action'] != kind:
            raise AssertionError('Fake effect requires the matching persisted authorization')
        if authorization['action_id'] in {e['authorization'] for e in self.effects}:
            raise AssertionError('Duplicate effect')
        if kind == 'apply' and key in self.receipts:
            raise AssertionError('A second submission reached the fake portal')
        event = {'authorization': authorization['action_id'], 'kind': kind, 'key': key, 'content': content}
        self.effects.append(event)
        if kind == 'apply':
            self.receipts[key] = 'Candidatura recebida no portal fictício'
        return event

    def type_field(self, key, value, *, truncate=False):
        self.fields[key] = value[:4] if truncate else value


class ProcessJourneyTests(unittest.TestCase):
    def setUp(self):
        self.network = patch.object(socket.socket, 'connect', side_effect=AssertionError('Network disabled'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.fx = support.WorkflowTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.root = self.fx.root
        self.fx.approve_profile({action: 'ask' for action in support.ACTIONS})
        profile = Profile(self.root)
        profile.answer('identity', 'name', 'Marina Exemplo')
        profile.answer('identity', 'email', 'marina@example.invalid')
        profile.answer('preferences', 'roles', ['Atendente'])
        profile.answer('preferences', 'contracts', ['CLT'])
        profile.answer('preferences', 'salary.floors', [{'contract': 'CLT', 'amount': 3500, 'currency': 'BRL', 'period': 'month'}])
        profile.answer('preferences', 'salary.public_expectation', {'amount': 4200, 'currency': 'BRL', 'period': 'month'})
        profile.answer('connections', 'accounts', [
            {'provider': 'portal', 'alias': 'portal-a', 'address': 'marina@example.invalid'},
            {'provider': 'searchsite', 'alias': 'portal-b', 'address': 'marina@example.invalid'},
            {'provider': 'gmail', 'alias': 'principal', 'address': 'marina@example.invalid'},
            {'provider': 'outlook', 'alias': 'alternativa', 'address': 'marina@example.invalid'}])
        profile.approve(profile.get()['version'])
        from scripts.job.resumes import ResumeManager
        resumes = ResumeManager(self.root)
        fact = resumes.add_fact('Marina Exemplo, experiência fictícia em atendimento.', 'candidate:chat', True)
        self.resume = resumes.approve(resumes.draft('atendimento', '# Marina Exemplo\n\nExperiência fictícia em atendimento.', [fact['id']])['id'])
        self.fx.wf.close()
        self.generation = 1
        self.turns, self.calls = [], []
        self.services = FakeServices()
        self.guard = self.root / 'offline-guard'
        self.guard.mkdir()
        (self.guard / 'sitecustomize.py').write_text(
            'import socket, subprocess, os\n'
            'def deny(*args, **kwargs):\n    raise RuntimeError("SIMULATION_EXTERNAL_ACCESS_BLOCKED")\n'
            'socket.socket.connect = deny\nsocket.socket.connect_ex = deny\n'
            'socket.socket.sendto = deny\nsocket.create_connection = deny\nsocket.getaddrinfo = deny\n'
            'subprocess.Popen = deny\nos.system = deny\n'
            'os.environ["JOB_SIMULATION_GUARD"] = "active"\n')
        self.env = {**os.environ, 'PYTHONPATH': str(self.guard) + os.pathsep + str(PROJECT),
                    'PATH': str(self.guard), 'PYTHONDONTWRITEBYTECODE': '1'}
        self.call('goal', data={'summary': 'Buscar vagas de atendimento e acompanhar os processos, perguntando antes de agir', 'actions': list(support.ACTIONS)})
        for provider, account, kind in [('chrome', 'public', 'browser'), ('chrome', 'portal-a', 'browser'),
                                         ('chrome', 'portal-b', 'browser'), ('gmail', 'principal', 'mail'), ('outlook', 'alternativa', 'mail')]:
            self.capability(provider, account, kind)

    def tearDown(self):
        destination = os.environ.get('JOB_PROCESS_REPORT')
        if not destination:
            return
        target = Path(destination) / self._testMethodName
        target.mkdir(parents=True, exist_ok=False)
        report = {'dialogue': self.turns, 'cli_calls': self.calls, 'fake_effects': self.services.effects,
                  'fake_receipts': self.services.receipts, 'network': 'blocked in CLI subprocesses',
                  'scope': 'Scripted dialogue, real local controller, fake portal and mailbox. No live account.'}
        (target / 'evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        lines = ['# Percurso fictício após o onboarding', '',
                 'O controle local e a CLI são reais. Portal, caixa postal e respostas da pessoa são simulados. Acesso à rede e novos processos estão bloqueados nas chamadas da CLI.', '']
        for turn in self.turns:
            lines.extend(['IA: ' + turn['ia'], '', 'Pessoa: ' + turn['pessoa'], ''])
        lines.extend([f'Chamadas à CLI: {len(self.calls)}.', f'Efeitos apenas nos simuladores: {len(self.services.effects)}.', ''])
        (target / 'dialogue.md').write_text('\n'.join(lines))

    def call(self, *args, data=None, success=True):
        process = subprocess.run([sys.executable, '-m', 'scripts.job.cli', '--root', str(self.root), *args, '--json'],
                                 input=json.dumps(data) if data is not None else None, text=True, capture_output=True,
                                 env=self.env, cwd=PROJECT, timeout=15)
        self.assertEqual(process.returncode, 0 if success else 1, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.calls.append({'command': list(args), 'input': data, 'result': result, 'expected_success': success})
        return result

    def turn(self, guide, person):
        self.turns.append({'ia': guide, 'pessoa': person})

    def capability(self, provider, account, kind='browser', status='ready'):
        return self.call('capability', data={'kind': kind, 'provider': provider, 'account': account, 'status': status,
                                            'checked_at': now(), 'evidence': 'Estado conferido no simulador local'})

    def vacancy(self, key, company='Loja Exemplo', **changes):
        vacancy = {'role': 'Atendente', 'modality': 'remote', 'contract': 'CLT', 'languages': [],
                   'salary': {'min': 4000, 'max': 4500, 'currency': 'BRL', 'period': 'month', 'estimated': False}, **changes}
        return self.call('opportunity', data={'company': company, 'title': 'Atendente', 'portal': 'portal',
                                             'aliases': ['job:portal:' + key], 'identity_verified': True,
                                             'evidence': 'Anúncio e identidade conferidos no simulador', 'vacancy': vacancy})

    def authorize(self, action, *, success=True, **extra):
        payload = {'action': action, 'owner': 'chat:simulacao', 'generation': self.generation,
                   'channel': {'provider': 'chrome', 'account': 'portal-a'},
                   'user_confirmation': 'Marina confirmou esta ação no roteiro fictício', **extra}
        if action == 'research':
            payload['source_url'] = 'https://jobs.example.org/'
        if action == 'apply':
            payload.update(resume_id=self.resume['id'], resume_sha256=self.resume['sha256'])
        return self.call('action', 'authorize', data=payload, success=success)

    def complete(self, action, outcome='confirmed', *, success=True, **extra):
        return self.call('action', 'complete', action['action_id'], success=success,
                         data={'owner': 'chat:simulacao', 'generation': self.generation, 'outcome': outcome,
                               'evidence': 'Resultado conferido no destino fictício', 'evidence_source': 'destination_page',
                               'checked_at': now(), **extra})

    def perform(self, kind, *, key=None, content=None, **extra):
        action = self.authorize(kind, **extra)
        if kind == 'email_reply':
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), extra['reply']['content_sha256'])
            self.assertEqual(extra['reply']['recipient'], 'message_sender')
        self.services.perform(action, kind, key=key, content=content)
        self.complete(action)
        return action

    def mail(self, id, category, job=None, **extra):
        data = {'provider': 'gmail', 'account': 'principal', 'message_id': id, 'category': category,
                'received_at': now(), 'summary': 'Mensagem fictícia de recrutamento', **extra}
        if job is not None:
            data.update(opportunity_id=job, link_evidence='Empresa e processo conferidos no portal fictício')
        read = self.authorize('email_read', channel={'provider': data['provider'], 'account': data['account']}, scope_key='mensagem:' + id)
        self.services.perform(read, 'email_read', key=id)
        message = self.call('email', data=data)
        self.complete(read, evidence_source='destination_email')
        return message

    @staticmethod
    def ref(message):
        return {key: message[key] for key in ('provider', 'account', 'message_id')}

    def test_search_application_and_email_until_interview(self):
        self.turn('Vou procurar vagas de atendente remoto conforme seu perfil. Posso começar a busca?', 'Pode procurar. Antes de enviar, me mostra.')
        self.perform('research', scope_key='portal-a:atendente-remoto', channel={'provider': 'chrome', 'account': 'public'})
        job = self.vacancy('vaga-a')['opportunity_id']
        low = self.vacancy('abaixo-piso', 'Mercado Fictício', salary={'min': 2500, 'max': 3000, 'currency': 'BRL', 'period': 'month', 'estimated': False})
        self.assertEqual(low['evaluation']['decision'], 'discarded')
        unknown = self.vacancy('sem-salario', 'Comércio Exemplo', salary=None)
        self.turn('A Loja Exemplo oferece trabalho remoto com carteira assinada, entre R$ 4.000 e R$ 4.500. O Mercado Fictício ficou abaixo do seu mínimo. O Comércio Exemplo não informa salário. Quer considerar essa última vaga mesmo assim?', 'Pode considerar só essa sem salário. Meu mínimo continua o mesmo.')
        self.call('decision', data={'opportunity_id': unknown['opportunity_id'], 'reasons': unknown['evaluation']['reasons'],
                                    'user_confirmation': 'Pode considerar só essa sem salário. Meu mínimo continua o mesmo.'})
        self.assertEqual(self.vacancy('sem-salario', 'Comércio Exemplo', salary=None)['evaluation']['decision'], 'eligible')
        self.assertEqual(self.vacancy('vaga-a')['opportunity_id'], job)
        self.call('coverage', 'save', data={'source': 'portal-a', 'query': 'atendente remoto', 'pages': 1,
                                           'status': 'complete', 'checked_at': now(), 'next_action': 'Pesquisar outra fonte'})
        self.turn('Para usar o portal, abra a página de acesso que eu indicar e faça seu login. Senha e código ficam nessa página. Depois me diga que entrou.', 'Entrei. Pode preparar a candidatura na Loja Exemplo.')
        self.perform('register', opportunity_id=job)
        fill = self.authorize('fill', opportunity_id=job)
        self.services.type_field('name', 'Marina Exemplo', truncate=True)
        self.assertNotEqual(self.services.fields['name'], 'Marina Exemplo')
        self.services.type_field('name', 'Marina Exemplo')
        self.services.type_field('salary', '4200')
        self.assertEqual(self.services.fields, {'name': 'Marina Exemplo', 'salary': '4200'})
        self.services.perform(fill, 'fill', key=job)
        self.complete(fill)
        self.turn('O formulário está preenchido. Vou revisar com você antes de enviar.', 'O nome ficou cortado na tela. Confere e corrige antes de mandar.')
        correction = self.authorize('fill', opportunity_id=job)
        self.services.type_field('name', 'Marina Exemplo')
        self.services.perform(correction, 'fill', key=job)
        self.complete(correction)
        self.turn('Conferi o formulário e o currículo de atendimento. A pretensão informada será R$ 4.200 por mês. Seu mínimo de R$ 3.500 continua privado. Posso enviar à Loja Exemplo?', 'Pode enviar.')
        self.perform('apply', opportunity_id=job, key=job)
        self.assertEqual(self.services.receipts[job], 'Candidatura recebida no portal fictício')
        self.authorize('apply', opportunity_id=job, success=False)
        self.turn('A Loja Exemplo confirmou o recebimento. Posso conferir os e-mails desse processo?', 'Sim, pode olhar.')
        self.mail('recebimento', 'application_update', job)
        reply = self.mail('pedido-disponibilidade', 'recruiter_contact', job, step_key='disponibilidade', step_kind='email_reply')
        reminder = self.mail('lembrete', 'recruiter_contact', job, step_key='disponibilidade', step_kind='email_reply', provider='outlook', account='alternativa')
        self.assertEqual(reply['step_id'], reminder['step_id'])
        self.turn('A recrutadora pediu sua disponibilidade. Você pode conversar na sexta-feira à tarde?', 'Posso, às 14 horas, no horário de Brasília.')
        draft = 'Olá! Tenho interesse na vaga e disponibilidade na sexta-feira às 14h, no horário de Brasília. Obrigada, Marina.'
        self.turn('Vou responder à recrutadora da Loja Exemplo: "' + draft + '" Posso enviar?', 'Pode enviar esse texto.')
        reply_args = {'channel': {'provider': 'gmail', 'account': 'principal'}, 'message': self.ref(reply),
                      'reply': {'recipient': 'message_sender', 'content_sha256': hashlib.sha256(draft.encode()).hexdigest(), 'summary': 'Disponibilidade confirmada pela pessoa'}}
        self.perform('email_reply', content=draft, **reply_args)
        self.authorize('email_reply', **{**reply_args, 'message': self.ref(reminder), 'channel': {'provider': 'outlook', 'account': 'alternativa'}}, success=False)
        self.mail('complemento', 'application_update', job, step_key='complemento', step_kind='form', summary='Confirmar disponibilidade')
        self.turn('Chegou um formulário para confirmar sua disponibilidade. Posso preencher com o horário que você informou?', 'Pode.')
        self.perform('fill', opportunity_id=job, step_key='complemento')
        self.mail('questionario', 'assessment', job, step_key='pessoal', summary='Responder questionário pessoal')
        personal = next(s for s in self.call('steps') if s['step_key'] == 'pessoal')
        self.call('transition', data={'id': personal['id'], 'state': 'candidate_pending', 'evidence': 'Questionário de autorrelato precisa da própria pessoa'})
        self.turn('O questionário pergunta sobre suas preferências pessoais. Você precisa respondê-lo. Vou abrir a página do processo; quando terminar, diga "terminei o questionário".', 'Terminei o questionário.')
        self.call('transition', data={'id': personal['id'], 'state': 'completed', 'evidence': 'Participação informada no chat', 'user_confirmation': 'Terminei o questionário.'})
        self.mail('entrevista', 'interview', job, step_key='entrevista', summary='Escolher horário da entrevista')
        appointment = (datetime.now(timezone.utc) + timedelta(days=3)).replace(hour=17, minute=0, second=0, microsecond=0)
        starts = appointment.isoformat()
        date = appointment.astimezone(timezone(timedelta(hours=-3))).strftime('%d/%m/%Y')
        self.turn(f'A empresa ofereceu uma entrevista em {date}, às 14h no horário de Brasília. Esse horário serve?', 'Sim, essa data também serve. Pode marcar.')
        self.perform('schedule', opportunity_id=job, step_key='entrevista', schedule={'starts_at': starts})
        state = self.call('status')
        self.assertEqual(state['ledger']['confirmed'], 1)
        attendance = next(s for s in self.call('steps') if s['kind'] == 'interview_attendance')
        self.assertEqual(attendance['state'], 'candidate_pending')
        self.assertIn('Participar da entrevista', state['message'])
        self.turn('A entrevista está marcada. Você participará pessoalmente. A candidatura continua registrada uma única vez. Ao terminar, diga "participei da entrevista".', 'Participei da entrevista.')
        self.call('transition', data={'id': attendance['id'], 'state': 'completed', 'evidence': 'Participação relatada pela pessoa', 'user_confirmation': 'Participei da entrevista.'})
        obsolete = self.call('step', data={'job_id': job, 'step_key': 'nova-conversa', 'kind': 'interview', 'summary': 'Aguardar segunda entrevista'})
        self.mail('resultado', 'rejection', job)
        self.call('transition', data={'id': obsolete['id'], 'state': 'cancelled', 'evidence': 'Encerramento deste processo confirmado pela mensagem fictícia'})
        self.turn('A Loja Exemplo informou que não seguirá com a candidatura. Vou manter o histórico e continuar procurando dentro dos seus critérios.', 'Tudo bem. Pode continuar.')
        self.assertEqual(self.call('status')['ledger']['confirmed'], 1)
        self.assertEqual(len(self.services.receipts), 1)

    def test_login_uncertain_submission_resume_and_mail_coverage(self):
        a = self.vacancy('login')['opportunity_id']
        b = self.vacancy('outra', 'Outra Loja Exemplo')['opportunity_id']
        self.capability('chrome', 'portal-a', status='auth_required')
        self.turn('O primeiro portal pediu login. Deixei a página aberta para você. Enquanto isso, posso continuar na Outra Loja Exemplo pelo segundo portal?', 'Pode continuar na outra. Depois faço esse login.')
        self.authorize('apply', opportunity_id=a, success=False)
        action = self.authorize('apply', opportunity_id=b, channel={'provider': 'chrome', 'account': 'portal-b'})
        self.services.perform(action, 'apply', key=b)
        self.complete(action, 'uncertain', evidence='A confirmação não apareceu após o envio fictício', evidence_source='agent_report')
        self.authorize('apply', opportunity_id=b, channel={'provider': 'chrome', 'account': 'portal-b'}, success=False)
        self.turn('A página parou de responder depois do envio. Vou conferir a lista de candidaturas antes de tentar qualquer novo envio.', 'Preciso sair. Pare por enquanto.')
        self.call('stop')
        self.authorize('research', scope_key='retomada', channel={'provider': 'chrome', 'account': 'public'}, success=False)
        self.turn('Parei e guardei o ponto em que estávamos. Quando voltar, diga "continuar". Nada ficará sendo enviado enquanto a execução estiver parada.', 'Continuar.')
        self.generation = self.call('resume-work')['control']['generation']
        self.call('action', 'authorize', success=False, data={'action': 'research', 'source_url': 'https://jobs.example.org/', 'owner': 'chat:antigo', 'generation': 1,
                 'channel': {'provider': 'chrome', 'account': 'public'}, 'scope_key': 'retomada', 'user_confirmation': 'Pode buscar'})
        self.assertIn(b, self.services.receipts)
        self.complete(action)
        self.turn('Conferi a lista: a Outra Loja Exemplo recebeu sua candidatura. Registrei a confirmação, sem enviar outra vez.', 'Certo. Pode conferir meus e-mails também.')
        self.assertEqual(len([e for e in self.services.effects if e['kind'] == 'apply']), 1)
        read = self.authorize('email_read', channel={'provider': 'gmail', 'account': 'principal'}, scope_key='cobertura:retomada')
        self.services.perform(read, 'email_read')
        run = self.call('mail-coverage', 'begin', data={'minutes': 30})
        start, end = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), now()
        window = {'run_id': run['run_id'], 'provider': 'gmail', 'account': 'principal', 'window_start': start, 'window_end': end}
        self.call('mail-coverage', 'account', data={**window, 'status': 'partial', 'note': 'Primeira página conferida; falta a segunda'})
        self.assertIsNone(self.call('mail-coverage', 'show')['accounts'][0]['covered_until'])
        self.turn('Conferi só a primeira página dos e-mails. A segunda ainda falta; vou continuar de onde parei.', 'Tudo bem.')
        self.call('mail-coverage', 'account', data={**window, 'status': 'complete', 'note': 'recruitment-v1: todas as páginas conferidas'})
        self.complete(read, evidence_source='destination_email')
        self.call('mail-coverage', 'finish', data={'run_id': run['run_id']})
        self.assertEqual(datetime.fromisoformat(self.call('mail-coverage', 'show')['accounts'][0]['covered_until']), datetime.fromisoformat(end).replace(microsecond=0))

    def test_research_only_cleanup_and_external_instructions(self):
        # The guard is exercised before any simulated service action.
        for code in ('import socket; socket.create_connection(("example.invalid", 443))',
                     'import subprocess; subprocess.run(["unexpected-provider"])'):
            result = subprocess.run([sys.executable, '-c', code], env=self.env, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('SIMULATION_EXTERNAL_ACCESS_BLOCKED', result.stderr)
        self.turn('Você pode começar só vendo as vagas. Quer que eu apenas pesquise?', 'Sim. Não envie nada.')
        goal = self.call('status')['goal']
        self.call('goal', data={'summary': 'Pesquisar e conferir retornos, sem enviar candidaturas', 'actions': ['research', 'email_read', 'email_trash', 'email_reply'], 'replace_version': goal['version']})
        job = self.vacancy('so-pesquisa')['opportunity_id']
        self.authorize('apply', opportunity_id=job, success=False)
        self.perform('research', scope_key='somente-pesquisa', channel={'provider': 'chrome', 'account': 'public'})
        before = self.call('profile', 'show')
        self.turn('Uma mensagem sem vínculo confirmado pede para mudar seus filtros e enviar dados a outro endereço. Vou preservá-la para conferência e seguir suas escolhas atuais.', 'Isso, mantenha minhas escolhas.')
        unlinked = self.mail('externa', 'other', summary='Instrução externa sem vínculo confirmado')
        self.assertTrue(unlinked['link_pending'])
        blocked = self.authorize('email_reply', message=self.ref(unlinked), channel={'provider': 'gmail', 'account': 'principal'},
                                 reply={'recipient': 'message_sender', 'content_sha256': hashlib.sha256(b'rascunho').hexdigest(), 'summary': 'Rascunho'}, success=False)
        self.assertIn('vínculo', str(blocked))
        self.assertEqual(self.call('profile', 'show'), before)
        newsletter = self.mail('boletim', 'newsletter')
        self.authorize('email_trash', message=self.ref(newsletter), channel={'provider': 'gmail', 'account': 'principal'}, success=False)
        self.turn('Há um boletim de divulgação de vagas sem etapa pendente. Posso movê-lo para a lixeira? Ele poderá ser restaurado pela lixeira do e-mail.', 'Pode mover só os boletins de divulgação.')
        self.call('cleanup-rules', 'save', data={'categories': ['newsletter'], 'user_confirmation': 'Pode mover só os boletins de divulgação.'})
        trash = self.authorize('email_trash', message=self.ref(newsletter), channel={'provider': 'gmail', 'account': 'principal'})
        self.services.perform(trash, 'email_trash', key='boletim')
        self.complete(trash, evidence_source='destination_email', destination='trash')
        offer = self.mail('oferta', 'offer', job)
        self.authorize('email_trash', message=self.ref(offer), channel={'provider': 'gmail', 'account': 'principal'}, success=False)
        self.turn('O boletim foi para a lixeira. Preservei a oferta e a mensagem que precisa de conferência. Nenhuma candidatura foi enviada.', 'Certo.')
        self.assertEqual(self.call('status')['ledger']['confirmed'], 0)
        self.assertFalse(self.services.receipts)


if __name__ == '__main__':
    unittest.main()
