"""One fictional person, real CLI, blocked network and simulated next day."""
import hashlib
from datetime import datetime, timedelta, timezone
import unittest

from tests import test_job_preparation_journey as preparation


class ReleaseJourneyTests(unittest.TestCase):
    setUp = preparation.PreparationJourneyTests.setUp
    tearDown = preparation.PreparationJourneyTests.tearDown
    call = preparation.PreparationJourneyTests.call
    say = preparation.PreparationJourneyTests.say
    answer = preparation.PreparationJourneyTests.answer
    prepare = preparation.PreparationJourneyTests.prepare
    checkpoint = preparation.PreparationJourneyTests.checkpoint
    next_day = preparation.PreparationJourneyTests.next_day

    def authorize(self, action, **extra):
        generation = self.call('status')['control']['generation']
        data = {'action': action, 'owner': 'chat:simulacao', 'generation': generation,
                'channel': {'provider': 'chrome', 'account': 'perfil-ficticio'},
                'user_confirmation': 'Confirmado pela pessoa no roteiro fictício.', **extra}
        authorization = self.call('action', 'authorize', data=data)
        checked = self.call('action', 'check', authorization['action_id'],
                            data={'owner': 'chat:simulacao', 'generation': generation})
        self.assertEqual(checked['status'], 'authorized')
        return authorization

    def complete(self, authorization, **extra):
        return self.call('action', 'complete', authorization['action_id'], data={
            'owner': 'chat:simulacao', 'generation': self.call('status')['control']['generation'],
            'outcome': 'confirmed', 'evidence': 'Resultado conferido somente no cenário fictício.',
            'evidence_source': 'destination_page', 'checked_at': self.time, **extra})

    def test_novice_from_start_to_offer_without_external_effects(self):
        self.say(self.call('start')['model_setup']['question'], 'Uso quatro serviços. Não sei os modelos de todos.')
        model_access = self.call('models', 'save', data={'expected_version': 0, 'decision': 'available', 'providers': [
            {'name': 'OpenAI', 'models': [{'name': 'GPT-6.1 Terra', 'efforts': ['medium', 'high']}]},
            {'name': 'Anthropic', 'models': []}, {'name': 'Google', 'models': []},
            {'name': 'Serviço comunitário', 'models': [{'name': 'Modelo local'}]}]})
        self.assertIsNone(self.call('start')['model_setup']['question'])
        self.assertFalse(self.call('models', 'recommend')['automatic_switch'])
        resume = self.prepare()
        self.say('Seu currículo está pronto. Quer revisar LinkedIn e GitHub?', 'Sim, mas preciso de ajuda para escrever.')
        self.call('presence', 'choose', data={'decision': 'now', 'topics': ['linkedin', 'github'], 'confirmation': 'Quero revisar os dois.'})
        for topic, link in [('linkedin', 'https://linkedin.com/in/pessoa-ficticia'), ('github', 'https://github.com/pessoa-ficticia')]:
            self.call('presence', 'draft', data={'topic': topic, 'source': link,
                'content': 'Desenvolvimento frontend com React e TypeScript. Experiência com formulários e testes.'})
            self.call('presence', 'finish', data={'topic': topic, 'version': 1, 'confirmation': 'Conferi o texto.'})
        self.say('Os textos estão salvos. As sugestões ainda não foram publicadas.', 'Pode simular a publicação da biografia do GitHub. Depois quero buscar vagas.')
        self.call('profile', 'answer', 'sources', data={'field': 'urls', 'value': ['https://jobs.example.invalid/']})
        self.call('profile', 'answer', 'connections', data={'field': 'accounts', 'value': [
            {'provider': 'gmail', 'alias': 'principal', 'address': 'marina@example.invalid'}]})
        self.call('profile', 'approve', '--version', str(self.call('profile', 'status')['version']))
        from scripts.job.profile import ACTIONS
        self.call('goal', data={'summary': 'Percurso fictício completo autorizado', 'actions': list(ACTIONS)})
        for kind, provider, account in [('browser', 'chrome', 'perfil-ficticio'), ('mail', 'gmail', 'principal')]:
            self.call('capability', data={'kind': kind, 'provider': provider, 'account': account,
                'status': 'ready', 'checked_at': self.time, 'evidence': 'Sessão apenas do cenário fictício.'})
        review = self.call('presence', 'show')['reviews']['github']
        digest = hashlib.sha256(review['content'].encode()).hexdigest()
        publication = self.authorize('profile_publish', publication={'topic': 'github', 'version': 1,
            'section': 'bio', 'destination': review['link'], 'visibility': 'public', 'content_sha256': digest})
        historical = self.call('action', 'show', publication['action_id'])
        self.assertEqual(historical['publication']['content_sha256'], digest)
        self.assertFalse(historical['execution_allowed'])
        # Only a local synthetic receipt: no browser, API request or live account.
        self.complete(publication, publication_sha256=digest, evidence_url=review['link'])
        practice = self.call('practice', 'start', data={'track': 'technical', 'mode': 'coach', 'short': True})
        response = {'session_id': practice['session_id'], 'question_id': practice['question']['id']}
        self.say(practice['question']['question'], 'Eu explicaria o token: JWT de curta duração, sem incluir nenhuma credencial.')
        self.call('practice', 'answer', data={**response, 'text': 'Eu explicaria o token: JWT de curta duração, sem incluir nenhuma credencial.'})
        self.call('practice', 'feedback', data={**response, 'version': 1, 'strengths': 'Separou o conceito de uma credencial.',
            'improvements': 'Falta explicar a renovação.', 'suggestion': 'Descrever expiração e renovação com um exemplo fictício.',
            'exercise': 'Ensaiar a explicação em duas frases.'})
        search = self.authorize('research', source_url='https://jobs.example.invalid/', scope_key='frontend')
        self.say('Você pode ensaiar de novo quando quiser.', 'Quero pausar só o treino. Continue a busca.')
        self.call('practice', 'choose', data={'decision': 'later'})
        self.assertFalse(self.call('status')['control']['stopped'])
        self.call('action', 'check', search['action_id'], data={'owner': 'chat:simulacao', 'generation': 1})
        self.complete(search)
        self.checkpoint('research', 'Busca fictícia feita; treino salvo.', 'Conferir uma vaga compatível.')
        self.say('O progresso está salvo.', 'Agora vou parar tudo e continuar amanhã.')
        self.call('stop')
        self.next_day()
        self.assertTrue(self.call('start')['welcome_back'])
        self.say('Encontrei seu currículo, os perfis revisados e o treino de ontem.', 'Continue de onde parei.')
        self.call('resume-work')
        self.assertEqual(self.call('models', 'show'), model_access)
        self.assertIsNone(self.call('start')['model_setup']['question'])
        for kind, provider, account in [('browser', 'chrome', 'perfil-ficticio'), ('mail', 'gmail', 'principal')]:
            self.call('capability', data={'kind': kind, 'provider': provider, 'account': account,
                'status': 'ready', 'checked_at': self.time, 'evidence': 'Sessão fictícia reconferida no dia seguinte.'})
        slot = self.call('tabs', 'reserve', data={'owner': 'chat:simulacao', 'purpose': 'Portal fictício', 'owned': True})
        self.call('tabs', 'update', data={'reservation': slot['reservation'], 'external_id': 'fake:portal', 'protected': True, 'evidence': 'Formulário fictício aberto.'})
        vacancy = {'role': 'Desenvolvimento frontend', 'modality': 'remoto', 'contract': 'CLT',
                   'location': 'Brasil', 'technologies': ['React'], 'languages': [],
                   'salary': {'min': 6000, 'max': 7000, 'currency': 'BRL', 'period': 'month', 'estimated': False}}
        job = self.call('opportunity', data={'company': 'Empresa Exemplo', 'title': 'Desenvolvimento frontend',
            'portal': 'portal-ficticio', 'aliases': ['job:portal-ficticio:frontend'], 'identity_verified': True,
            'evidence': 'Empresa e anúncio coerentes no cenário fictício.', 'vacancy': vacancy})
        self.assertEqual(job['evaluation']['decision'], 'eligible')
        self.say('A vaga fictícia respeita suas preferências. A pretensão será R$ 6.000; seu mínimo fica privado.', 'Pode simular o cadastro, preencher e enviar.')
        self.complete(self.authorize('register', opportunity_id=job['opportunity_id']))
        for kind in ('fill', 'apply'):
            action = self.authorize(kind, opportunity_id=job['opportunity_id'], resume_id=resume['id'], resume_sha256=resume['sha256'])
            self.complete(action, **({'submitted_at': self.time} if kind == 'apply' else {}))
        self.call('tabs', 'update', data={'reservation': slot['reservation'], 'external_id': 'fake:portal', 'protected': False, 'evidence': 'Recibo fictício conferido; formulário encerrado.'})
        self.call('tabs', 'release', data={'reservation': slot['reservation'], 'outcome': 'closed', 'evidence': 'Aba fictícia encerrada.'})
        self.assertEqual(self.call('tabs', 'status')['in_use'], 0)
        read = self.authorize('email_read', channel={'provider': 'gmail', 'account': 'principal'}, scope_key='retorno')
        email = {'provider': 'gmail', 'account': 'principal', 'message_id': 'convite-ficticio',
            'category': 'recruiter_contact', 'received_at': self.time, 'summary': 'Convite fictício para continuar.',
            'opportunity_id': job['opportunity_id'], 'link_evidence': 'Empresa e processo conferidos no cenário.',
            'step_key': 'resposta', 'step_kind': 'email_reply'}
        message = self.call('email', data=email)
        self.say('O convite não informa o fuso do prazo. Vou registrar essa pendência.',
                 'Conferi no portal: o prazo é amanhã, às 17h de Brasília.')
        local_time = datetime.fromisoformat(self.time).astimezone(timezone(timedelta(hours=-3)))
        deadline = (local_time + timedelta(days=1)).replace(hour=17, minute=0, second=0).isoformat()
        repeated = self.call('email', data={**{key: value for key, value in email.items() if key != 'step_kind'}, 'due_at': deadline})
        self.assertTrue(repeated['duplicate'])
        self.assertEqual(repeated['step_id'], message['step_id'])
        step = next(item for item in self.call('steps') if item['id'] == message['step_id'])
        self.assertEqual(datetime.fromisoformat(step['due_at']), datetime.fromisoformat(deadline))
        self.complete(read, evidence_source='destination_email')
        self.say('Chegou um convite fictício. Preparei uma resposta confirmando seu interesse.', 'Pode simular o envio desse texto.')
        reply = self.authorize('email_reply', channel={'provider': 'gmail', 'account': 'principal'},
            message={key: message[key] for key in ('provider', 'account', 'message_id')},
            reply={'recipient': 'message_sender', 'content_sha256': hashlib.sha256(b'Tenho interesse.').hexdigest(), 'summary': 'Interesse confirmado.'})
        self.complete(reply, evidence_source='destination_email')
        self.call('practice', 'choose', data={'decision': 'now'})
        self.assertEqual(self.call('practice', 'status')['session_id'], practice['session_id'])
        self.call('practice', 'advance', data=response)
        self.call('practice', 'finish', data={'session_id': practice['session_id'], 'report': 'Boa distinção entre conceito e credencial. Falta detalhar renovação.', 'next_steps': 'Ensaiar renovação com um exemplo fictício.'})
        offer = {'label': 'Proposta fictícia', 'regime': 'CLT', 'currency': 'BRL', 'gross_monthly': '6000',
            'paid_months': 12, 'guaranteed_extra_annual': '6000', 'variable_annual': '0', 'benefits_annual': '3000',
            'restricted_funds_annual': '0', 'taxes_annual': '5000', 'costs_annual': '1000', 'reserve_annual': '2000',
            'estimated_fields': ['taxes_annual']}
        first = self.call('offers', 'save', data=offer)
        second = self.call('offers', 'save', data={**offer, 'label': 'Alternativa fictícia', 'regime': 'PJ', 'gross_monthly': '8000', 'paid_months': 11})
        comparison = self.call('offers', 'compare', data={'ids': [first['offer']['id'], second['offer']['id']]})
        self.assertTrue(comparison['comparable'])
        self.assertIsNone(comparison['ranking'])
        self.say('Comparei os valores com as premissas que você informou. A decisão é sua.', 'Entendi. Pode encerrar esta simulação.')
        self.checkpoint('stopped', 'Percurso fictício concluído, com proposta comparada.', 'Nenhuma ação real foi executada.', False)
        final = self.call('stop')
        self.assertTrue(final['stopped'])
        self.assertEqual(self.call('status')['counts']['opportunities'], 1)
        self.assertEqual(self.call('status')['pending'], [])
        self.say('A simulação está pausada e o histórico está salvo.', 'Consegui emprego. Quero encerrar esta campanha.')
        closed = self.call('goal-complete', data={
            'goal_version': 1, 'outcome': 'hired', 'reason': 'Emprego confirmado no roteiro fictício.',
            'user_confirmation': 'Consegui emprego. Quero encerrar esta campanha.'})
        self.assertEqual(closed['status'], 'completed')
        self.next_day()
        returned = self.call('start', '--focus', 'search')
        self.assertEqual(returned['next_step'], 'campaign_completed')
        self.assertIn('encerrada', returned['message'])
        self.call('resume-work', success=False)
        self.assertEqual(self.call('start', '--focus', 'career')['next_step'], 'career_guidance')
        self.assertEqual(self.call('status')['counts']['opportunities'], 1)
        self.say(returned['message'], 'Quero iniciar outra campanha com o mesmo perfil.')
        self.call('goal', data={'summary': 'Nova busca fictícia', 'actions': ['research']}, success=False)
        new = self.call('goal', data={'summary': 'Nova busca fictícia', 'actions': ['research'],
                                     'user_confirmation': 'Quero iniciar outra campanha com o mesmo perfil.'})
        self.assertEqual(new['version'], 2)
        self.assertTrue(self.call('status')['control']['stopped'])
        self.call('resume-work')
        self.assertIsNone(self.call('status')['closed_goal'])
        self.assertEqual(self.call('status')['counts']['opportunities'], 1)


if __name__ == '__main__':
    unittest.main()
