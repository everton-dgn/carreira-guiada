"""Regression checks for accidental publication of private files and staged content."""

from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
import zlib

from scripts.check_publication import check, content_problems, path_problem


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="job-publication-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def stage(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.git("add", "--", name)

    def test_private_paths_are_rejected_without_reading_content(self):
        for name in (".job/profile.json", "curriculo.pdf", "docs/resume.docx", ".env", "scripts/credentials.json", "docs/private.pem", ".claude/settings.local.json", "backup/data.md"):
            with self.subTest(name=name):
                self.assertIsNotNone(path_problem(name))

    def test_neutral_fixture_and_documentation_are_allowed(self):
        self.stage("README.md", "# Carreira Guiada\nA fictional contact: person@example.invalid\n")
        self.stage("tests/test_example.py", "VALUE = 'https://jobs.example/vagas'\n")
        count, findings = check(self.root)
        self.assertEqual(count, 2)
        self.assertEqual(findings, [])

    def test_staged_secret_is_detected_even_if_working_file_was_cleaned(self):
        self.stage("README.md", "ghp_" + "a" * 36)
        (self.root / "README.md").write_text("# Clean working copy")
        self.assertTrue(check(self.root)[1])

    def test_unstaged_private_content_is_not_read_as_published_content(self):
        self.stage("README.md", "# Public")
        (self.root / "README.md").write_text("ghp_" + "a" * 36)
        self.assertEqual(check(self.root)[1], [])

    def test_email_and_machine_paths_are_detected(self):
        for value in ("candidate" + "@" + "company.tld", "/Users/" + "example-person/project", "C:" + "\\Users\\example-person\\file", "C:" + "/Users/" + "example-person/file"):
            with self.subTest(value=value):
                self.assertTrue(content_problems("README.md", value.encode()))

    def test_symlink_is_blocked_without_following_it(self):
        (self.root / "README.md").symlink_to(self.root / "absent")
        self.git("add", "README.md")
        self.assertIn("link simbólico", check(self.root)[1][0][1])

    def test_credential_url_to_ip_is_detected(self):
        value = "https://" + "u:p@" + "127.0.0.1/x"
        self.assertTrue(content_problems("README.md", value.encode()))

    def test_additional_known_secret_shapes_are_blocked(self):
        values = ["-----BEGIN " + kind + "-----" for kind in ("ENCRYPTED PRIVATE KEY", "PGP PRIVATE KEY BLOCK")]
        values += [prefix + "a" * 40 for prefix in ("xoxb-", "sk_live_", "rk_live_")]
        values += ["AIza" + "a" * 35, "ASIA" + "A" * 16, "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 20]
        for value in values:
            with self.subTest(prefix=value[:5]):
                self.assertTrue(content_problems("README.md", value.encode()))

    def test_unexpected_binary_and_metadata_are_rejected(self):
        self.assertTrue(content_problems("docs/file.md", b"\x00binary"))
        self.assertTrue(content_problems("docs/assets/test.png", b"not png"))
        self.assertTrue(content_problems("docs/assets/test.gif", b"GIF89a"))

    def test_empty_index_is_not_a_successful_publication_check(self):
        self.assertTrue(check(self.root)[1])

    def test_unknown_png_metadata_is_blocked_and_reviewed_images_are_preserved(self):
        """Reject unknown image metadata while preserving reviewed banner assets."""
        assets = Path(__file__).resolve().parents[1] / "docs/assets"
        for name in ('carreira-guiada-automacao-banner.png', 'jornada-candidaturas-banner.png'):
            with self.subTest(name=name):
                original = (assets / name).read_bytes()
                self.assertEqual(content_problems('docs/assets/' + name, original), [])
                self.assertTrue(content_problems("docs/assets/other.png", original))
                kind, value = b"ruSt", b"synthetic extra data"
                chunk = struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value))
                changed = original[:-12] + chunk + original[-12:]
                self.assertTrue(content_problems('docs/assets/' + name, changed))

    def test_gif_loop_extension_cannot_carry_extra_metadata(self):
        """Reject extra GIF extension data while accepting the generated loop block."""
        assets = Path(__file__).resolve().parents[1] / "docs/assets"
        original = (assets / "menu-com-contexto.gif").read_bytes()
        expected = b"\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
        self.assertIn(expected, original)
        self.assertEqual(content_problems("docs/assets/menu-com-contexto.gif", original), [])
        injected = b"\x0bNETSCAPE2.0\x03\x01\x00\x00\x05hello\x00"
        self.assertTrue(content_problems("docs/assets/menu-com-contexto.gif", original.replace(expected, injected, 1)))


if __name__ == "__main__":
    unittest.main()
