"""Direct routes through isolated CLI processes, with fictional data."""
import unittest
import json
from tests import test_job_cli as cli

PROJECT = cli.PROJECT


class NavigationTests(unittest.TestCase):
    setUp = cli.CliTests.setUp
    call = cli.CliTests.call
    def test_menu_is_read_only_and_routes(self):
        """Numbers and accented names select routes without creating private state."""
        result = self.call('menu')
        self.assertEqual(len(result['choices']), 4)
        for selection, step in [('1', 'curriculum_input'), ('CURRÍCULO', 'curriculum_input'),
                                ('2', 'interview_preparation'), ('carreira', 'career_guidance'),
                                ('4', 'preferences')]:
            self.assertEqual(self.call('menu', '--choose', selection)['next_step'], step)
        self.assertIsNone(self.call('menu', '--choose', 'desconhecido')['selected'])
        self.assertIn('1. Currículo', self.call('start')['message'])
        self.assertFalse((self.root / '.job').exists())

    def test_missing_menu_choice_cannot_write_state(self):
        """An incomplete persistence request leaves a fresh installation untouched."""
        self.call('menu', '--remember', success=False)
        self.assertFalse((self.root / '.job').exists())

    def test_public_search_follows_only_explicitly_consented_source_paths(self):
        """Pagination and details need scoped consent without widening old grants."""
        from scripts.job.research_scope import ResearchScopes
        self.call('profile', 'answer', 'preferences', data={'field': 'roles', 'value': ['Atendimento']})
        self.call('profile', 'answer', 'preferences', data={'field': 'modalities', 'value': []})
        self.call('profile', 'answer', 'sources', data={'field': 'urls', 'value': ['https://vagas.example.invalid/vagas']})
        request = self.call('start', '--focus', 'search')['scope_request']
        scopes = ResearchScopes(self.root)
        legacy = scopes.grant({**{k: v for k, v in request.items() if k != 'url_policy'},
            'question': 'Ler somente esta página?', 'user_confirmation': 'Sim, somente esta página.'})
        check = {'scope_id': legacy['id'], 'expected_version': 1, 'purpose': 'job_search',
                 'target': legacy['target'], 'url': 'https://vagas.example.invalid/vagas/123'}
        self.assertFalse(scopes.check(check)['allowed'])
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_scope_confirmation')
        self.assertEqual(request['url_policy'], 'source_paths')
        scope = scopes.grant({**request, 'question': 'Consultar resultados e detalhes dentro destes caminhos?',
            'user_confirmation': 'Sim, inclua resultados, paginação e detalhes dentro dos caminhos indicados.'})
        check['scope_id'] = scope['id']
        for url in ('https://vagas.example.invalid/vagas/123', 'https://vagas.example.invalid/vagas?page=2&q=atendimento'):
            self.assertTrue(scopes.check({**check, 'url': url})['allowed'])
        for url in ('https://vagas.example.invalid/vagas-falsas', 'https://outro.example.invalid/vagas/123',
                    'https://vagas.example.invalid:444/vagas/123', 'https://vagas.example.invalid/conta'):
            self.assertFalse(scopes.check({**check, 'url': url})['allowed'])
        for url in ('https://vagas.example.invalid/vagas?token=privado', 'https://pessoa:senha@vagas.example.invalid/vagas',
                    'https://vagas.example.invalid/vagas/../conta', 'https://vagas.example.invalid/vagas/%2e%2e/conta'):
            with self.assertRaises(ValueError):
                scopes.check({**check, 'url': url})
        scopes.revoke({'scope_id': scope['id'], 'expected_version': 1})
        self.assertFalse(scopes.check(check)['allowed'])

    def test_remembered_choice_does_not_require_an_intake_answer(self):
        """A saved activity survives restart without changing a stop or checkpoint."""
        self.call('menu', '--choose', '1', '--remember')
        self.assertIn('currículo?', self.call('start')['message'])
        self.call('stop')
        before = self.call('checkpoint', 'show')
        self.call('menu', '--choose', '4', '--remember')
        self.assertEqual(self.call('start')['next_step'], 'preferences')
        self.assertTrue(self.call('status')['control']['stopped'])
        self.assertEqual(self.call('checkpoint', 'show'), before)
        self.assertFalse(self.call('profile', 'show')['sections'].get('permissions'))

    def test_curriculum_resume_and_switch(self):
        """Standalone CV preparation preserves saved work across activity changes."""
        self.call('checkpoint', 'save', data={'phase': 'company', 'summary': 'Análise guardada', 'next_action': 'Continuar análise', 'needs_user': True})
        before = self.call('checkpoint', 'show')
        self.call('intake', 'choose', data={'mode': 'create', 'route': 'curriculum'})
        for field in ('education', 'experience', 'skills', 'languages', 'extra'):
            self.assertEqual(self.call('start')['question']['field'], field)
            self.call('intake', 'answer', data={'field': field, 'text': 'Experiência fictícia em organização.'})
        self.assertEqual(self.call('checkpoint', 'show'), before)
        self.assertEqual(self.call('start')['next_step'], 'resume_approval')
        facts = self.call('intake', 'status')['fact_ids']
        draft = self.call('resume', 'draft', data={'label': 'Exemplo', 'markdown': '# Pessoa Exemplo\n\nExperiência fictícia em organização.', 'fact_ids': facts})
        self.call('resume', 'approve', draft['id'])
        self.assertEqual(self.call('start')['next_step'], 'curriculum_complete')
        self.assertEqual(self.call('start', '--focus', 'practice')['next_step'], 'interview_preparation')
        self.assertEqual(self.call('start', '--focus', 'career')['next_step'], 'career_guidance')
        self.call('intake', 'choose', data={'mode': 'create', 'route': 'prepare'})
        self.assertNotEqual(self.call('start')['next_step'], 'curriculum_complete')

    def test_search_consent_generation_and_revocation(self):
        """Filter changes, stopping and revocation invalidate public-search readiness."""
        self.call('profile', 'answer', 'preferences', data={'field': 'roles', 'value': ['Atendimento']})
        self.call('profile', 'answer', 'preferences', data={'field': 'modalities', 'value': ['remote']})
        self.call('profile', 'answer', 'sources', data={'field': 'urls', 'value': ['https://vagas.example.invalid/']})
        route = self.call('start', '--focus', 'search')
        self.assertEqual(route['next_step'], 'search_scope_confirmation')
        self.assertEqual(self.call('research-scope', 'list'), [])
        scope = self.call('research-scope', 'grant', data={**route['scope_request'], 'question': 'Buscar vagas públicas', 'user_confirmation': 'Autorizo esta busca.'})
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_ready')
        check = {'scope_id': scope['id'], 'expected_version': scope['version'], 'purpose': scope['purpose'],
                 'target': scope['target'], 'url': scope['urls'][0]}
        self.call('profile', 'answer', 'preferences', data={'field': 'roles', 'value': ['Organização']})
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_scope_confirmation')
        self.assertFalse(self.call('research-scope', 'check', data=check)['allowed'])
        self.call('profile', 'answer', 'preferences', data={'field': 'roles', 'value': ['Atendimento']})
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_ready')
        self.call('stop')
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_paused')
        self.call('resume-work')
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_scope_confirmation')
        self.call('research-scope', 'revoke', data={'scope_id': scope['id'], 'expected_version': scope['version']})
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_scope_confirmation')

    def test_switch_from_curriculum_to_career_and_practice_preserves_checkpoint(self):
        """Optional activity changes preserve operational checkpoints and stop state."""
        self.call('checkpoint', 'save', data={'phase': 'company', 'summary': 'Guardado', 'next_action': 'Continuar', 'needs_user': True})
        before = self.call('checkpoint', 'show')
        self.call('intake', 'choose', data={'mode': 'create', 'route': 'curriculum'})
        self.call('career', 'start', data={})
        self.call('stop')
        self.assertEqual(self.call('start')['next_step'], 'career_guidance')
        self.assertTrue(self.call('status')['control']['stopped'])
        self.call('practice', 'choose', data={'decision': 'now'})
        self.assertEqual(self.call('start')['next_step'], 'interview_preparation')
        self.assertEqual(self.call('checkpoint', 'show'), before)
        self.assertTrue(self.call('status')['control']['stopped'])

    def test_existing_authorized_campaign_search(self):
        """An approved campaign retains its research permissions and stop controls."""
        sections = json.loads((PROJECT / 'templates/profile.json').read_text())['sections']
        sections['identity'] = {'name': 'Pessoa Exemplo', 'email': 'pessoa@example.invalid'}
        sections['preferences'].update(roles=['Atendimento'], modalities=['remote'], currencies=['BRL'])
        sections['sources']['urls'] = ['https://vagas.example.invalid/']
        sections['permissions']['research'] = 'allow'
        sections['permissions']['confirmed'] = list(sections['permissions'].keys() - {'confirmed'})
        for section, value in sections.items():
            self.call('profile', 'save', section, data=value)
        version = self.call('profile', 'show')['version']
        self.call('profile', 'approve', '--version', str(version))
        self.call('goal', data={'summary': 'Pesquisar vagas', 'actions': ['research']})
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'execution_readiness')
        self.call('stop')
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'search_paused')

    def test_switching_does_not_change_uncertain_application(self):
        """Menu navigation must never clear an uncertain send or permit a duplicate."""
        from tests.test_job_workflow import WorkflowTests
        fixture = WorkflowTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        job, resume = fixture.ready()
        action = fixture.apply(job, resume)
        fixture.done(action['action_id'], outcome='uncertain', evidence_source='agent_report')
        before = fixture.wf.show_action(action['action_id'])
        self.call('menu', '--choose', 'currículo')
        self.call('start', '--focus', 'practice')
        self.call('start', '--focus', 'career')
        self.assertEqual(fixture.wf.show_action(action['action_id']), before)
        with self.assertRaises(ValueError):
            fixture.apply(job, resume)
