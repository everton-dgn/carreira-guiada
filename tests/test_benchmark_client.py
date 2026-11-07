from pathlib import Path
import tempfile
import unittest

from scripts.maintainers.bench_client import create


class BenchmarkClientTests(unittest.TestCase):
    def test_fresh_client_is_portable_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            lab = root / 'lab'
            lab.mkdir()
            (lab / 'state.json').write_text('{}')
            client = root / 'client'
            create(lab, client)
            self.assertTrue((client / 'tools').stat().st_mode & 0o100)
            self.assertIn('GUIA.md', (lab / 'executor-prompts/fase-1.txt').read_text())
            self.assertIn('Voltei no dia seguinte', (lab / 'executor-prompts/fase-2.txt').read_text())
            self.assertFalse((client / 'fase-2.txt').exists())
            with self.assertRaises(FileExistsError):
                create(lab, client)

    def test_client_inside_git_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / '.git').mkdir()
            (root / 'state.json').write_text('{}')
            with self.assertRaises(ValueError):
                create(root, root / 'client')
            self.assertFalse((root / 'client').exists())
