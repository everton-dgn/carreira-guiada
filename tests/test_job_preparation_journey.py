"""Novice preparation via real CLI processes, a simulated clock and no network."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''
import os, socket, subprocess, sys
from datetime import datetime
def deny(*args, **kwargs):
    raise RuntimeError("SIMULATION_EXTERNAL_ACCESS_BLOCKED")
socket.socket.connect = socket.socket.connect_ex = socket.socket.sendto = deny
socket.create_connection = socket.getaddrinfo = deny
subprocess.Popen = os.system = deny
class SimulationDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime.fromisoformat(os.environ["JOB_TEST_TIME"])
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)
import scripts.job.workflow as workflow
import scripts.job.checkpoint as checkpoint
import scripts.job.resumes as resumes
workflow.datetime = checkpoint.datetime = resumes.datetime = SimulationDateTime
from scripts.job.cli import main
if sys.argv[1:] == ["guard"]:
    for action in (lambda: socket.create_connection(("example.invalid", 443)),
                   lambda: subprocess.Popen(["unused"])):
        try:
            action()
        except RuntimeError as error:
            assert str(error) == "SIMULATION_EXTERNAL_ACCESS_BLOCKED"
        else:
            raise AssertionError("External access was not blocked")
    print('{"guard": "active"}')
else:
    raise SystemExit(main())
'''

CV = '''# Marina Exemplo

marina@example.invalid

## Objetivo

Desenvolvimento frontend com React e TypeScript.

## Formação

Curso fictício de Sistemas de Informação concluído em 2023.

## Experiência

Empresa Exemplo, desenvolvimento de formulários com React entre 2023 e 2025.

## Habilidades

React, TypeScript e Git. Projeto pessoal fictício de organização de tarefas.

## Idiomas

Português nativo.
'''


class PreparationJourneyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='job-preparation-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.time = '2026-11-06T18:00:00-03:00'
        self.calls, self.turns = [], []

    def tearDown(self):
        destination = os.environ.get('JOB_PREPARATION_REPORT')
        if not destination:
            return
        target = Path(destination) / self._testMethodName
        target.mkdir(parents=True, exist_ok=False)
        (target / 'evidence.json').write_text(json.dumps({'calls': self.calls, 'dialogue': self.turns,
            'scope': 'CLI real, respostas roteirizadas, relógio simulado, rede e subprocessos externos bloqueados.'}, ensure_ascii=False, indent=2))
        lines = ['# Preparação fictícia e retomada no dia seguinte', '',
                 'A CLI e os arquivos são reais. Pessoa, perfis e relógio são simulados. Nenhum site foi acessado.', '']
        for turn in self.turns:
            lines += ['IA: ' + turn['assistant'], '', 'Pessoa: ' + turn['person'], '']
        (target / 'dialogue.md').write_text('\n'.join(lines))
        if (self.root / '.job/resumes').exists():
            shutil.copytree(self.root / '.job/resumes', target / 'curriculos-ficticios')

    def call(self, *args, data=None, success=True, plain=False):
        command = [sys.executable, '-c', BOOTSTRAP, '--root', str(self.root), *args]
        if not plain:
            command.append('--json')
        result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
            capture_output=True, text=True, cwd=PROJECT, timeout=15,
            env={**os.environ, 'JOB_TEST_TIME': self.time, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        output = result.stdout.strip() if plain else json.loads(result.stdout)
        self.calls.append({'time': self.time, 'command': list(args), 'input': data, 'output': output})
        return output

    def say(self, assistant, person):
        self.turns.append({'assistant': assistant, 'person': person})

    def answer(self, section, field, words, value, confirmed=False):
        state = self.call('start')
        self.assertEqual(state['next_step'], section)
        self.assertEqual(state['question']['field'], field)
        self.say(state['message'], words)
        self.call('profile', 'answer', section, data={'field': field, 'value': value, 'confirmed': confirmed})

    def prepare(self):
        self.say(self.call('start')['message'], 'Não tenho currículo. Trabalho com sites, mas não sei me apresentar.')
        self.call('intake', 'choose', data={'mode': 'create'})
        self.answer('identity', 'name', 'Marina Exemplo', 'Marina Exemplo')
        self.answer('identity', 'email', 'marina@example.invalid', 'marina@example.invalid')
        for field, text in [('education', 'Curso fictício de Sistemas de Informação concluído em 2023.'),
                            ('experience', 'Empresa Exemplo, desenvolvimento de formulários com React entre 2023 e 2025.'),
                            ('skills', 'React, TypeScript e Git. Projeto pessoal fictício de organização de tarefas.'),
                            ('languages', 'Português nativo.'), ('extra', None)]:
            state = self.call('start')
            self.assertEqual(state['question']['field'], field)
            self.say(state['message'], text or 'Por enquanto é só isso.')
            self.call('intake', 'answer', data={'field': field, 'text': text})
        answers = {
            'roles': ('Quero fazer interfaces com React.', ['Desenvolvimento frontend']),
            'modalities': ('Quero trabalhar de casa.', ['remoto']),
            'currencies': ('Em reais.', ['BRL']), 'levels': ('Não sei os nomes. Sem preferência.', []),
            'contracts': ('Quero carteira assinada.', ['CLT']), 'locations': ('No Brasil.', ['Brasil']),
            'technologies': ('Quero usar React.', ['React']),
            'languages': ('Só português, como já contei.', [{'name': 'Português', 'level': 6, 'required': False}]),
            'blocked_companies': ('Nenhuma.', []), 'blocked_sectors': ('Nenhum.', []),
            'blocked_platforms': ('Nenhum.', []), 'missing': ('Pode me perguntar.', 'ask'),
            'salary.floors': ('No mínimo cinco mil reais por mês.', [{'contract': 'CLT', 'currency': 'BRL', 'period': 'month', 'amount': 5000}]),
            'salary.public_expectation': ('Pode pedir seis mil reais por mês.', {'currency': 'BRL', 'period': 'month', 'amount': 6000}),
            'salary.missing': ('Pode considerar a vaga.', 'accept'),
            'salary.estimated': ('Confirme antes.', 'ask'), 'salary.range': ('Confirme o mínimo antes.', 'ask'),
        }
        # The agent reuses the language already confirmed in the CV conversation.
        self.call('profile', 'answer', 'preferences', data={'field': 'languages', 'value': answers['languages'][1]})
        for field, (words, value) in answers.items():
            if field != 'languages':
                self.answer('preferences', field, words, value)
        self.answer('sources', 'urls', 'Deixe os sites para depois.', [])
        self.say(self.call('start')['message'], 'Pergunte antes de tudo. Agora quero só organizar minha apresentação.')
        from scripts.job.profile import ACTIONS
        self.call('profile', 'save', 'permissions', data={action: 'ask' for action in ACTIONS})
        self.answer('connections', 'accounts', 'Não quero conectar e-mail agora.', [])
        self.assertEqual(self.call('start')['next_step'], 'profile_approval')
        self.say('Você procura frontend remoto no Brasil, CLT, mínimo privado de R$ 5.000 e pretensão de R$ 6.000. Sites e e-mail ficam para depois. Qualquer ação exige sua confirmação. Está correto?', 'Sim, pode salvar assim.')
        self.call('profile', 'approve', '--version', str(self.call('profile', 'status')['version']))
        draft = self.call('resume', 'draft', data={'label': 'Frontend', 'markdown': CV,
                          'fact_ids': self.call('intake', 'status')['fact_ids']})
        self.assertTrue(self.call('resume', 'check', draft['id'])['passed'])
        self.say('Preparei este currículo para conferir:\n\n' + CV, 'Está certo. Pode aprovar, sem enviar.')
        self.call('resume', 'approve', draft['id'])
        self.assertEqual(self.call('start')['next_step'], 'professional_presence')
        return draft

    def checkpoint(self, phase, summary, next_action, needs_user=True):
        return self.call('checkpoint', 'save', data={'phase': phase, 'summary': summary,
                         'next_action': next_action, 'needs_user': needs_user})

    def next_day(self):
        self.time = (datetime.fromisoformat(self.time) + timedelta(days=1)).isoformat()

    def test_full_preparation_linkedin_github_and_next_day(self):
        draft = self.prepare()
        self.say(self.call('start')['message'], 'Quero melhorar os dois. Não sei escrever sobre mim.')
        self.call('presence', 'choose', data={'decision': 'now', 'topics': ['linkedin', 'github'], 'confirmation': 'Quero revisar os dois perfis.'})
        link = 'https://www.linkedin.com/in/pessoa-ficticia'
        self.say('Envie o link do seu LinkedIn. Vou analisar sua apresentação; nada será publicado.', link)
        self.call('presence', 'source', data={'topic': 'linkedin', 'source': link})
        self.say('Nesta simulação o perfil não está disponível. Pode colar o título e o Sobre aqui, sem senha.', 'Título: desenvolvedora. Sobre: faço interfaces e formulários com React.')
        self.call('presence', 'source', data={'topic': 'linkedin', 'source': 'candidate_text'})
        content = 'Título: Desenvolvimento frontend com React e TypeScript.\nSobre: Atuação em interfaces e formulários na Empresa Exemplo entre 2023 e 2025. Projeto pessoal de organização de tarefas.'
        self.call('presence', 'draft', data={'topic': 'linkedin', 'source': 'candidate_text', 'content': content})
        self.say('Preparei as sugestões de título e Sobre:\n' + content, 'Vou parar agora. Amanhã termino.')
        note = self.checkpoint('presence', 'Currículo aprovado; LinkedIn em revisão. GitHub ainda não começou.', 'Conferir título e Sobre do LinkedIn já salvos.')
        self.call('stop')
        self.next_day()
        state = self.call('start')
        self.say(state['welcome_back'], 'Continuar de onde parei.')
        self.assertEqual(state['resume_options'], ['continue', 'review'])
        self.assertEqual(self.call('checkpoint', 'show'), note)
        self.assertTrue(self.call('status')['control']['stopped'])
        self.assertNotIn('Ainda preciso conferir o acesso', self.call('status')['message'])
        self.assertNotIn('Diga se quer apenas conhecer vagas', self.call('status')['message'])
        resumed = self.call('resume-work')
        self.assertFalse(resumed['control']['stopped'])
        self.assertEqual(resumed['counts']['actions'], {})
        self.assertNotIn('Ainda preciso conferir o acesso', resumed['message'])
        saved = self.call('presence', 'show')['reviews']['linkedin']
        self.assertEqual(saved['link'], link)
        self.assertEqual(saved['content'], content)
        self.assertFalse(saved['reviewed'])
        self.say('Seu currículo continua aprovado. Vamos retomar o título e o Sobre já salvos, sem repetir seus dados.', 'Conferi, pode finalizar a revisão. Vou publicar depois.')
        self.call('presence', 'finish', data={'topic': 'linkedin', 'version': saved['version'], 'confirmation': 'Conferi; vou publicar depois.'})
        self.assertEqual(self.call('presence', 'status')['next_topic'], 'github')
        self.call('presence', 'source', data={'topic': 'github', 'source': 'https://github.com/pessoa-ficticia'})
        self.say('Quais projetos posso considerar para apresentar seu trabalho?', 'Só meu organizador de tarefas. O código da empresa não pode entrar.')
        github = 'README do perfil: Marina Exemplo, desenvolvimento frontend com React e TypeScript.\nProjeto em destaque: organizador fictício de tarefas. Descrever uso, instalação e limitações.\nNão incluir projetos privados da empresa.'
        self.call('presence', 'draft', data={'topic': 'github', 'source': 'candidate_text', 'content': github})
        self.say('Sugestão para o perfil e o projeto:\n' + github, 'Gostei. Pode finalizar a revisão, mas não publique nada.')
        self.call('presence', 'finish', data={'topic': 'github', 'version': 1, 'confirmation': 'Revisado; não publicar.'})
        self.assertFalse(self.call('presence', 'status')['publication_authorized'])
        self.assertEqual(self.call('start')['next_step'], 'interview_preparation')
        self.say(self.call('start')['message'], 'Quero deixar o treino para depois e começar a busca.')
        self.call('practice', 'choose', data={'decision': 'later'})
        self.assertEqual(self.call('start')['next_step'], 'sources')
        self.assertNotIn('continuamos preparando o currículo', self.call('start')['message'])
        self.answer('sources', 'urls', 'Pode usar este site fictício.', ['https://jobs.example.invalid/vagas'])
        self.call('profile', 'approve', '--version', str(self.call('profile', 'status')['version']))
        self.assertEqual(self.call('start')['next_step'], 'execution_readiness')
        self.assertEqual(self.call('resume', 'show', draft['id'])['status'], 'approved')
        final = self.checkpoint('waiting', 'Currículo e revisões de LinkedIn e GitHub concluídos; nada publicado.', 'Combinar se a pessoa quer começar a busca.')
        self.call('stop')
        self.next_day()
        self.assertEqual(self.call('checkpoint', 'show'), final)
        self.assertTrue(self.call('status')['control']['stopped'])
        self.assertEqual(self.call('status')['counts'], {'opportunities': 0, 'actions': {}, 'messages': 0})
        self.assertEqual(self.call('presence', 'status')['pending'], [])
        self.assertEqual(self.call('resume', 'list')[0]['sha256'], draft['sha256'])

    def test_profile_text_is_saved_before_analysis_and_invalidates_old_review(self):
        self.call('presence', 'choose', data={'decision': 'now', 'topics': ['linkedin'], 'confirmation': 'Quero revisar o LinkedIn.'})
        link = 'https://linkedin.com/in/pessoa-ficticia'
        self.call('presence', 'source', data={'topic': 'linkedin', 'source': link})
        text = 'Título atual: desenvolvedora. Sobre: trabalho com React desde 2023.'
        self.say('Pode colar aqui as partes do perfil que quer revisar.', text + ' Mas vou parar agora.')
        self.call('presence', 'source', data={'topic': 'linkedin', 'source': 'candidate_text', 'material': text})
        self.checkpoint('presence', 'Texto do LinkedIn recebido e salvo; análise ainda não iniciada.', 'Analisar o texto já salvo, sem pedir para colar novamente.', False)
        self.call('stop')
        self.next_day()
        self.call('resume-work')
        saved = self.call('presence', 'show')
        self.assertEqual(saved['materials']['linkedin']['content'], text)
        self.assertEqual(saved['reviews']['linkedin']['link'], link)
        self.call('presence', 'draft', data={'topic': 'linkedin', 'source': 'candidate_text', 'content': 'Desenvolvimento frontend com React desde 2023.'})
        self.call('presence', 'finish', data={'topic': 'linkedin', 'version': 1, 'confirmation': 'Conferi.'})
        corrected = text.replace('2023', '2022')
        self.call('presence', 'source', data={'topic': 'linkedin', 'source': 'candidate_text', 'material': corrected})
        saved = self.call('presence', 'show')
        self.assertFalse(saved['reviews']['linkedin']['reviewed'])
        self.assertIsNone(saved['reviews']['linkedin']['content'])
        self.assertEqual(saved['materials']['linkedin']['content'], corrected)
        self.assertEqual(saved['material_history']['linkedin'][0]['content'], text)
        self.assertEqual(saved['history']['linkedin'][0]['version'], 1)
        self.call('presence', 'finish', data={'topic': 'linkedin', 'version': 1, 'confirmation': 'Confirmação antiga.'}, success=False)

    def test_interview_coaching_and_mock_resume_next_day_without_accounts(self):
        self.say('Podemos treinar uma pergunta com ajuda ou fazer um simulado. Se seu aplicativo tiver voz, você pode falar; por texto também funciona.', 'Quero ajuda para contar um erro que cometi.')
        self.assertEqual(self.call('start', '--focus', 'practice')['next_step'], 'interview_preparation')
        session = self.call('practice', 'start', data={'track': 'behavioral', 'mode': 'coach', 'question_ids': ['erro']})
        key = {'session_id': session['session_id'], 'question_id': 'erro'}
        hint = self.call('practice', 'answer', data={**key, 'text': 'Não sei.'}, plain=True)
        self.assertIn('Tudo bem', hint)
        self.assertIn('sua responsabilidade', hint)
        self.assertIsNone(self.call('practice', 'status')['question']['attempt'])
        self.say(session['question']['question'], 'No projeto de estudo, alterei uma validação e o formulário parou de salvar. Corrigi depois.')
        self.call('practice', 'answer', data={**key, 'text': self.turns[-1]['person']})
        self.checkpoint('practice', 'Primeira resposta salva; falta feedback sobre a correção do formulário.', 'Retomar a mesma resposta e explicar como verificou a correção.')
        self.call('stop')
        self.next_day()
        self.assertEqual(self.call('practice', 'status')['next_step'], 'feedback')
        self.assertTrue(self.call('status')['control']['stopped'])
        self.assertIn('parado', ' '.join(self.call('status')['next_steps']).lower())
        self.call('resume-work')
        feedback = {'strengths': 'Você assumiu a mudança e explicou o problema.', 'improvements': 'Falta dizer como verificou a correção; isso ajuda a entender o resultado.', 'suggestion': 'Mantenha o contexto e acrescente somente a verificação que realmente fez.', 'exercise': 'Explique a verificação em uma frase, sem inventar números.'}
        self.assertNotIn('dados de contato', self.call('status')['message'])
        self.call('practice', 'feedback', data={**key, 'version': 1, **feedback})
        self.say('Você explicou o erro. Falta contar como verificou a correção; podemos ensaiar isso em uma frase.', 'Revisei a regra e testei o envio com campos vazios e preenchidos; consegui reproduzir e corrigir o problema do estudo.')
        self.call('practice', 'answer', data={**key, 'text': self.turns[-1]['person']})
        self.call('practice', 'advance', data=key, success=False)
        self.call('practice', 'feedback', data={**key, 'version': 1, **feedback}, success=False)
        self.call('practice', 'feedback', data={**key, 'version': 2, **feedback, 'strengths': 'A segunda versão descreve os cenários usados na verificação.', 'improvements': 'Na próxima rodada, explique a prevenção que realmente adotou.', 'exercise': 'Pensar em um teste que detecte a regressão antes da entrega.'})
        self.call('practice', 'advance', data=key)
        self.call('practice', 'finish', data={'session_id': key['session_id'], 'report': 'A segunda tentativa tornou a verificação concreta. Ainda não discutimos prevenção.', 'next_steps': 'Escrever um caso de teste com resultado esperado e depois explicar em voz alta, se preferir.'})
        saved = self.call('practice', 'show')['sessions'][0]
        self.assertEqual(len(saved['questions'][0]['attempts']), 2)
        self.assertEqual(saved['completion'], 'completed')
        mock = self.call('practice', 'start', data={'track': 'system_design', 'mode': 'mock', 'question_ids': ['requisitos', 'falhas']})
        self.assertIn('Exercício fictício:', mock['context'])
        key = {'session_id': mock['session_id'], 'question_id': 'requisitos'}
        self.call('practice', 'answer', data={**key, 'text': 'É preciso consultar horários e reservar sem sobreposição. Quero confirmar duração e permissão para cancelar.'})
        self.call('practice', 'feedback', data={**key, 'version': 1, **feedback}, success=False)
        self.call('practice', 'advance', data=key)
        self.call('practice', 'choose', data={'decision': 'later'})
        self.assertNotEqual(self.call('start')['next_step'], 'interview_preparation')
        self.next_day()
        self.call('practice', 'choose', data={'decision': 'now'})
        self.assertEqual(self.call('start')['question']['id'], 'falhas')
        self.call('practice', 'skip', data={'session_id': mock['session_id'], 'question_id': 'falhas'})
        self.call('practice', 'end-questions', data={'session_id': mock['session_id']})
        self.call('practice', 'feedback', data={**key, 'version': 1, **feedback, 'strengths': 'Identificou sobreposição e pediu esclarecimentos.', 'improvements': 'Não avaliamos concorrência, pois a pergunta foi pulada.', 'suggestion': 'Manter os requisitos e esclarecer a operação simultânea em outro treino.', 'exercise': 'Desenhar duas tentativas de reserva no mesmo horário.'})
        self.call('practice', 'finish', data={'session_id': mock['session_id'], 'report': 'Treino encerrado antes do final; falhas não foram avaliadas.', 'next_steps': 'Ensaiar o caso de duas reservas simultâneas.'})
        self.assertEqual(self.call('practice', 'status')['completion'], 'ended_early')
        self.assertEqual(self.call('profile', 'show')['sections'], {})
        self.assertEqual(self.call('status')['counts'], {'opportunities': 0, 'actions': {}, 'messages': 0})

    def test_practice_choice_survives_before_topic_and_deferred_is_visible(self):
        self.call('practice', 'choose', data={'decision': 'now'})
        self.next_day()
        self.assertEqual(self.call('start')['next_step'], 'interview_preparation')
        self.assertIn('treino salvo', self.call('status')['message'])
        self.assertNotIn('dados de contato', self.call('status')['message'])
        session = self.call('practice', 'start', data={'track': 'rh', 'mode': 'coach', 'short': True})
        self.call('practice', 'choose', data={'decision': 'later'})
        self.assertIn('treino adiado', self.call('start')['message'])
        self.assertIn('treino adiado', self.call('start', plain=True))
        self.assertIn('treino adiado', self.call('status')['message'])
        self.assertEqual(self.call('practice', 'status')['session_id'], session['session_id'])

    def test_verified_site_suspicious_job_and_offer_comparison(self):
        self.say('Quer colar sites que conhece ou ajuda para encontrar opções verificadas?', 'Quero ajuda; não conheço nenhum.')
        site = {'kind': 'site', 'subject': 'Portal fictício', 'url': 'https://portal.example.invalid/',
                'checked_at': '2026-11-01T12:00:00Z', 'identity': 'confirmed', 'official_origin': 'confirmed',
                'data_requests': 'ordinary', 'red_flags': [], 'uncertainties': [],
                'evidence': [{'url': 'https://portal.example.invalid/sobre', 'observation': 'Identidade coerente no cenário fictício.', 'kind': 'official'},
                             {'url': 'https://referencia.example.invalid/', 'observation': 'Referência independente fictícia compatível.', 'kind': 'independent'}]}
        record = self.call('research', 'save', data=site)
        self.assertEqual(record['outcome'], 'consider')
        self.assertEqual(self.call('research', 'get', data={'record_id': record['id']}), record)
        self.assertEqual(len(self.call('research', 'suggestions')), 1)
        vacancy = self.call('research', 'save', data={**site, 'kind': 'vacancy', 'subject': 'Anúncio fictício suspeito', 'url': 'https://portal.example.invalid/vaga/123', 'red_flags': ['O anunciante pediu pagamento para continuar.'], 'data_requests': 'dangerous'})
        self.assertEqual(vacancy['outcome'], 'avoid')
        self.assertEqual(len(self.call('research', 'suggestions')), 1)
        self.assertEqual(self.call('profile', 'show')['sections'], {})
        self.say('O portal tem evidências favoráveis neste cenário; esta vaga pede pagamento e não deve seguir. Sua lista de fontes ainda precisa da sua escolha.', 'Entendi. Agora quero comparar duas propostas fictícias.')
        clt = {'label': 'CLT fictícia', 'regime': 'CLT', 'currency': 'BRL', 'gross_monthly': '10000', 'paid_months': 12,
               'guaranteed_extra_annual': '10000', 'variable_annual': '5000', 'benefits_annual': '12000',
               'restricted_funds_annual': '8000', 'taxes_annual': None, 'costs_annual': '1000', 'reserve_annual': '3000'}
        incomplete = self.call('offers', 'save', data=clt)
        self.checkpoint('offers', 'Proposta fictícia salva sem imposto anual.', 'Confirmar imposto ou preservar a comparação incompleta.')
        self.assertTrue(self.call('start')['welcome_back'])
        self.assertNotIn('dados de contato', self.call('status')['message'])
        self.assertIsNone(incomplete['calculation']['net_guaranteed_annual'])
        self.assertEqual(incomplete['calculation']['missing'], ['taxes_annual'])
        self.say('Falta o imposto anual para calcular o líquido. Podemos guardar assim e comparar depois.', 'No exemplo fictício, use 26 mil de imposto anual estimado.')
        first = self.call('offers', 'save', data={**clt, 'taxes_annual': '26000', 'estimated_fields': ['taxes_annual']})
        second = self.call('offers', 'save', data={**clt, 'label': 'PJ fictícia', 'regime': 'PJ', 'gross_monthly': '12000',
            'paid_months': 11, 'guaranteed_extra_annual': '0', 'variable_annual': '0', 'benefits_annual': '0',
            'restricted_funds_annual': '0', 'taxes_annual': '12000', 'costs_annual': '8000', 'reserve_annual': '2000'})
        ids = [first['offer']['id'], second['offer']['id']]
        compared = self.call('offers', 'compare', data={'ids': ids})
        self.assertTrue(compared['comparable'])
        self.assertIsNone(compared['ranking'])
        self.assertEqual([x['calculation']['comparable_annual'] for x in compared['offers']], ['112000', '110000'])
        equivalent = self.call('offers', 'equivalent', data={'base_id': ids[0], 'target_id': ids[1]})
        self.assertEqual(equivalent['gross_monthly_required'], '12181.82')
        self.next_day()
        self.assertEqual(self.call('offers', 'status')['count'], 3)
        self.assertIsNone(self.call('offers', 'get', data={'offer_id': incomplete['offer']['id']})['calculation']['net_guaranteed_annual'])
        self.assertEqual(self.call('status')['counts'], {'opportunities': 0, 'actions': {}, 'messages': 0})

    def test_pending_tabs_survive_next_day_without_claiming_live_work(self):
        first = self.call('tabs', 'reserve', data={'owner': 'chat:simulation', 'purpose': 'Perfil em revisão', 'owned': True})
        self.call('tabs', 'update', data={'reservation': first['reservation'], 'external_id': 'fake:profile', 'protected': True, 'evidence': 'Inventário simulado: texto não salvo no formulário.'})
        second = self.call('tabs', 'reserve', data={'owner': 'chat:simulation', 'purpose': 'Aba da pessoa', 'owned': False})
        self.call('tabs', 'update', data={'reservation': second['reservation'], 'external_id': 'fake:user', 'protected': False, 'evidence': 'Inventário simulado: aba emprestada.'})
        self.call('stop')
        self.next_day()
        self.assertEqual(self.call('tabs', 'status')['in_use'], 2)
        self.call('tabs', 'reserve', data={'owner': 'chat:simulation', 'purpose': 'Terceira aba', 'owned': True}, success=False)
        self.call('tabs', 'release', data={'reservation': first['reservation'], 'outcome': 'closed', 'evidence': 'Não pode fechar: tem pendência.'}, success=False)
        self.call('tabs', 'release', data={'reservation': second['reservation'], 'outcome': 'closed', 'evidence': 'Não pode fechar: é da pessoa.'}, success=False)
        self.call('tabs', 'release', data={'reservation': second['reservation'], 'outcome': 'returned_to_user', 'evidence': 'Aba devolvida sem fechar.'})
        self.call('tabs', 'release', data={'reservation': first['reservation'], 'outcome': 'already_absent', 'evidence': 'Inventário simulado após reiniciar: a aba identificada já não existe.'})
        self.assertEqual(self.call('tabs', 'status')['available'], 2)
        self.assertIsNone(self.call('status')['runner'])

    def test_external_access_guard(self):
        result = subprocess.run([sys.executable, '-c', BOOTSTRAP, 'guard'], cwd=PROJECT,
            env={**os.environ, 'JOB_TEST_TIME': self.time}, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'guard': 'active'})
