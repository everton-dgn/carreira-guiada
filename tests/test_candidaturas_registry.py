"""Synthetic fixtures; no profile data or real mailbox messages."""

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from candidaturas.registry import canonical_public_url, read_registry, read_workspace, render_report
from candidaturas.store import Store


class RegistryTests(unittest.TestCase):
    def test_namespaced_legacy_ids_are_not_truncated(self):
        path = self.write("table.md", """## Em verificação
| Empresa | Cargo | Chave | Evidência |
| --- | --- | --- | --- |
| Exemplo | React Sênior | inhire:company:abc-123 | application_id 900000002; registro anterior |
""")
        record = read_registry(path)[0]
        self.assertIn("job:inhire:company:abc-123", record["aliases"])
        from scripts.candidaturas.store import Store
        store = Store(self.root / "ledger" / "control.sqlite3")
        store.import_records([record], "fixture")
        store.close()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="candidaturas-registry-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, filename, text):
        path = self.root / filename
        path.write_text(text, encoding="utf-8")
        return path

    def test_historical_table_ignores_detail_and_registration_date(self):
        path = self.write("historico-candidaturas.md", """## Candidaturas confirmadas
| Empresa | Vaga | Portal | Data registrada | Evidência preservada |
| --- | --- | --- | --- | --- |
| Exemplo A | Frontend Sênior | Gupy | 5 de setembro de 2026 | Confirmada no portal https://exemplo.gupy.io/jobs/123?utm_source=mail |

### Ficha: Exemplo A
Empresa: Exemplo A. Vaga: Frontend Sênior. gupy:123.
""")
        records = read_registry(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["state"], "confirmed")
        self.assertIsNone(records[0]["confirmed_at"])
        self.assertIn("job:gupy:123", records[0]["aliases"])
        self.assertTrue(records[0]["identity_verified"])
        self.assertIsNone(records[0]["eligible"])
        self.assertNotIn("utm_source", records[0]["evidence"])

    def test_explicit_send_date_and_stable_key_when_status_changes(self):
        header = "| Empresa | Cargo | Chave | Estado | Data do envio | Evidência |\n| --- | --- | --- | --- | --- | --- |\n"
        path = self.write("table.md", "## Candidaturas confirmadas\n" + header + "| Exemplo B | React Sênior | gupy:234 | confirmada | 5 de setembro de 2026 | Portal confirmou |")
        original = read_registry(path)[0]
        self.assertEqual(original["confirmed_at"], "2026-09-05")
        other = self.write("other.md", "## Em verificação\n" + header + "| Exemplo B | React Sênior | gupy:234 | resultado_incerto | 2026-09-06 | Portal confirmou |")
        self.assertEqual(original["source_key"].split(":", 1)[1], read_registry(other)[0]["source_key"].split(":", 1)[1])
        self.assertNotEqual(original["source_key"], read_registry(other)[0]["source_key"])

    def test_verified_markers_count_only_confirmed_compatible_send(self):
        path = self.write("historico-candidaturas.md", """## Candidaturas confirmadas
| Empresa | Vaga | Portal | Data registrada | Evidência preservada |
| --- | --- | --- | --- | --- |
| Exemplo B | React Sênior | Gupy | 2 de janeiro de 2000, 12:00 -0300 | gupy:234; portal confirmou; envio_comprovado=2000-01-02; elegibilidade_vigente=sim |
""")
        record = read_registry(path)[0]
        self.assertEqual(record["confirmed_at"], "2000-01-02")
        self.assertIs(record["eligible"], True)
        store = Store(self.root / "verified.sqlite3")
        self.addCleanup(store.close)
        store.import_records([record], "fixture")
        self.assertEqual(store.summary(since="2000-01-02", until="2000-01-02")["period_confirmed"], 1)

    def test_pending_sections_and_email_reminders(self):
        self.write("portais-pendentes.md", """## Em verificação
| Chave | Empresa | Cargo | Estado | Próxima ação | Desde |
| --- | --- | --- | --- | --- | --- |
| gupy:345 | Exemplo C | React Sênior | resultado_incerto | Conferir portal | 2026-09-05 |
## Aguardando candidato
| Chave | Empresa | Cargo | Motivo | Próxima ação | Desde |
| --- | --- | --- | --- | --- | --- |
| linkedin:456 | Exemplo D | React Sênior | Autenticação | Abrir sessão | 2026-09-05 |
## Bloqueios de triagem
| Chave | Empresa | Cargo | Motivo | Desde |
| --- | --- | --- | --- | --- |
| indeed:abc789 | Exemplo E | React Sênior | senioridade_nao_confirmada | 2026-09-05 |
## Lembretes de e-mail
| Mensagem | Processo ligado | Decisão | Disposição | Desde |
| --- | --- | --- | --- | --- |
| msg-local | gupy:345 | Verificar | Preservada | 2026-09-05 |
""")
        records, notes = read_workspace(self.root)
        self.assertEqual([row["state"] for row in records], ["pending_verification", "candidate_pending", "blocked"])
        self.assertTrue(any("Lembretes" in note for note in notes))
        self.assertTrue(any("incompleto" in note for note in notes))
        self.assertTrue(any("historico-candidaturas.md" in note for note in notes))

    def test_application_id_never_becomes_public_job_id(self):
        path = self.write("table.md", """## Em verificação
| Empresa | Cargo | Chave | Evidência |
| --- | --- | --- | --- |
| Exemplo F | Frontend Sênior | application:gupy:456 | https://exemplo.gupy.io/applications/456 |
""")
        record = read_registry(path)[0]
        self.assertEqual(record["aliases"], ["application:gupy:456"])
        self.assertFalse(record["identity_verified"])

    def test_does_not_confirm_unrelated_archive_table(self):
        path = self.write("vagas-arquivadas.md", """# Trilha antiga
| Empresa | Vaga | Chave | Estado | Evidência |
| --- | --- | --- | --- | --- |
| Exemplo G | React Sênior | gupy:567 | confirmada | Relato antigo |
""")
        self.assertEqual(read_registry(path)[0]["state"], "pending_verification")

    def test_rejects_secrets_and_spoofed_job_hosts(self):
        self.assertIsNone(canonical_public_url("https://jobs.example/jobs/1?access_token=private"))
        self.assertIsNone(canonical_public_url("https://user:password@jobs.example/jobs/1"))
        self.assertIsNone(canonical_public_url("http://jobs.example/jobs/1"))
        self.assertIsNone(canonical_public_url("https://jobs.example/invite/private"))
        self.assertEqual(canonical_public_url("https://br.indeed.com/viewjob?jk=abc123&utm_source=mail"), "https://br.indeed.com/viewjob?jk=abc123")
        path = self.write("table.md", """## Em verificação
| Empresa | Vaga | Chave | Evidência |
| --- | --- | --- | --- |
| Exemplo H | React Sênior | local-h | https://gupy.io.example/jobs/678 https://jobs.example/jobs/1?token=private |
""")
        record = read_registry(path)[0]
        self.assertFalse(record["identity_verified"])
        self.assertFalse(any(alias.startswith("job:gupy:") for alias in record["aliases"]))
        self.assertNotIn("token=private", record["evidence"])

    def test_conflicting_public_ids_are_not_joined(self):
        path = self.write("table.md", """## Candidaturas confirmadas
| Empresa | Vaga | Chave | Evidência |
| --- | --- | --- | --- |
| Exemplo I | React Sênior | gupy:111 | gupy:222 |
""")
        record = read_registry(path)[0]
        self.assertFalse(record["identity_verified"])
        self.assertFalse(any(alias.startswith("job:") for alias in record["aliases"]))

    def test_counting_caveat_affects_matching_company_only(self):
        self.write("historico-candidaturas.md", """## Candidaturas confirmadas
| Empresa | Vaga | Chave | Evidência |
| --- | --- | --- | --- |
| Exemplo J | React Sênior | gupy:901 | Portal confirmou |
| Exemplo K | React Sênior | gupy:902 | Portal confirmou |
""")
        self.write("portais-pendentes.md", """## Ressalvas de contagem
- Exemplo J: identidade da oportunidade exige conferência.
""")
        records, notes = read_workspace(self.root)
        self.assertFalse(records[0]["identity_verified"])
        self.assertTrue(records[1]["identity_verified"])
        self.assertTrue(any("ressalvas" in note for note in notes))

    def test_ignores_fenced_tables_and_handles_escaped_pipes(self):
        path = self.write("table.md", """```markdown
## Candidaturas confirmadas
| Empresa | Cargo | Chave |
| --- | --- | --- |
| Não importar | React | gupy:55 |
```
## Em verificação
| Empresa | Cargo | Chave |
| --- | --- | --- |
| Exemplo L | React \\| Next Sênior | gupy:66 |
""")
        records = read_registry(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "React | Next Sênior")

    def test_render_uses_computed_totals_and_no_mail_bodies(self):
        rendered = render_report(
            {"confirmed": 2, "pending_steps": 1, "notes": ["Cobertura incompleta"]},
            [{"company": "Exemplo M", "title": "React | Next", "state": "confirmada", "id": "opp-1"}],
            [{"company": "Exemplo M", "kind": "teste", "state": "pendente_candidato", "next_action": "Abrir portal", "body": "mensagem privada"}],
        )
        self.assertIn("| Candidaturas confirmadas | 2 |", rendered)
        self.assertIn("React \\| Next", rendered)
        self.assertIn("Cobertura incompleta", rendered)
        self.assertNotIn("mensagem privada", rendered)

    def test_registry_output_imports_into_store_and_preserves_next_action(self):
        path = self.write("portais-pendentes.md", """## Aguardando candidato
| Chave | Empresa | Cargo | Motivo | Próxima ação | Desde |
| --- | --- | --- | --- | --- | --- |
| inhire:abc-123 | Exemplo N | React Sênior | Autenticação | Conferir o portal; contato (00) 90000-0000 | 2026-09-05 |
""")
        records = read_registry(path)
        self.assertIsNone(records[0]["evidence"])
        self.assertEqual(records[0]["aliases"], ["job:inhire:abc-123"])
        self.assertTrue(any("Próxima ação: Conferir o portal" in note for note in records[0]["notes"]))
        self.assertFalse(any("90000-0000" in note for note in records[0]["notes"]))
        store = Store(self.root / "test.sqlite3")
        self.addCleanup(store.close)
        store.import_records(records, "workspace-markdown")
        store.import_records(records, "workspace-markdown")
        self.assertEqual(store.summary()["opportunities"], 1)

    def test_company_homepage_does_not_link_distinct_jobs(self):
        path = self.write("table.md", """## Em verificação
| Empresa | Vaga | Chave | Evidência |
| --- | --- | --- | --- |
| Exemplo O | React Sênior | gupy:890 | https://example.com/ https://linkedin.com/company/example |
""")
        self.assertEqual(read_registry(path)[0]["aliases"], ["job:gupy:890"])

    def test_malformed_job_tables_abort_workspace_import(self):
        header = "## Em verificação\n| Empresa | Cargo | Chave |\n"
        malformed = (
            header + "| --- | incompleto | --- |\n| Exemplo privado | React | gupy:77 |\n",
            header + "| --- | --- |\n| Exemplo privado | React | gupy:77 |\n",
            header.rstrip(),
            header + "| --- | --- | --- |\n| Exemplo privado | React | gupy:77 | dado-privado |\n",
            header + "| --- | --- | --- |\n| Exemplo privado | gupy:77 |\n",
        )
        for index, document in enumerate(malformed):
            with self.subTest(case=index):
                workspace = self.root / str(index)
                workspace.mkdir()
                (workspace / "historico-candidaturas.md").write_text("# Histórico\n", encoding="utf-8")
                (workspace / "portais-pendentes.md").write_text(document, encoding="utf-8")
                (workspace / "vagas-arquivadas.md").write_text("# Arquivo\n", encoding="utf-8")
                with self.assertRaises(ValueError) as caught:
                    read_workspace(workspace)
                error = str(caught.exception)
                self.assertIn("portais-pendentes.md", error)
                self.assertIn("linha", error)
                self.assertNotIn("Exemplo privado", error)
                self.assertNotIn("dado-privado", error)

    def test_legitimate_empty_and_non_job_tables_remain_importable(self):
        self.write("historico-candidaturas.md", """## Candidaturas confirmadas
| Empresa | Vaga | Evidência preservada |
| --- | --- | --- |

Nenhuma candidatura registrada.
""")
        self.write("portais-pendentes.md", """## Lembretes de e-mail
| Mensagem | Processo ligado | Decisão |
| separador | legado |
| msg-local | processo-local | preservar | referência adicional |

## Fichas
| Campo | Valor |
| separador incompleto |
| Empresa | Exemplo | Informação adicional |
""")
        self.write("vagas-arquivadas.md", "# Arquivo\nSem registros.\n")
        records, _ = read_workspace(self.root)
        self.assertEqual(records, [])

    def test_report_shows_store_step_summary_and_reason(self):
        path = self.write("table.md", """## Em verificação
| Empresa | Vaga | Chave |
| --- | --- | --- |
| Exemplo P | React Sênior | gupy:990 |
""")
        store = Store(self.root / "step-report.sqlite3")
        try:
            job_id = store.import_records(read_registry(path), "fixture")["job_ids"][0]
            store.upsert_step({
                "job_id": job_id, "step_key": "questionario-1", "kind": "complemento",
                "summary": "Completar questionário cadastral", "reason": "Confirmar disponibilidade",
                "state": "candidate_pending",
            })
            store.upsert_step({
                "job_id": job_id, "step_key": "teste-1", "kind": "teste",
                "reason": "Realizar avaliação no portal", "state": "candidate_pending",
            })
            rendered = render_report(store.summary(), store.list_jobs(), store.list_steps())
            self.assertIn("| Exemplo P | Completar questionário cadastral | candidate_pending | NAO_INFORMADO | Confirmar disponibilidade |", rendered)
            self.assertIn("| Exemplo P | teste | candidate_pending | NAO_INFORMADO | Realizar avaliação no portal |", rendered)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
