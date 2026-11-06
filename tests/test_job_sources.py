import unittest
from scripts.job.sources import normalize_url, research_target


class SourceTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_url('https://JOBS.example.org:443/jobs?q=remote'), 'https://jobs.example.org/jobs?q=remote')

    def test_unsafe_urls(self):
        for url in ['http://jobs.example.org', 'https://localhost', 'https://127.0.0.1', 'https://[::1]', 'https://a.local', 'https://user:pass@example.org', 'https://example.org/#token', 'https://example.org/?token=secret', 'https://example.org/%2e%2e/private', 'https://example.org/../private']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_url(url)

    def test_boundaries(self):
        sources = ['https://jobs.example.org/jobs']
        self.assertEqual(research_target('https://jobs.example.org/jobs/open?q=remote', sources), 'https://jobs.example.org/jobs/open?q=remote')
        for target in ['https://jobs.example.org/jobs-other', 'https://jobs.example.org.example.net/jobs', 'https://jobs.example.org:444/jobs', 'https://other.example.org/jobs']:
            with self.subTest(target=target), self.assertRaises(ValueError):
                research_target(target, sources)
        with self.assertRaises(ValueError):
            research_target('https://jobs.example.org/', [])

class SourceProfileTests(unittest.TestCase):
    def test_defer_resume_and_old_profile(self):
        import tempfile
        import json
        from pathlib import Path
        from scripts.job.profile import Profile
        with tempfile.TemporaryDirectory() as directory:
            profile = Profile(Path(directory).resolve())
            sections = json.loads((Path(__file__).resolve().parents[1] / 'templates/profile.json').read_text())['sections']
            sections['identity'] = {'name': 'Pessoa fictícia', 'email': 'person@example.org'}
            sections['preferences'].update(roles=['Atendimento'], modalities=['remote'], currencies=['BRL'])
            for section, data in sections.items():
                if section != 'sources': profile.save(section, data)
            self.assertEqual(profile.status()['next_section'], 'sources')
            self.assertEqual(profile.status()['questions'][0]['question'], 'Você já tem sites onde quer procurar vagas ou quer ajuda para encontrar opções?')
            with self.assertRaises(ValueError): profile.answer('sources', 'urls', ['javascript:alert(1)'])
            profile.answer('sources', 'urls', [])
            profile.approve(profile.get()['version'])
            self.assertTrue(profile.status()['approved'])
            profile.answer('sources', 'urls', ['https://JOBS.example.org/jobs'])
            self.assertFalse(profile.status()['approved'])
            permissions = sections['permissions']
            permissions['email_read'] = 'deny'
            profile.save('permissions', permissions)
            self.assertEqual(profile.get()['sections']['sources']['urls'], ['https://jobs.example.org/jobs'])
