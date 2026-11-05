import tempfile
import unittest
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from scripts.job.resumes import ResumeManager


CV = """# Pessoa de exemplo

## Resumo profissional

Profissional com experiência em atendimento e organização de documentos.

## Experiência profissional

### Empresa fictícia A

mar/2018 a jul/2021

- Organizou documentos e atendeu clientes.

### Empresa fictícia B

jan/2017 a dez/2018

## Formação

Curso de exemplo concluído.
"""


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manager = ResumeManager(self.root)

    def draft(self, label="Atendimento"):
        fact = self.manager.add_fact("Atuação nas duas empresas em períodos simultâneos.", "candidate:resposta-1", True)
        return self.manager.draft(label, CV, [fact["id"]])

    def test_empty_status_does_not_create_private_data(self):
        self.assertEqual(self.manager.list(), [])
        self.assertEqual(self.manager.facts(), [])
        self.assertFalse((self.root / ".job").exists())

    def test_queries_do_not_mutate_existing_profile_database(self):
        from scripts.job.profile import Profile
        Profile(self.root.resolve()).save("identity", {"name": "Pessoa fictícia"})
        path = self.root / ".job/control.sqlite3"
        before = path.read_bytes()
        self.assertEqual(self.manager.list(), [])
        self.assertEqual(self.manager.facts(), [])
        self.assertEqual(self.manager.sources(), [])
        with self.assertRaises(ValueError):
            self.manager.get("ausente")
        self.assertEqual(path.read_bytes(), before)

    def test_three_formats_preserve_text_and_overlap(self):
        draft = self.draft()
        self.assertEqual(draft["status"], "draft")
        self.assertEqual(set(draft["paths"]), {"md", "pdf", "docx"})
        pdf_text = "\n".join(page.extract_text() for page in PdfReader(self.root / draft["paths"]["pdf"]).pages)
        document = Document(self.root / draft["paths"]["docx"])
        docx_text = "\n".join(p.text for p in document.paragraphs)
        for text in (pdf_text, docx_text):
            self.assertIn("mar/2018 a jul/2021", text)
            self.assertIn("jan/2017 a dez/2018", text)
            self.assertIn("Organizou documentos", text)
        approved = self.manager.approve(draft["id"])
        self.assertEqual(approved["status"], "approved")
        self.assertTrue(approved["approved_at"])

    def test_import_preserves_original_and_does_not_confirm_facts(self):
        original = self.root / "anexo.md"
        original.write_text(CV)
        imported = self.manager.import_file(original, "Original")
        self.assertEqual((self.root / imported["original_path"]).read_bytes(), original.read_bytes())
        self.assertFalse(imported["confirmed"])
        self.assertEqual(self.manager.facts(), [])
        self.assertEqual(self.manager.list(), [])
        fact = self.manager.add_fact("Trabalho na empresa fictícia A.", imported["id"], False)
        with self.assertRaisesRegex(ValueError, "não confirmado"):
            self.manager.draft("Em revisão", CV, [fact["id"]])

    def test_pdf_and_docx_import_are_readable(self):
        draft = self.draft()
        for fmt in ("pdf", "docx"):
            imported = self.manager.import_file(self.root / draft["paths"][fmt], fmt)
            self.assertIn("mar/2018 a jul/2021", imported["text"])
            self.assertFalse(imported["confirmed"])

    def test_approval_is_bound_to_exact_files(self):
        draft = self.draft()
        pdf = self.root / draft["paths"]["pdf"]
        pdf.write_bytes(pdf.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "alterado"):
            self.manager.approve(draft["id"])

    def test_new_approved_version_retires_only_same_label(self):
        first = self.manager.approve(self.draft()["id"])
        other = self.manager.approve(self.draft("Outra área")["id"])
        second = self.manager.approve(self.draft()["id"])
        self.assertEqual(self.manager.get(first["id"])["status"], "retired")
        self.assertEqual(self.manager.get(other["id"])["status"], "approved")
        self.assertEqual(self.manager.get(second["id"])["status"], "approved")

    def test_secret_and_invalid_provenance_rejected(self):
        with self.assertRaisesRegex(ValueError, "senhas"):
            self.manager.add_fact("token=example", "candidate:1", True)
        with self.assertRaisesRegex(ValueError, "Vincule"):
            self.manager.add_fact("Fato sem origem.", "arquivo-inexistente", True)
        with self.assertRaisesRegex(ValueError, "confirmação"):
            self.manager.add_fact("Fato.", "candidate:1", "true")

    def test_private_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            (self.root / ".job").symlink_to(other, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "simbólicos"):
                self.manager.list()
            self.assertEqual(list(Path(other).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
