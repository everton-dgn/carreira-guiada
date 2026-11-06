"""Workflow com dados sintéticos em diretório temporário; nenhuma rede ou navegador."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.job.profile import ACTIONS as PROFILE_ACTIONS, Profile
from scripts.job.resumes import ResumeManager
from scripts.job.workflow import ACTIONS, Workflow

TEMPLATE = Path(__file__).resolve().parents[1] / "templates/profile.json"
VACANCY = {"role": "Função sintética", "modality": "remote", "languages": [], "salary": {"min": 5000, "max": 6000, "currency": "BRL", "period": "month", "estimated": False}}


class Clock:
    def __init__(self):
        self.value = datetime.now(timezone.utc)

    def __call__(self):
        return self.value


def iso(value):
    return value.isoformat()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="job-workflow-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.clock = Clock()
        self.wf = Workflow(self.root, clock=self.clock)
        self.addCleanup(self.wf.close)

    def approve_profile(self, permissions=None):
        sections = json.loads(TEMPLATE.read_text())["sections"]
        sections["sources"] = {"urls": ["https://jobs.example.org/"]}
        sections["identity"] = {"name": "Pessoa de Teste", "email": "teste@example.invalid"}
        sections["preferences"].update(roles=["Função sintética"], modalities=["remote"], currencies=["BRL"])
        allowed = permissions or {"research": "allow", "apply": "allow", "email_trash": "allow", "email_reply": "allow", "assessment": "allow", "schedule": "allow"}
        sections["permissions"] = {**{a: "ask" for a in PROFILE_ACTIONS}, **allowed, "confirmed": [a for a, v in allowed.items() if v == "allow"]}
        sections["connections"] = {"accounts": [{"provider": "portal", "alias": "portal-teste", "address": "teste@example.invalid"}, {"provider": "gmail", "alias": "principal", "address": "teste@example.invalid"}]}
        profile = Profile(self.root)
        for name, data in sections.items():
            profile.save(name, data)
        return profile.approve(profile.get()["version"])

    def approved_resume(self):
        manager = ResumeManager(self.root)
        fact = manager.add_fact("Experiência sintética em testes", "candidate:resposta-chat", True)
        version = manager.approve(manager.draft("geral", "# Pessoa de Teste\n\nExperiência sintética em testes.", [fact["id"]])["id"])
        return version

    def ready(self, goal=None):
        self.approve_profile()
        self.wf.configure_goal(goal or {"summary": "Candidaturas sintéticas", "actions": ["research", "apply", "email_trash", "email_reply", "assessment", "schedule"]})
        for kind, provider, account in (("browser", "chrome", "portal-teste"), ("browser", "chrome", "public"), ("mail", "gmail", "principal")):
            self.wf.capability({"kind": kind, "provider": provider, "account": account, "status": "ready", "checked_at": iso(self.clock()), "evidence": "Ferramenta listou a sessão", "agent_provider": "claude"})
        job = self.wf.opportunity({"company": "Empresa Exemplo", "title": "Função sintética", "portal": "portal", "aliases": ["job:portal:abc", "url:https://portal.example.org/jobs/abc"], "identity_verified": True, "evidence": "Anúncio público conferido", "vacancy": VACANCY})
        return job["opportunity_id"], self.approved_resume()

    def apply(self, job_id, resume, **changes):
        payload = {"action": "apply", "owner": "chat:sessao", "generation": self.wf.state()["control"]["generation"], "opportunity_id": job_id, "channel": {"provider": "chrome", "account": "portal-teste"}, "resume_id": resume["id"], "resume_sha256": resume["sha256"]}
        payload.update(changes)
        return self.wf.authorize(payload)

    def done(self, action_id, outcome="confirmed", **changes):
        payload = {"owner": "chat:sessao", "generation": self.wf.state()["control"]["generation"], "outcome": outcome, "evidence": "Portal exibiu a candidatura na lista do candidato", "evidence_source": "destination_page", "checked_at": iso(self.clock())}
        payload.update(changes)
        return self.wf.complete(action_id, payload)

    def test_actions_match_profile_and_fresh_state_creates_nothing(self):
        self.assertEqual(ACTIONS, PROFILE_ACTIONS)
        state = self.wf.state()
        self.assertFalse(state["initialized"])
        self.assertEqual(state["control"]["generation"], 1)
        self.assertFalse((self.root / ".job").exists())
        self.assertNotIn("teste@example.invalid", json.dumps(state))

    def test_apply_confirmed_with_destination_evidence_and_duplicate_blocked(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume)
        with self.assertRaisesRegex(ValueError, "duplicata"):
            self.apply(job_id, resume)
        with self.assertRaisesRegex(ValueError, "relato"):
            self.done(action["action_id"], evidence_source="agent_report")
        result = self.done(action["action_id"])
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(self.done(action["action_id"])["duplicate"], True)
        job = self.wf._store.conn.execute("SELECT state, evidence FROM jobs WHERE id=?", (job_id,)).fetchone()
        self.assertEqual(job["state"], "confirmed")
        with self.assertRaisesRegex(ValueError, "já confirmada"):
            self.apply(job_id, resume)
        state = self.wf.state()
        self.assertEqual(state["counts"]["actions"], {"confirmed": 1})
        self.assertNotIn("teste@example.invalid", json.dumps(state))

    def test_uncertain_blocks_repeat_until_not_received_evidence(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume)
        self.done(action["action_id"], "uncertain", evidence="Página fechou antes da confirmação", evidence_source="agent_report")
        with self.assertRaisesRegex(ValueError, "incert"):
            self.apply(job_id, resume)
        with self.assertRaisesRegex(ValueError, "checked_at"):
            self.done(action["action_id"], "not_received", checked_at=None)
        self.done(action["action_id"], "not_received", evidence="Lista do portal não mostra a vaga")
        self.assertEqual(self.apply(job_id, resume)["status"], "authorized")

    def test_reregister_keeps_identity_and_uncertain_state(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume)
        self.done(action["action_id"], "uncertain", evidence="Resultado não observado", evidence_source="agent_report")
        updated = self.wf.opportunity({"company": "Empresa Exemplo", "title": "Função sintética", "portal": "portal", "aliases": ["job:portal:abc", "application:portal:xyz"], "vacancy": VACANCY})
        self.assertTrue(updated["identity_verified"])
        self.assertEqual(updated["opportunity_id"], job_id)
        self.assertEqual(updated["state"], "pending_verification")
        self.assertEqual(self.wf.state()["ledger"]["uncertain"], 1)
        with self.assertRaisesRegex(ValueError, "incerto"):
            self.apply(job_id, resume)

    def test_uncertain_search_does_not_block_other_portal(self):
        self.ready()
        base = {"action": "research", "source_url": "https://jobs.example.org/", "owner": "chat:sessao", "generation": 1, "channel": {"provider": "chrome", "account": "public"}}
        with self.assertRaisesRegex(ValueError, "scope_key"):
            self.wf.authorize(base)
        first = self.wf.authorize({**base, "scope_key": "portal-a:atendimento"})
        self.done(first["action_id"], "uncertain", evidence="Fonte indisponível", evidence_source="agent_report")
        second = self.wf.authorize({**base, "scope_key": "portal-b:atendimento"})
        self.assertEqual(second["status"], "authorized")

    def test_expired_authorization_becomes_uncertain(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume, lease_seconds=60)
        self.clock.value += timedelta(minutes=5)
        self.wf.capability({"kind": "browser", "provider": "chrome", "account": "portal-teste", "status": "ready", "checked_at": iso(self.clock()), "evidence": "Sessão observada"})
        with self.assertRaisesRegex(ValueError, "incert"):
            self.apply(job_id, resume)
        self.assertEqual(self.wf.state()["pending"][-1]["status"], "uncertain")
        self.assertEqual(action["status"], "authorized")

    def test_stop_revokes_and_old_owner_rejected_after_resume(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume)
        stopped = self.wf.stop()
        self.assertEqual(stopped["uncertain"], [action["action_id"]])
        with self.assertRaisesRegex(ValueError, "Parada"):
            self.apply(job_id, resume)
        with self.assertRaisesRegex(ValueError, "Parada"):
            self.done(action["action_id"])
        resumed = self.wf.resume()
        self.assertEqual(resumed["control"]["generation"], 2)
        self.assertEqual(resumed["uncertain"], [action["action_id"]])
        with self.assertRaisesRegex(ValueError, "geração antiga"):
            self.done(action["action_id"], generation=1)
        with self.assertRaisesRegex(ValueError, "geração antiga"):
            self.apply(job_id, resume, generation=1)
        self.assertEqual(self.done(action["action_id"])["status"], "confirmed")

    def test_other_owner_cannot_complete_authorized_action(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume)
        with self.assertRaisesRegex(ValueError, "owner"):
            self.done(action["action_id"], owner="chat:outra")

    def test_profile_resume_and_eligibility_checks(self):
        job_id, resume = self.ready()
        path = self.root / resume["paths"]["pdf"]
        original = path.read_bytes()
        path.write_bytes(original + b"%")
        with self.assertRaisesRegex(ValueError, "alterado"):
            self.apply(job_id, resume)
        path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "hash"):
            self.apply(job_id, resume, resume_sha256=hashlib.sha256(b"outro").hexdigest())
        other = self.wf.opportunity({"company": "Outra Empresa", "title": "Função sintética", "portal": "portal", "aliases": ["job:portal:def"], "identity_verified": True, "evidence": "Anúncio público conferido", "vacancy": {**VACANCY, "modality": "onsite"}})
        self.assertEqual(other["evaluation"]["decision"], "discarded")
        with self.assertRaisesRegex(ValueError, "elegibilidade"):
            self.apply(other["opportunity_id"], resume)
        Profile(self.root).answer("identity", "location", "Cidade fictícia")
        with self.assertRaisesRegex(ValueError, "perfil"):
            self.apply(job_id, resume)

    def test_ask_permission_requires_user_confirmation_and_runner_cannot(self):
        self.approve_profile({"research": "ask", "apply": "ask"})
        self.wf.configure_goal({"summary": "Pesquisa", "actions": ["research"]})
        self.wf.capability({"kind": "browser", "provider": "chrome", "account": "public", "status": "ready", "checked_at": iso(self.clock()), "evidence": "Navegador abriu página pública"})
        base = {"action": "research", "source_url": "https://jobs.example.org/", "owner": "chat:sessao", "generation": 1, "channel": {"provider": "chrome", "account": "public"}, "scope_key": "portal:funcao"}
        with self.assertRaisesRegex(ValueError, "confirmação"):
            self.wf.authorize(base)
        with self.assertRaisesRegex(ValueError, "owner"):
            self.wf.authorize({**base, "owner": "runner:abc", "user_confirmation": "Usuário disse sim"})
        self.assertEqual(self.wf.authorize({**base, "user_confirmation": "Usuário confirmou a pesquisa no chat"})["status"], "authorized")

    def test_capability_revocation_and_aliases(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume)
        revoked = self.wf.capability({"kind": "browser", "provider": "chrome", "account": "portal-teste", "status": "expired", "checked_at": iso(self.clock()), "evidence": "Portal pediu login novamente"})
        self.assertEqual(revoked["revoked_actions"], [action["action_id"]])
        self.done(action["action_id"], "not_received", evidence="Lista do portal não mostra a vaga")
        with self.assertRaisesRegex(ValueError, "capacidade"):
            self.apply(job_id, resume)
        with self.assertRaisesRegex(ValueError, "application"):
            self.wf.opportunity({"company": "X", "title": "Y", "portal": "portal", "aliases": ["application:portal:abc"], "vacancy": VACANCY})

    def test_goal_open_idempotent_and_incompatible_requires_replace(self):
        first = self.wf.configure_goal({"summary": "Aberto", "actions": ["research"]})
        self.assertIsNone(first["criteria"]["period_days"])
        self.assertTrue(self.wf.configure_goal({"summary": "Aberto", "actions": ["research"]})["unchanged"])
        with self.assertRaisesRegex(ValueError, "replace_version"):
            self.wf.configure_goal({"summary": "Outro", "actions": ["research", "apply"], "target_applications": 3})
        second = self.wf.configure_goal({"summary": "Outro", "actions": ["research", "apply"], "target_applications": 3, "replace_version": first["version"]})
        self.assertEqual(second["version"], 2)

    def test_target_counts_only_this_goal_and_current_eligibility(self):
        job_id, resume = self.ready({"summary": "Primeiro objetivo", "actions": ["apply"], "target_applications": 2})
        self.done(self.apply(job_id, resume)["action_id"], submitted_at=iso(self.clock()))
        self.assertEqual(self.wf.state()["progress"]["confirmed_applications"], 1)
        self.assertEqual(self.wf.state()["ledger"]["eligible_confirmed"], 1)
        profile = Profile(self.root)
        prefs = profile.get()["sections"]["preferences"]
        profile.save("preferences", {**prefs, "modalities": ["onsite"]})
        profile.approve(profile.get()["version"])
        self.assertEqual(self.wf.state()["progress"]["confirmed_applications"], 0)
        self.assertEqual(self.wf.state()["ledger"]["eligible_confirmed"], 0)
        profile.save("preferences", prefs)
        profile.approve(profile.get()["version"])
        self.wf.configure_goal({"summary": "Novo objetivo", "actions": ["apply"], "period_days": 30, "target_applications": 1, "replace_version": 1})
        self.assertEqual(self.wf.state()["progress"]["confirmed_applications"], 0)
    def test_email_duplicate_link_and_individual_cleanup(self):
        job_id, resume = self.ready()
        msg = {"provider": "gmail", "account": "principal", "message_id": "msg-alerta", "category": "job_alert", "received_at": iso(self.clock())}
        self.assertFalse(self.wf.ingest_email(msg)["duplicate"])
        self.assertTrue(self.wf.ingest_email(msg)["duplicate"])
        with self.assertRaisesRegex(ValueError, "categoria"):
            self.wf.ingest_email({**msg, "category": "newsletter"})
        trash = {"action": "email_trash", "owner": "chat:sessao", "generation": 1, "message": {k: msg[k] for k in ("provider", "account", "message_id")}}
        with self.assertRaisesRegex(ValueError, "categoria não autorizada"):
            self.wf.authorize(trash)
        self.wf.cleanup_rules({"categories": ["job_alert"], "user_confirmation": "Usuário autorizou mover alertas para a lixeira"})
        action = self.wf.authorize(trash)
        with self.assertRaisesRegex(ValueError, "duplicata"):
            self.wf.authorize({**trash, "scope_key": "outra-chave"})
        with self.assertRaisesRegex(ValueError, "lixeira"):
            self.done(action["action_id"], evidence="Mensagem removida", evidence_source="destination_email")
        self.assertEqual(self.done(action["action_id"], evidence="Mensagem aparece na lixeira", evidence_source="destination_email", destination="trash")["status"], "confirmed")
        with self.assertRaisesRegex(ValueError, "já tratada"):
            self.wf.authorize(trash)
        assessment = {"provider": "gmail", "account": "principal", "message_id": "msg-teste", "category": "assessment", "received_at": iso(self.clock()), "opportunity_id": job_id, "link_evidence": "Assunto cita a vaga registrada"}
        with self.assertRaisesRegex(ValueError, "step_key"):
            self.wf.ingest_email(assessment)
        linked = self.wf.ingest_email({**assessment, "step_key": "avaliacao-tecnica"})
        self.assertIsNotNone(linked["step_id"])
        self.wf.cleanup_rules({"categories": ["job_alert", "rejection"], "user_confirmation": "Usuário incluiu recusas"})
        rejection = {"provider": "gmail", "account": "principal", "message_id": "msg-recusa", "category": "rejection", "received_at": iso(self.clock()), "opportunity_id": job_id, "link_evidence": "Assunto cita a vaga registrada"}
        self.wf.ingest_email(rejection)
        with self.assertRaisesRegex(ValueError, "etapa pendente"):
            self.wf.authorize({**trash, "message": {k: rejection[k] for k in ("provider", "account", "message_id")}})

    def test_late_confirmation_without_submission_date_does_not_count_today(self):
        job_id, resume = self.ready({"summary": "Meta diária", "actions": ["apply"],
                                     "target_applications": 1, "period_days": 1})
        action = self.apply(job_id, resume)
        self.done(action['action_id'], 'uncertain')
        self.clock.value += timedelta(days=3)
        self.done(action['action_id'])
        state = self.wf.state()
        self.assertEqual(state['ledger']['confirmed'], 1)
        self.assertEqual(state['ledger']['confirmed_without_date'], 1)
        self.assertEqual(state['progress']['confirmed_applications'], 0)
        self.assertFalse(state['progress']['reached'])

    def test_verified_submission_date_is_distinct_from_late_check(self):
        job_id, resume = self.ready({"summary": "Meta diária", "actions": ["apply"],
                                     "target_applications": 1, "period_days": 1})
        action = self.apply(job_id, resume)
        sent = iso(self.clock())
        self.done(action['action_id'], 'uncertain')
        self.clock.value += timedelta(days=3)
        self.done(action['action_id'], submitted_at=sent)
        self.assertEqual(self.wf.state()['progress']['confirmed_applications'], 0)
        job = self.wf._store.conn.execute('SELECT confirmed_at FROM jobs WHERE id=?', (job_id,)).fetchone()
        self.assertEqual(job['confirmed_at'], datetime.fromisoformat(sent).date().isoformat())

    def test_submission_date_must_be_between_authorization_and_check(self):
        job_id, resume = self.ready()
        action = self.apply(job_id, resume)
        for moment in (self.clock() - timedelta(days=1), self.clock() + timedelta(days=1)):
            with self.assertRaisesRegex(ValueError, 'submitted_at'):
                self.done(action['action_id'], submitted_at=iso(moment))
        self.assertEqual(self.wf.state()['counts']['actions'], {'authorized': 1})

    def test_followup_respects_new_platform_block_and_destination(self):
        job_id, resume = self.ready()
        self.done(self.apply(job_id, resume)['action_id'])
        self.wf._writer().upsert_step({'job_id': job_id, 'step_key': 'teste', 'kind': 'assessment'})
        profile = Profile(self.root)
        base = {'action': 'assessment', 'owner': 'chat:sessao', 'generation': 1,
                'opportunity_id': job_id, 'step_key': 'teste',
                'channel': {'provider': 'chrome', 'account': 'portal-teste'},
                'user_confirmation': 'Pessoa aprovou ajuda neste teste',
                'assistance_rules': 'O teste permite consulta'}
        profile.answer('preferences', 'blocked_platforms', ['portal'])
        profile.approve(profile.get()['version'])
        with self.assertRaisesRegex(ValueError, 'Bloqueio'):
            self.wf.authorize(base)
        profile.answer('preferences', 'blocked_platforms', ['teste.example'])
        profile.approve(profile.get()['version'])
        with self.assertRaisesRegex(ValueError, 'destination_platform'):
            self.wf.authorize(base)
        with self.assertRaisesRegex(ValueError, 'Bloqueio'):
            self.wf.authorize({**base, 'destination_platform': 'TESTE.EXAMPLE'})
        self.assertEqual(self.wf.state()['counts']['actions'], {'confirmed': 1})
        result = self.wf.authorize({**base, 'destination_platform': 'permitido.example'})
        self.assertEqual(result['status'], 'authorized')

    def test_fill_requires_and_records_approved_resume(self):
        job_id, resume = self.ready({'summary': 'Preencher com versão aprovada', 'actions': ['fill']})
        base = {'action': 'fill', 'owner': 'chat:sessao', 'generation': 1,
                'opportunity_id': job_id, 'channel': {'provider': 'chrome', 'account': 'portal-teste'},
                'user_confirmation': 'Pessoa autorizou o preenchimento'}
        with self.assertRaisesRegex(ValueError, 'currículo'):
            self.wf.authorize(base)
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.wf.authorize({**base, 'resume_id': resume['id'], 'resume_sha256': '0' * 64})
        result = self.wf.authorize({**base, 'resume_id': resume['id'], 'resume_sha256': resume['sha256']})
        row = self.wf._store.conn.execute('SELECT resume_id,resume_sha256 FROM wf_actions WHERE id=?', (result['action_id'],)).fetchone()
        self.assertEqual(row['resume_id'], resume['id'])
        self.assertEqual(row['resume_sha256'], resume['sha256'])

    def test_browser_session_does_not_require_an_email_account(self):
        job_id, resume = self.ready({'summary': 'Formulário sem e-mail conectado', 'actions': ['fill']})
        profile = Profile(self.root)
        profile.answer('connections', 'accounts', [])
        version = profile.get()['version']
        profile.approve(version)
        payload = {'action': 'fill', 'owner': 'chat:sessao', 'generation': 1,
                   'opportunity_id': job_id, 'channel': {'provider': 'chrome', 'account': 'public'},
                   'resume_id': resume['id'], 'resume_sha256': resume['sha256'],
                   'user_confirmation': 'Pessoa confirmou preencher o formulário público'}
        result = self.wf.authorize(payload)
        self.assertEqual(result['status'], 'authorized')
        self.assertEqual(profile.get()['approved_version'], version)
        self.wf.capability({'kind': 'browser', 'provider': 'chrome', 'account': 'public',
                            'status': 'unavailable', 'checked_at': iso(self.clock()),
                            'evidence': 'Ferramenta deixou de responder'})
        self.done(result['action_id'], 'not_received')
        with self.assertRaisesRegex(ValueError, 'capacidade'):
            self.wf.authorize(payload)

    def test_reply_schedule_assessment_need_per_item_conditions(self):
        job_id, resume = self.ready()
        msg = {"provider": "gmail", "account": "principal", "message_id": "msg-recrutadora", "category": "recruiter_contact", "received_at": iso(self.clock()), "opportunity_id": job_id, "link_evidence": "Assunto cita a vaga registrada"}
        self.wf.ingest_email(msg)
        reply = {"action": "email_reply", "owner": "chat:sessao", "generation": 1, "message": {k: msg[k] for k in ("provider", "account", "message_id")}}
        with self.assertRaisesRegex(ValueError, "confirmação"):
            self.wf.authorize(reply)
        with self.assertRaisesRegex(ValueError, "reply"):
            self.wf.authorize({**reply, "user_confirmation": "Usuário aprovou o texto"})
        details = {"recipient": "message_sender", "content_sha256": hashlib.sha256(b"texto aprovado").hexdigest(), "summary": "Agradece e confirma interesse"}
        self.assertEqual(self.wf.authorize({**reply, "user_confirmation": "Usuário aprovou o texto e o destinatário", "reply": details})["status"], "authorized")
        action = self.apply(job_id, resume)
        self.done(action["action_id"])
        self.wf.ingest_email({"provider": "gmail", "account": "principal", "message_id": "msg-teste", "category": "assessment", "received_at": iso(self.clock()), "opportunity_id": job_id, "link_evidence": "Assunto cita a vaga registrada", "step_key": "avaliacao-tecnica"})
        base = {"action": "assessment", "owner": "chat:sessao", "generation": 1, "opportunity_id": job_id, "step_key": "avaliacao-tecnica", "channel": {"provider": "chrome", "account": "portal-teste"}, "user_confirmation": "Usuário pediu ajuda nesta avaliação"}
        with self.assertRaisesRegex(ValueError, "assistance_rules"):
            self.wf.authorize(base)
        self.assertEqual(self.wf.authorize({**base, "assistance_rules": "Enunciado permite consulta e ferramentas"})["status"], "authorized")

    def test_repeated_mail_for_same_reply_step_is_completed_once(self):
        job_id, _ = self.ready()
        refs = []
        for message_id in ("msg-primeira", "msg-lembrete"):
            message = {"provider": "gmail", "account": "principal", "message_id": message_id,
                       "category": "recruiter_contact", "received_at": iso(self.clock()),
                       "opportunity_id": job_id, "link_evidence": "Mesmo pedido de resposta confirmado",
                       "step_key": "responder-disponibilidade", "step_kind": "email_reply"}
            refs.append(self.wf.ingest_email(message))
        base = {"action": "email_reply", "owner": "chat:sessao", "generation": 1,
                "message": {k: refs[0][k] for k in ("provider", "account", "message_id")},
                "user_confirmation": "Usuário aprovou resposta e destinatário",
                "reply": {"recipient": "message_sender", "content_sha256": hashlib.sha256(b"resposta").hexdigest(), "summary": "Informa disponibilidade"}}
        action = self.wf.authorize(base)
        self.done(action["action_id"], evidence_source="destination_email")
        row = self.wf._store.conn.execute("SELECT state FROM steps WHERE id=?", (refs[0]["step_id"],)).fetchone()
        self.assertEqual(row["state"], "completed")
        with self.assertRaisesRegex(ValueError, "duplicata"):
            self.wf.authorize({**base, "message": {k: refs[1][k] for k in ("provider", "account", "message_id")}})


if __name__ == "__main__":
    unittest.main()
