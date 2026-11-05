"""Check discovery and navigation of the shareable chat guide."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_skills_are_discoverable_and_identical_in_both_apps(self):
        skills = list((ROOT / ".agents/skills").glob("*/SKILL.md"))
        self.assertTrue(skills)
        self.assertTrue((ROOT / ".agents/skills/inicio/SKILL.md").is_file())
        for path in skills:
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                header = text.split("---", 2)[1]
                self.assertIn("name: " + path.parent.name, header)
                self.assertRegex(header, r"description: .+")
                mirror = ROOT / ".claude/skills" / path.parent.name / "SKILL.md"
                self.assertEqual(path.read_bytes(), mirror.read_bytes())

    def test_local_document_links_resolve(self):
        files = list(ROOT.glob("*.md"))
        for directory in ("docs", ".agents", ".claude"):
            files.extend((ROOT / directory).rglob("*.md"))
        for path in files:
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
                if target.startswith(("https://", "http://", "#")):
                    continue
                local = target.split("#")[0]
                with self.subTest(document=str(path.relative_to(ROOT)), target=target):
                    self.assertFalse(Path(local).is_absolute())
                    self.assertTrue((path.parent / local).resolve().exists())


if __name__ == "__main__":
    unittest.main()
