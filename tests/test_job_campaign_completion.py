"""Campaign closure and task capabilities, using only temporary fictional state."""
import unittest
from datetime import timedelta
from scripts.job.cli import dispatch, parser
from scripts.job.doctor import doctor
from scripts.job.intake import Intake
from tests import test_job_workflow as fixtures


class CampaignCompletionTests(unittest.TestCase):
    def setUp(self):
        import socket
        from unittest.mock import patch
        fixtures.WorkflowTests.setUp(self)
        network = patch.object(socket.socket, 'connect', side_effect=AssertionError('Network disabled'))
        network.start()
        self.addCleanup(network.stop)
    approve_profile = fixtures.WorkflowTests.approve_profile
    approved_resume = fixtures.WorkflowTests.approved_resume
    ready = fixtures.WorkflowTests.ready
    apply = fixtures.WorkflowTests.apply
    done = fixtures.WorkflowTests.done

    def close_goal(self, **changes):
        return self.wf.complete_goal({'goal_version': 1, 'user_confirmation': 'Consegui emprego, encerre.',
                                     'reason': 'Pedido da pessoa', 'outcome': 'hired', **changes})

    def test_closed_campaign_survives_next_day_and_cannot_resume(self):
        job, resume = self.ready()
        action = self.apply(job, resume)
        closed = self.close_goal()
        self.assertEqual(closed['status'], 'completed')
        self.assertIsNone(closed['superseded_at'])
        self.assertFalse(self.wf.state()['control']['stopped'])
        self.assertEqual(self.wf.state()['counts']['actions'], {'uncertain': 1})
        generation = self.wf.state()['control']['generation']
        self.assertTrue(self.close_goal()['unchanged'])
        self.assertEqual(self.wf.state()['control']['generation'], generation)
        with self.assertRaises(ValueError):
            self.wf.check(action['action_id'], {'owner': 'chat:sessao', 'generation': generation})
        with self.assertRaises(ValueError):
            self.wf.resume()
        self.clock.value += timedelta(days=1)
        self.assertEqual(self.wf.state(focus='search')['session']['condition'], 'completed')
        for command in ('start', 'menu'):
            result = dispatch(parser().parse_args([command, '--root', str(self.root)]))
            self.assertIn('encerrada', result['message'])
            if command == 'menu':
                self.assertIn('1. Currículo', result['message'])
        with self.assertRaises(ValueError):
            self.wf.configure_goal({'summary': 'Nova', 'actions': ['apply']})
        new = self.wf.configure_goal({'summary': 'Nova', 'actions': ['apply'], 'user_confirmation': 'Quero uma nova campanha.'})
        self.assertEqual(new['version'], 2)
        with self.assertRaises(ValueError):
            self.apply(job, resume)
        self.assertEqual(self.wf.state()['counts']['actions'], {'uncertain': 1})

    def test_task_readiness_does_not_require_onboarding_or_claim_authentication(self):
        report = doctor(self.root, which=lambda _: None)
        self.assertIn('tasks', report)
        self.assertFalse(report['tasks']['applications']['authentication_verified'])
        for focus in ('curriculum', 'practice', 'career'):
            result = dispatch(parser().parse_args(['start', '--focus', focus, '--root', str(self.root)]))
            self.assertFalse(result['task_capabilities'][focus]['requires_authentication'])
        self.assertFalse((self.root / '.job').exists())

    def test_first_use_hint_stays_in_menu_without_repeating_each_question(self):
        """Keep capability guidance available without adding it to every answer."""
        menu = dispatch(parser().parse_args(['start', '--root', str(self.root)]))
        hint = 'Currículo, entrevistas e carreira podem começar no chat'
        self.assertIn(hint, menu['message'])
        curriculum = dispatch(parser().parse_args(['start', '--focus', 'curriculum', '--root', str(self.root)]))
        self.assertNotIn(hint, curriculum['message'])
        self.assertIn('curriculum', curriculum['task_capabilities'])

    def test_pause_next_day_and_activity_switch_preserve_campaign(self):
        self.ready()
        self.wf.stop()
        self.clock.value += timedelta(days=1)
        for route in ('curriculum', 'practice', 'career', 'search'):
            Intake(self.root).remember_route(route)
            result = dispatch(parser().parse_args(['start', '--root', str(self.root)]))
            self.assertEqual(result['session']['activity'], route)
            self.assertTrue(result['session']['campaign_stopped'])
        self.wf.resume()
        self.assertEqual(self.wf.state()['goal']['version'], 1)
        self.assertIsNone(self.wf.state()['closed_goal'])
        self.assertFalse(self.wf.state()['control']['stopped'])

    def test_capability_guidance_separates_missing_data_from_live_checks(self):
        unavailable = doctor(self.root, which=lambda _: None)
        for task in ('curriculum', 'practice', 'career'):
            self.assertFalse(unavailable['tasks'][task]['ready'])
            self.assertNotIn('Pode começar', unavailable['tasks'][task]['message'])
        self.ready()
        report = doctor(self.root, which=lambda _: None)
        self.assertNotIn('registered_account', report['tasks']['email']['missing'])
        self.assertIn('mail_live_check', report['tasks']['email']['verify_now'])
        self.assertNotIn('sources_and_scope_confirmation', report['tasks']['search']['missing'])
        self.assertIn('sources_and_scope_confirmation', report['tasks']['search']['verify_now'])

    def test_closure_preserves_uncertain_evidence_steps_and_pause(self):
        job, resume = self.ready()
        action = self.apply(job, resume)
        self.done(action['action_id'], 'uncertain', evidence='Resposta fictícia sem confirmação')
        step = self.wf._store.upsert_step({'job_id': job, 'step_key': 'fixture:interview',
                                         'kind': 'interview_attendance', 'state': 'candidate_pending',
                                         'summary': 'Entrevista fictícia'})
        before = dict(self.wf._store.conn.execute('SELECT * FROM wf_actions WHERE id=?', (action['action_id'],)).fetchone())
        self.wf.stop()
        self.close_goal(outcome='user_closed')
        after = dict(self.wf._store.conn.execute('SELECT * FROM wf_actions WHERE id=?', (action['action_id'],)).fetchone())
        self.assertEqual(before, after)
        self.assertTrue(self.wf.state()['control']['stopped'])
        self.assertEqual(self.wf.state(focus='search')['session']['condition'], 'completed')
        self.assertTrue(any(item.get('step_id') == step['id'] for item in self.wf.state()['pending']))
        self.assertIn('encerrada', self.wf.state(needs_user=True)['message'])
        with self.assertRaisesRegex(ValueError, 'encerrada'):
            self.wf.resume()
        self.wf.close()
        from scripts.job.workflow import Workflow
        reopened = Workflow(self.root, clock=self.clock)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.state()['closed_goal']['outcome'], 'user_closed')
        self.assertEqual(reopened.state()['counts']['actions'], {'uncertain': 1})

    def test_target_reached_is_not_hiring_or_closure(self):
        job, resume = self.ready({'summary': 'Uma candidatura', 'actions': ['apply'], 'target_applications': 1})
        self.done(self.apply(job, resume)['action_id'], submitted_at=fixtures.iso(self.clock()))
        state = self.wf.state()
        self.assertTrue(state['progress']['reached'])
        self.assertEqual(state['goal']['status'], 'active')
        self.assertIsNone(state['closed_goal'])

    def test_validation_and_idempotence_do_not_change_new_campaign(self):
        self.wf.configure_goal({'summary': 'Primeira', 'actions': ['research']})
        for changes in ({'goal_version': 2}, {'goal_version': True}, {'outcome': 'target_reached'},
                        {'user_confirmation': ''}, {'reason': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.close_goal(**changes)
        self.assertEqual(self.wf.state()['goal']['version'], 1)
        self.close_goal()
        with self.assertRaises(ValueError):
            self.close_goal(outcome='user_closed')
        new = self.wf.configure_goal({'summary': 'Segunda', 'actions': ['research'], 'user_confirmation': 'Quero iniciar outra campanha.'})
        generation = self.wf.state()['control']['generation']
        self.assertEqual(new['version'], 2)
        self.assertTrue(self.close_goal()['unchanged'])
        self.assertEqual(self.wf.state()['control']['generation'], generation)
        self.assertEqual(self.wf.state()['goal']['version'], 2)
        self.assertIsNone(self.wf.state()['closed_goal'])
        saved = dict(self.wf._store.conn.execute('SELECT * FROM wf_goal_starts').fetchone())
        self.assertEqual(saved['user_confirmation'], 'Quero iniciar outra campanha.')
        self.assertEqual(saved['generation'], generation)

    def test_legacy_schema_read_and_positional_writer_remain_compatible(self):
        self.wf.configure_goal({'summary': 'Legado', 'actions': ['research']})
        conn = self.wf._store.conn
        conn.execute('DROP TABLE wf_goal_completions')
        conn.execute('DROP TABLE wf_goal_starts')
        conn.commit()
        self.wf.close()
        from scripts.job.workflow import Workflow
        self.wf = Workflow(self.root, clock=self.clock)
        self.addCleanup(self.wf.close)
        self.assertIsNone(self.wf.state()['closed_goal'])
        self.assertEqual(self.wf.state()['goal']['version'], 1)
        self.close_goal()
        # A positional legacy writer still sees exactly the original seven columns.
        conn = self.wf._store.conn
        conn.execute("INSERT INTO wf_goals VALUES(2,'superseded','Legado inativo','{}',NULL,?,?)",
                     (fixtures.iso(self.clock()), fixtures.iso(self.clock())))
        conn.commit()
        self.assertEqual(self.wf.state()['closed_goal']['version'], 1)

    def test_saved_capability_never_proves_live_authentication(self):
        self.ready()
        report = doctor(self.root, which=lambda _: '/fixture/uv',
                        run=lambda *args, **kwargs: type('Result', (), {'returncode': 0, 'stdout': 'uv fixture'})())
        self.assertTrue(report['recorded_effect_prerequisites'])
        self.assertFalse(report['ready']['effects'])
        self.assertFalse(report['tasks']['applications']['authentication_verified'])
        self.assertTrue(any(item['usable'] for item in report['sessions']))

    def test_cli_completion_and_direct_routes_after_closure(self):
        import io
        import json
        from unittest.mock import patch
        self.ready()
        data = {'goal_version': 1, 'user_confirmation': 'Encerre a campanha.',
                'reason': 'Decisão pessoal', 'outcome': 'user_closed'}
        with patch('sys.stdin', io.StringIO(json.dumps(data))):
            closed = dispatch(parser().parse_args(['goal-complete', '--root', str(self.root)]))
        self.assertEqual(closed['status'], 'completed')
        for route, step in (('curriculum', 'curriculum_complete'), ('practice', 'interview_preparation'), ('career', 'career_guidance')):
            result = dispatch(parser().parse_args(['start', '--focus', route, '--root', str(self.root)]))
            self.assertEqual(result['next_step'], step)
            self.assertIn('encerrada', result['message'])
        Intake(self.root).remember_route('search')
        result = dispatch(parser().parse_args(['start', '--root', str(self.root)]))
        self.assertEqual(result['next_step'], 'campaign_completed')
        self.assertIsNone(result['welcome_back'])


    def test_generation_revokes_public_research_grants(self):
        from scripts.job.research_scope import ResearchScopes, job_search_target
        self.approve_profile()
        from scripts.job.profile import Profile
        sections = Profile(self.root).get()["sections"]
        target = job_search_target(sections["preferences"], sections["sources"]["urls"])
        self.wf.configure_goal({'summary': 'Busca fictícia', 'actions': ['research']})
        scopes = ResearchScopes(self.root)
        grant = scopes.grant({'purpose': 'job_search', 'target': target,
                              'urls': sections['sources']['urls'], 'question': 'Pesquisar?',
                              'user_confirmation': 'Sim, pesquisar.'})
        check = {'scope_id': grant['id'], 'expected_version': grant['version'],
                 'purpose': grant['purpose'], 'target': grant['target'], 'url': grant['urls'][0]}
        self.assertTrue(scopes.check(check)['allowed'])
        self.close_goal()
        self.assertFalse(scopes.check(check)['allowed'])
        self.wf.configure_goal({'summary': 'Nova busca', 'actions': ['research'],
                                'user_confirmation': 'Quero outra campanha.'})
        self.assertFalse(scopes.check(check)['allowed'])

    def test_explicit_public_search_after_closure_requires_fresh_scope(self):
        """Public browsing can be chosen without reopening applications."""
        from scripts.job.research_scope import ResearchScopes
        self.ready()
        self.close_goal()
        entry = dispatch(parser().parse_args(['menu', '--choose', '4', '--root', str(self.root)]))
        self.assertEqual(entry['next_step'], 'search_scope_confirmation')
        self.assertEqual(entry['session']['phase'], 'search_scope_confirmation')
        self.assertTrue(entry['session']['campaign_completed'])
        self.assertIn('encerrada', entry['message'])
        scopes = ResearchScopes(self.root)
        request = entry['scope_request']
        scopes.grant({**request, 'question': 'Pesquisar só nestes sites?',
                      'user_confirmation': 'Sim, quero apenas ver as vagas.'})
        ready = dispatch(parser().parse_args(['start', '--focus', 'search', '--root', str(self.root)]))
        self.assertEqual(ready['next_step'], 'search_ready')
        self.assertEqual(ready['session']['condition'], 'ready')
        self.assertIsNone(self.wf.state()['goal'])
        self.assertIsNotNone(self.wf.state()['closed_goal'])
        with self.assertRaisesRegex(ValueError, 'encerrada'):
            self.wf.resume()

    def test_public_search_after_closure_preserves_active_pause(self):
        """Choosing public search cannot clear a pause retained by completion."""
        from scripts.job.navigation import search
        from scripts.job.profile import Profile
        from scripts.job.research_scope import ResearchScopes, job_search_target
        self.ready()
        self.wf.stop()
        self.close_goal()
        entry = dispatch(parser().parse_args(['menu', '--choose', '4', '--root', str(self.root)]))
        self.assertNotEqual(entry['next_step'], 'search_ready')
        self.assertNotIn('scope_request', entry)
        self.assertTrue(entry['session']['campaign_completed'])
        self.assertTrue(self.wf.state()['control']['stopped'])
        self.assertIsNone(self.wf.state()['goal'])
        sections = Profile(self.root).get()['sections']
        self.assertEqual(search(self.root, sections)['next_step'], 'search_paused')
        with self.assertRaisesRegex(ValueError, 'Pesquisa parada'):
            ResearchScopes(self.root).grant({
                'purpose': 'job_search', 'target': job_search_target(sections['preferences'], sections['sources']['urls']),
                'urls': sections['sources']['urls'], 'question': 'Pesquisar só nestes sites?',
                'user_confirmation': 'Sim, quero apenas ver as vagas.'})

    def test_new_campaign_can_authorize_fresh_action_but_not_old_authorization(self):
        job, resume = self.ready()
        old = self.apply(job, resume)
        self.close_goal()
        self.wf.configure_goal({'summary': 'Nova campanha', 'actions': ['apply'],
                                'user_confirmation': 'Quero iniciar uma nova campanha.'})
        fresh = self.wf.opportunity({'company': 'Outra Empresa Exemplo', 'title': 'Função sintética',
            'portal': 'portal', 'aliases': ['job:portal:def'], 'identity_verified': True,
            'evidence': 'Anúncio fictício conferido', 'vacancy': fixtures.VACANCY})
        current = self.apply(fresh['opportunity_id'], resume)
        self.assertEqual(self.wf.show_action(current['action_id'])['goal_version'], 2)
        self.wf.check(current['action_id'], {'owner': 'chat:sessao', 'generation': current['generation']})
        with self.assertRaises(ValueError):
            self.wf.check(old['action_id'], {'owner': 'chat:sessao', 'generation': current['generation']})
