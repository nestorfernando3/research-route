from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "research-route" / "scripts" / "route.py"


class RouteCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.project = Path(self.temporary_directory.name) / "paper"

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *arguments],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def init_project(self) -> None:
        result = self.run_cli(
            "init", str(self.project), "--title", "Test Paper", "--language", "en"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_init_copies_portable_template_and_sets_project_metadata(self):
        result = self.run_cli(
            "init",
            str(self.project),
            "--title",
            "Archives of Care",
            "--language",
            "es",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        route = (self.project / "ROUTE.md").read_text()
        self.assertIn('project_title: "Archives of Care"', route)
        self.assertIn('language: "es"', route)
        self.assertTrue((self.project / "manuscript" / "sections").is_dir())

    def test_init_refuses_nonempty_destination(self):
        self.project.mkdir()
        (self.project / "notes.md").write_text("mine")
        result = self.run_cli(
            "init", str(self.project), "--title", "X", "--language", "en"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.project / "notes.md").read_text(), "mine")
