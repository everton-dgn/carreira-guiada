"""CLI integration through separate processes, using only synthetic data."""
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="job-cli-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def call(self, *args, data=None, raw=None, success=True):
        result = subprocess.run(
            [sys.executable, "-m", "scripts.job.cli", "--root", str(self.root), *args, "--json"],
            input=json.dumps(data) if data is not None else raw,
            text=True, capture_output=True, cwd=PROJECT, timeout=15,
        )
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_empty_read_commands_do_not_create_candidate_data(self):
        self.assertEqual(self.call("start")["next_step"], "curriculum_input")
        self.assertFalse(self.call("start")["automatic_execution_started"])
        for args in (("profile", "show"), ("profile", "status"), ("resume", "list"),
                     ("resume", "facts"), ("status",), ("doctor",), ("context",)):
            self.call(*args)
        self.assertFalse((self.root / ".job").exists())

    def test_search_focus_prepares_sources_without_requiring_a_resume(self):
        from scripts.job.profile import Profile
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'identity')
        self.assertFalse((self.root / '.job').exists())
        profile = Profile(self.root)
        sections = json.loads((PROJECT / 'templates/profile.json').read_text())['sections']
        sections['identity'] = {'name': 'Pessoa Exemplo', 'email': 'pessoa@example.invalid'}
        sections['preferences'].update(roles=['Atendimento'], modalities=['remote'], currencies=['BRL'])
        sections['permissions']['confirmed'] = list(sections['permissions'].keys() - {'confirmed'})
        for section, value in sections.items():
            profile.save(section, value)
        profile.approve(profile.get()['version'])
        self.assertEqual(self.call('start', '--focus', 'search')['next_step'], 'sources')
        profile.answer('sources', 'urls', ['https://carreiras.example/vagas'])
        profile.approve(profile.get()['version'])
        result = self.call('start', '--focus', 'search')
        self.assertEqual(result['next_step'], 'execution_readiness')
        self.assertEqual(result['approved_resumes'], [])
        self.assertFalse(result['automatic_execution_started'])
        self.assertEqual(self.call('start')['next_step'], 'resume_approval')

    def test_restart_and_rejected_input_preserve_answers(self):
        self.call("profile", "save", "identity", data={"name": "Pessoa fictícia"})
        questions = self.call("profile", "status")["questions"]
        self.assertEqual([q["field"] for q in questions], ["email"])
        before = self.call("profile", "show")
        self.call("profile", "save", "identity", raw="{invalid", success=False)
        self.call("profile", "save", "identity", data={"email": "invalid"}, success=False)
        self.assertEqual(before, self.call("profile", "show"))

    def test_end_to_end_profile_and_resume_preparation(self):
        sections = json.loads((PROJECT / "templates/profile.json").read_text())["sections"]
        sections["identity"] = {"name": "Pessoa fictícia", "email": "pessoa@example.invalid"}
        sections["preferences"].update(roles=["Atendimento"], modalities=["remoto"], currencies=["BRL"])
        for section, value in sections.items():
            self.call("profile", "save", section, data=value)
        status = self.call("profile", "status")
        self.assertFalse(status["approved"])
        self.assertEqual(self.call("start")["next_step"], "profile_approval")
        self.call("profile", "approve", "--version", str(status["version"]))
        self.assertEqual(self.call("start")["next_step"], "resume_approval")
        fact = self.call("resume", "fact", data={"text": "Atendimento ao público.", "source": "candidate:resposta-experiencia", "confirmed": True})
        draft = self.call("resume", "draft", data={"label": "Atendimento", "markdown": "# Pessoa fictícia\n\n## Experiência\n\nAtendimento ao público.", "fact_ids": [fact["id"]]})
        self.call("resume", "approve", draft["id"])
        self.assertEqual(self.call('start')['next_step'], 'professional_presence')
        self.call('presence', 'choose', data={'decision': 'now', 'topics': ['linkedin'], 'confirmation': 'Quero revisar meu LinkedIn.'})
        self.call('presence', 'draft', data={'topic': 'linkedin', 'content': 'Atendimento ao público e organização de documentos, conforme fatos confirmados.', 'source': 'candidate_text'})
        self.assertEqual(self.call('presence', 'status')['next_topic'], 'linkedin')
        self.call('presence', 'finish', data={'topic': 'linkedin', 'version': 1, 'confirmation': 'Conferi as sugestões; vou aplicar depois.'})
        self.assertFalse(self.call('presence', 'status')['publication_authorized'])
        self.assertEqual(self.call('start')['next_step'], 'interview_preparation')
        self.call('practice', 'choose', data={'decision': 'later'})
        deferred = self.call("start")
        self.assertEqual(deferred["next_step"], "sources")
        self.assertEqual(deferred["question"]["field"], "urls")
        self.assertNotIn("[]", deferred["message"])
        self.call("profile", "answer", "sources", data={"field": "urls", "value": ["https://jobs.example.org/"]})
        self.call("profile", "approve", "--version", str(self.call("profile", "status")["version"]))
        self.assertEqual(self.call("start")["next_step"], "execution_readiness")
        self.assertFalse(self.call("start")["automatic_execution_started"])
        checked = self.call("resume", "show", draft["id"])
        for path in checked["paths"].values():
            self.assertTrue((self.root / path).is_file())
        self.call("profile", "save", "identity", data={**sections["identity"], "phone": "contato a confirmar"})
        self.assertFalse(self.call("profile", "status")["approved"])
        self.assertEqual(self.call("start")["next_step"], "profile_approval")

    def test_saved_checkpoint_and_tabs_are_visible_after_restart(self):
        self.assertIsNone(self.call('checkpoint', 'show'))
        self.assertEqual(self.call('tabs', 'status')['available'], 2)
        self.assertFalse((self.root / '.job').exists())
        self.call('checkpoint', 'save', data={'phase': 'waiting', 'summary': 'Formulário preservado na vaga fictícia.',
                                             'next_action': 'A pessoa precisa fazer login na aba aberta.', 'needs_user': True})
        state = self.call('status')
        self.assertTrue(state['checkpoint']['needs_user'])
        self.assertIn('Último ponto salvo', state['message'])
        self.assertEqual(state['browser']['limit'], 2)
        self.assertEqual(self.call('checkpoint', 'show')['phase'], 'waiting')

    def test_presence_fact_dependencies_survive_cli_restart(self):
        fact = self.call('resume', 'fact', data={'text': 'Experiência fictícia em atendimento.',
            'source': 'candidate:experiencia', 'confirmed': True})
        self.call('presence', 'choose', data={'decision': 'now', 'topics': ['linkedin'],
            'confirmation': 'Quero revisar este perfil.'})
        draft = {'topic': 'linkedin', 'content': 'Experiência fictícia em atendimento.',
            'source': 'candidate_text', 'fact_ids': [fact['id']]}
        self.call('presence', 'draft', data=draft)
        self.call('presence', 'finish', data={'topic': 'linkedin', 'version': 1,
            'confirmation': 'Conferi o texto.'})
        correction = self.call('resume', 'fact-replace', data={'fact_id': fact['id'],
            'text': 'Experiência fictícia em suporte.', 'source': 'candidate:correcao', 'confirmed': True})
        self.assertEqual(self.call('presence', 'status')['pending'], ['linkedin'])
        self.call('presence', 'draft', data=draft, success=False)
        draft.update(content='Experiência fictícia em suporte.', fact_ids=[correction['replacement']['id']])
        state = self.call('presence', 'draft', data=draft)
        version = state['reviews']['linkedin']['version']
        self.call('presence', 'finish', data={'topic': 'linkedin', 'version': version,
            'confirmation': 'Conferi a correção.'})
        review = self.call('presence', 'show')['reviews']['linkedin']
        self.assertEqual(review['fact_ids'], draft['fact_ids'])
        self.assertTrue(review['reviewed'])

    def test_launcher_resolves_project_when_called_from_elsewhere(self):
        result = subprocess.run([str(PROJECT / "job"), "--root", str(self.root), "start", "--json"],
                                cwd=self.root, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["next_step"], "curriculum_input")
        self.assertFalse((self.root / ".job").exists())

    def test_application_uncertainty_stop_and_resume_via_cli(self):
        sections = json.loads((PROJECT / "templates/profile.json").read_text())["sections"]
        sections["identity"] = {"name": "Pessoa fictícia", "email": "pessoa@example.invalid"}
        sections["preferences"].update(roles=["Atendimento"], modalities=["remoto"], currencies=["BRL"])
        sections["permissions"].update(apply="allow", confirmed=["apply"])
        sections["connections"] = {"accounts": [{"provider": "portal", "alias": "principal", "address": "pessoa@example.invalid"}]}
        for section, value in sections.items():
            self.call("profile", "save", section, data=value)
        self.call("profile", "approve", "--version", str(self.call("profile", "show")["version"]))
        fact = self.call("resume", "fact", data={"text": "Atendimento ao público.", "source": "candidate:experiencia", "confirmed": True})
        draft = self.call("resume", "draft", data={"label": "Geral", "markdown": "# Pessoa fictícia\n\nAtendimento ao público.", "fact_ids": [fact["id"]]})
        resume = self.call("resume", "approve", draft["id"])
        self.call("goal", data={"summary": "Envios compatíveis", "actions": ["apply"]})
        self.call("capability", data={"kind": "browser", "provider": "chrome", "account": "principal", "status": "ready", "checked_at": datetime.now(timezone.utc).isoformat(), "evidence": "Sessão fictícia verificada"})
        job = self.call("opportunity", data={"company": "Empresa fictícia", "title": "Atendimento", "portal": "portal", "aliases": ["job:portal:abc"], "identity_verified": True, "evidence": "Anúncio fictício conferido", "vacancy": {"role": "Atendimento", "modality": "remoto", "languages": [], "salary": None}})
        # Explicitly allow missing salary for this scenario and approve the changed version.
        preferences = sections["preferences"]
        preferences["salary"]["missing"] = "accept"
        self.call("profile", "save", "preferences", data=preferences)
        self.call("profile", "approve", "--version", str(self.call("profile", "show")["version"]))
        intent = {"action": "apply", "owner": "chat:teste", "generation": 1, "channel": {"provider": "chrome", "account": "principal"}, "opportunity_id": job["opportunity_id"], "resume_id": resume["id"], "resume_sha256": resume["sha256"]}
        action = self.call("action", "authorize", data=intent)
        self.assertTrue(self.call("stop")["stopped"])
        self.call("action", "authorize", data=intent, success=False)
        resumed = self.call("resume-work")
        self.assertEqual(resumed["control"]["generation"], 2)
        result = {"owner": "chat:teste", "generation": 1, "outcome": "confirmed", "evidence": "Portal fictício confirmou recebimento", "evidence_source": "destination_page", "checked_at": datetime.now(timezone.utc).isoformat()}
        self.call("action", "complete", action["action_id"], data=result, success=False)
        self.call("action", "complete", action["action_id"], data={**result, "generation": 2})
        self.call("action", "authorize", data={**intent, "generation": 2}, success=False)
        self.assertEqual(self.call("status")["counts"]["actions"], {"confirmed": 1})


if __name__ == "__main__":
    unittest.main()
