"""Regression coverage for a novice guided through the real local onboarding."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.job.cli import onboarding
from scripts.job.doctor import doctor
from scripts.job.profile import ACTIONS, Profile

PROJECT = Path(__file__).resolve().parents[1]


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="job-novice-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.profile = Profile(self.root)

    def identity_and_preferences(self):
        sections = json.loads((PROJECT / "templates/profile.json").read_text())["sections"]
        self.profile.save("identity", {"name": "Marina Exemplo", "email": "marina@example.invalid"})
        preferences = sections["preferences"]
        preferences.update(roles=["Atendente"], modalities=["presencial"], currencies=["BRL"])
        self.profile.save("preferences", preferences)
        self.profile.answer("sources", "urls", [])

    def test_one_permission_does_not_skip_eight_unanswered_permissions(self):
        self.identity_and_preferences()
        self.profile.save("permissions", {"research": "allow", "confirmed": ["research"]})
        status = Profile(self.root).status()
        self.assertEqual(status["next_section"], "permissions")
        self.assertEqual([q["field"] for q in status["questions"]], list(ACTIONS[1:]))
        with self.assertRaises(ValueError):
            self.profile.approve(status["version"])

    def test_chat_is_automatic_and_no_supervisor_is_probed(self):
        self.identity_and_preferences()
        self.profile.save("permissions", {action: "ask" for action in ACTIONS})
        self.assertEqual(self.profile.status()["next_section"], "connections")
        calls = []
        report = doctor(self.root, which=lambda tool: calls.append(tool))
        self.assertEqual(calls, ["uv"])
        self.assertEqual({check["id"] for check in report["checks"]}, {"python", "uv"})
        self.assertNotIn("supervised", report["ready"])

    def test_answers_merge_and_invalid_input_does_not_lose_progress(self):
        self.profile.answer("identity", "name", "Marina Exemplo")
        before = self.profile.get()
        with self.assertRaises(ValueError):
            self.profile.answer("identity", "email", "marina sem arroba")
        self.assertEqual(before, self.profile.get())
        Profile(self.root).answer("identity", "email", "marina@example.invalid")
        self.assertEqual(self.profile.get()["sections"]["identity"]["name"], "Marina Exemplo")
        self.profile.answer("preferences", "salary.floors", [])
        self.profile.answer("preferences", "salary.missing", "accept")
        self.assertEqual(self.profile.get()["sections"]["preferences"]["salary"], {"floors": [], "missing": "accept", "range": "ask"})
        with self.assertRaises(ValueError):
            self.profile.answer("permissions", "apply", "allow")
        self.profile.answer("permissions", "apply", "allow", confirmed=True)
        self.assertEqual(self.profile.get()["sections"]["permissions"]["confirmed"], ["apply"])

    def test_no_resume_choice_and_skipped_answers_survive_restart(self):
        from scripts.job.intake import Intake
        intake = Intake(self.root)
        intake.choose("create")
        self.assertEqual(onboarding(self.root)["next_step"], "identity")
        self.profile.answer("identity", "name", "Marina Exemplo")
        self.profile.answer("identity", "email", "marina@example.invalid")
        self.assertEqual(onboarding(self.root)["next_step"], "curriculum_intake")
        intake.answer("education", "Ensino médio concluído em 2024 na Escola Exemplo.")
        intake.answer("experience", "Estou procurando meu primeiro emprego.")
        intake.answer("skills", None)
        state = Intake(self.root).status()
        self.assertEqual(state["question"]["field"], "languages")
        self.assertNotIn("skills", [q["field"] for q in state["questions"]])
        self.assertEqual(onboarding(self.root)["question"]["field"], "languages")

    def test_intake_rejects_unknown_fields_and_preserves_original_answer(self):
        from scripts.job.intake import Intake
        intake = Intake(self.root)
        intake.choose("create")
        intake.answer("education", "Ensino médio completo.")
        before = intake.get()
        with self.assertRaises(ValueError):
            intake.answer("password", "not-a-secret")
        self.assertEqual(before, intake.get())
        intake.answer("education", "Ensino médio em andamento.")
        self.assertEqual(intake.get()["answers"]["education"]["text"], "Ensino médio em andamento.")

    def test_email_refusal_does_not_ask_for_mail_account(self):
        self.identity_and_preferences()
        self.profile.save("permissions", {**{action: "ask" for action in ACTIONS}, "email_read": "deny"})
        self.assertIsNone(self.profile.status()["next_section"])
        self.assertEqual(self.profile.get()["sections"]["connections"], {"accounts": []})

    def test_corrected_cv_answer_retires_versions_using_the_old_fact(self):
        from scripts.job.intake import Intake
        from scripts.job.resumes import ResumeManager
        intake, resumes = Intake(self.root), ResumeManager(self.root)
        intake.choose('create')
        intake.answer('education', 'Curso concluído em 2021.')
        draft = resumes.draft('Geral', '# Currículo\n\nCurso concluído em 2021.', intake.status()['fact_ids'])
        resumes.approve(draft['id'])
        intake.answer('education', 'Curso concluído em 2020.')
        self.assertEqual(resumes.get(draft['id'])['status'], 'retired')
        with self.assertRaises(ValueError):
            resumes.approve(draft['id'])

    def test_empty_intake_is_read_only_and_runtime_has_no_external_executor(self):
        from scripts.job.intake import Intake
        from scripts.job.cli import parser
        from scripts.job.workflow import Workflow
        self.assertIsNone(Intake(self.root).status()['mode'])
        self.assertFalse((self.root / '.job').exists())
        self.assertNotIn('runner', parser().format_help())
        workflow = Workflow(self.root)
        self.addCleanup(workflow.close)
        with self.assertRaises(ValueError):
            workflow.authorize({'action': 'research', 'source_url': 'https://jobs.example.org/', 'owner': 'runner:old', 'generation': 1})


if __name__ == "__main__":
    unittest.main()
