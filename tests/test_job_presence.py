"""Private, optional profile reviews and safe resumption with fictional data."""
import tempfile
import unittest
from pathlib import Path

from scripts.job.cli import onboarding, render
from scripts.job.presence import Presence
from scripts.job.profile import Profile


class PresenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='job-presence-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.presence = Presence(self.root)

    def test_read_only_start_and_skip_survive_restart(self):
        self.assertIsNone(self.presence.status()['decision'])
        self.assertEqual(onboarding(self.root)['resume_options'], [])
        self.assertFalse((self.root / '.job').exists())
        self.presence.choose('later', [], 'Quero procurar vagas primeiro.')
        self.assertEqual(Presence(self.root).status()['decision'], 'later')
        self.assertEqual(onboarding(self.root)['resume_options'], ['continue', 'review'])

    def test_review_requires_choice_and_current_version(self):
        with self.assertRaises(ValueError):
            self.presence.draft('linkedin', 'Título profissional proposto.', 'candidate_text')
        self.presence.choose('now', ['linkedin', 'github'], 'Quero revisar os dois.')
        self.presence.source('linkedin', 'candidate_text')
        self.assertEqual(Presence(self.root).get()['reviews']['linkedin']['source'], 'candidate_text')
        with self.assertRaises(ValueError):
            self.presence.finish('linkedin', 0, 'Ainda não há sugestões.')
        self.presence.draft('linkedin', 'Título profissional proposto.', 'candidate_text')
        self.assertEqual(Presence(self.root).status()['next_topic'], 'linkedin')
        self.presence.finish('linkedin', 1, 'Conferi as sugestões.')
        self.assertEqual(self.presence.status()['next_topic'], 'github')
        self.presence.draft('linkedin', 'Título corrigido pela pessoa.', 'candidate_text')
        with self.assertRaises(ValueError):
            self.presence.finish('linkedin', 1, 'Aprovo a versão anterior.')
        self.assertFalse(self.presence.status()['publication_authorized'])
        self.assertNotIn('content', str(self.presence.status()))
        self.assertIn('Título corrigido', self.presence.get()['reviews']['linkedin']['content'])

    def test_sources_reject_credentials_tracking_and_unrelated_hosts(self):
        self.presence.choose('now', ['github'], 'Quero revisar o GitHub.')
        credential_url = 'https://' + 'person:example' + '@' + 'github.com/profile'
        for source in ('https://github.com.evil.example/profile', 'https://github.com/profile?token=example', 'http://github.com/profile', credential_url):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.presence.draft('github', 'Sugestões fictícias.', source)
        self.presence.draft('github', 'Sugestões fictícias.', 'https://github.com/example')
        self.assertEqual(self.presence.status()['reviews']['github']['version'], 1)
        self.assertEqual([p.name for p in self.root.iterdir()], ['.job'])

    def test_pasted_text_keeps_regional_link_and_review_history(self):
        self.presence.choose('now', ['linkedin'], 'Quero revisar o LinkedIn.')
        link = 'https://br.linkedin.com/in/pessoa-exemplo'
        self.presence.source('linkedin', link)
        self.presence.draft('linkedin', 'Sugestões baseadas no texto da pessoa.', 'candidate_text')
        self.presence.finish('linkedin', 1, 'Conferi as sugestões.')
        self.presence.source('linkedin', link)
        saved = Presence(self.root).get()['reviews']['linkedin']
        self.assertEqual(saved['link'], link)
        self.assertEqual(saved['source'], 'candidate_text')
        self.assertEqual(saved['version'], 1)
        self.assertTrue(saved['reviewed'])
        self.presence.draft('linkedin', 'Sugestões corrigidas.', 'candidate_text')
        state = self.presence.get()
        self.assertFalse(state['reviews']['linkedin']['reviewed'])
        self.assertEqual(state['history']['linkedin'][0], saved)
        self.assertEqual(state['reviews']['linkedin']['link'], link)
        with self.assertRaises(ValueError):
            self.presence.source('linkedin', 'https://linkedin.com.evil.example/in/person')

    def test_plain_start_shows_next_step_with_one_resume_question(self):
        Profile(self.root).answer('identity', 'name', 'Pessoa Exemplo')
        text = render(onboarding(self.root))
        self.assertIn('Próxima etapa: dados de contato.', text)
        self.assertEqual(text.count('?'), 1)

    def test_source_fallback_and_confirmations_survive_restart(self):
        self.presence.choose('now', ['linkedin'], 'Quero revisar o LinkedIn.')
        link = 'https://linkedin.com/in/pessoa-exemplo'
        self.presence.source('linkedin', link)
        self.presence.source('linkedin', 'candidate_text')
        saved = Presence(self.root).get()
        self.assertEqual(saved['confirmation'], 'Quero revisar o LinkedIn.')
        self.assertEqual(saved['reviews']['linkedin']['source'], 'candidate_text')
        self.assertEqual(saved['reviews']['linkedin']['link'], link)
        self.presence.draft('linkedin', 'Texto revisado.', link)
        self.presence.finish('linkedin', 1, 'Conferi a versão atual.')
        self.presence.source('linkedin', 'candidate_text')
        saved = Presence(self.root).get()['reviews']['linkedin']
        self.assertEqual(saved['source'], link)
        self.assertEqual(saved['confirmation'], 'Conferi a versão atual.')
        self.presence.draft('linkedin', 'Novo texto revisado.', 'candidate_text')
        self.assertNotIn('confirmation', self.presence.get()['reviews']['linkedin'])
        for invalid in ('https://linkedin.com:99999/in/person', 'https://linkedin.com:abc/in/person'):
            with self.subTest(url=invalid), self.assertRaisesRegex(ValueError, 'Use o link HTTPS'):
                self.presence.source('linkedin', invalid)

    def test_browser_budget_is_bounded_and_preserves_existing_mode(self):
        profile = Profile(self.root)
        for value in (0, 6, True, '2'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                profile.save('limits', {'mode': 'chat', 'browser_tabs': value})
        profile.save('limits', {'mode': 'chat', 'browser_tabs': 1})
        self.assertEqual(profile.get()['sections']['limits']['browser_tabs'], 1)
