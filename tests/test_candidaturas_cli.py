import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="candidaturas-cli-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "historico-candidaturas.md").write_text("""# Histórico
## Candidaturas confirmadas
| Empresa | Vaga | Portal | Data registrada | Evidência preservada |
|---|---|---|---|---|
| Exemplo | Frontend Sênior | Gupy | NAO_INFORMADO | gupy:123; portal confirmou o envio |
""", encoding="utf-8")
        (self.root / "portais-pendentes.md").write_text("""# Pendências
## Aguardando candidato
| Chave | Empresa | Cargo | Motivo | Próxima ação | Desde |
|---|---|---|---|---|---|
| linkedin:456 | Outra Empresa | React Sênior | autenticação | Entrar no portal | 2026-09-10 |
""", encoding="utf-8")
        (self.root / "vagas-arquivadas.md").write_text("# Arquivado\nTrilha antiga incompleta.\n", encoding="utf-8")

    def command(self, *args, payload=None):
        result = subprocess.run([sys.executable, "-m", "scripts.candidaturas.cli", "--root", str(self.root), *args], input=json.dumps(payload) if payload else None, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_sync_report_and_repeat(self):
        originals = {p.name:p.read_bytes() for p in self.root.glob("*.md")}
        first = self.command("sync")
        second = self.command("sync")
        self.assertEqual(first["summary"]["opportunities"], 2)
        self.assertEqual(second["summary"]["opportunities"], 2)
        self.assertEqual(self.command("report")["summary"]["confirmed"], 1)
        self.assertEqual(originals, {p.name:p.read_bytes() for p in self.root.glob("*.md")})

    def test_browser_observation_to_step_and_monitor(self):
        self.command("sync")
        job = self.command("jobs", "--search", "Exemplo")[0]
        self.command("step", payload={"job_id":job["id"], "step_key":"assessment-1", "kind":"personal_assessment", "summary":"Avaliação pessoal", "state":"candidate_pending"})
        self.assertEqual(len(self.command("steps")), 1)
        run = self.command("monitor", "begin")
        self.command("monitor", "account", "--run-id", run["run_id"], payload={"provider":"gmail", "account":"primary", "status":"partial", "note":"Consulta temática incompleta"})
        self.command("monitor", "finish", "--run-id", run["run_id"])
        self.assertEqual(self.command("report")["monitor"]["accounts"][0]["status"], "partial")

    def test_missing_source_does_not_replace_last_snapshot(self):
        self.command("sync")
        (self.root / "portais-pendentes.md").rename(self.root / "portais-preservados.md")
        result = subprocess.run([sys.executable, "-m", "scripts.candidaturas.cli", "--root", str(self.root), "sync"], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.command("report")["summary"]["opportunities"], 2)

    def test_malformed_source_preserves_last_snapshot(self):
        source = self.root / "historico-candidaturas.md"
        original = source.read_text(encoding="utf-8")
        self.command("sync")
        before = self.command("report")["summary"]
        malformed_documents = (
            original.replace("|---|---|---|---|---|", "|---|---|---|---|broken|"),
            original.replace("| Exemplo |", "| Exemplo | extra |"),
        )
        for document in malformed_documents:
            with self.subTest(document=document):
                source.write_text(document, encoding="utf-8")
                result = subprocess.run([sys.executable, "-m", "scripts.candidaturas.cli", "--root", str(self.root), "sync"], text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self.command("report")["summary"], before)

    def test_snapshot_removal_keeps_step_and_repeat_totals(self):
        self.command("sync")
        job = self.command("jobs", "--search", "Exemplo")[0]
        step = self.command("step", payload={"job_id": job["id"], "step_key": "assessment-1", "kind": "personal_assessment", "summary": "Responder avaliação pessoal", "state": "candidate_pending"})
        (self.root / "historico-candidaturas.md").write_text("# Histórico\nSem registros ativos.\n", encoding="utf-8")
        first = self.command("sync")["summary"]
        second = self.command("sync")["summary"]
        self.assertEqual(first, second)
        self.assertEqual(second["opportunities"], 1)
        self.assertEqual(second["confirmed"], 0)
        self.assertEqual(second["pending_steps"], 1)
        self.assertEqual(second["inactive_records"], 1)
        self.assertEqual(self.command("jobs", "--search", "Exemplo"), [])
        self.assertFalse(self.command("jobs", "--all", "--search", "Exemplo")[0]["active"])
        self.assertEqual(self.command("steps")[0]["id"], step["id"])


if __name__ == "__main__":
    unittest.main()
