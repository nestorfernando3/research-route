from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "research-route" / "scripts" / "route.py"
SPEC = importlib.util.spec_from_file_location("research_route_cli", CLI)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load route CLI from {CLI}")
ROUTE_CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE_CLI)


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

    def test_init_refuses_symlink_to_empty_directory_without_touching_it(self):
        target = Path(self.temporary_directory.name) / "target"
        target.mkdir()
        self.project.symlink_to(target, target_is_directory=True)

        try:
            ROUTE_CLI.init_route(self.project, "Title", "en")
        except Exception as error:
            caught_error = error
        else:
            caught_error = None

        self.assertIsInstance(caught_error, FileExistsError)
        self.assertTrue(self.project.is_symlink())
        self.assertEqual(self.project.resolve(), target.resolve())
        self.assertEqual(list(target.iterdir()), [])

    def test_init_refuses_broken_symlink_without_touching_it(self):
        missing_target = Path(self.temporary_directory.name) / "missing-target"
        self.project.symlink_to(missing_target, target_is_directory=True)

        try:
            ROUTE_CLI.init_route(self.project, "Title", "en")
        except Exception as error:
            caught_error = error
        else:
            caught_error = None

        self.assertIsInstance(caught_error, FileExistsError)
        self.assertTrue(self.project.is_symlink())
        self.assertEqual(self.project.readlink(), missing_target)
        self.assertFalse(missing_target.exists())

    def test_parse_frontmatter_accepts_supported_scalars_and_preserves_body(self):
        route = Path(self.temporary_directory.name) / "ROUTE.md"
        body = "\n# Body\n\nKeep this exactly.\n"
        route.write_text(
            "---\n"
            'title: "Quoted title"\n'
            "venue: null\n"
            "count: -12\n"
            'tags: ["care", 3, null]\n'
            "---\n"
            + body,
            encoding="utf-8",
        )

        metadata, parsed_body = ROUTE_CLI.parse_frontmatter(route)

        self.assertEqual(
            metadata,
            {
                "title": "Quoted title",
                "venue": None,
                "count": -12,
                "tags": ["care", 3, None],
            },
        )
        self.assertEqual(parsed_body, body)

    def test_parse_frontmatter_rejects_unsupported_or_nested_yaml(self):
        route = Path(self.temporary_directory.name) / "ROUTE.md"
        invalid_frontmatter = {
            "indentation": "  child: 1\n",
            "nested mapping": "parent:\n  child: 1\n",
            "JSON object": 'value: {"nested": 1}\n',
            "boolean": "value: true\n",
            "duplicate key": "value: 1\nvalue: 2\n",
        }

        for description, content in invalid_frontmatter.items():
            with self.subTest(description=description):
                route.write_text(f"---\n{content}---\n", encoding="utf-8")
                with self.assertRaises(ValueError):
                    ROUTE_CLI.parse_frontmatter(route)

    def test_write_frontmatter_rejects_unsupported_output_values(self):
        route = Path(self.temporary_directory.name) / "ROUTE.md"
        route.write_text("original", encoding="utf-8")

        with self.assertRaises(ValueError):
            ROUTE_CLI.write_frontmatter(route, {"nested": {"value": 1}}, "body")

        self.assertEqual(route.read_text(encoding="utf-8"), "original")

    def test_write_frontmatter_atomically_replaces_existing_file(self):
        route = Path(self.temporary_directory.name) / "ROUTE.md"
        route.write_text("original", encoding="utf-8")
        original_inode = route.stat().st_ino

        ROUTE_CLI.write_frontmatter(route, {"count": 1}, "\nBody\n")

        self.assertNotEqual(route.stat().st_ino, original_inode)
        metadata, body = ROUTE_CLI.parse_frontmatter(route)
        self.assertEqual(metadata, {"count": 1})
        self.assertEqual(body, "\nBody\n")

    def test_write_frontmatter_does_not_clobber_fixed_temp_name_collision(self):
        route = Path(self.temporary_directory.name) / "ROUTE.md"
        route.write_text("original", encoding="utf-8")
        unrelated_temp = route.with_name(f".{route.name}.tmp")
        unrelated_temp.write_text("unrelated", encoding="utf-8")

        ROUTE_CLI.write_frontmatter(route, {"count": 1}, "\nBody\n")

        self.assertTrue(unrelated_temp.exists())
        self.assertEqual(unrelated_temp.read_text(encoding="utf-8"), "unrelated")

    def test_init_cleans_staging_directory_after_template_parse_failure(self):
        invalid_template = Path(self.temporary_directory.name) / "invalid-template"
        invalid_template.mkdir()
        (invalid_template / "ROUTE.md").write_text(
            "not frontmatter\n", encoding="utf-8"
        )

        with mock.patch.object(ROUTE_CLI, "TEMPLATE_ROOT", invalid_template):
            with self.assertRaises(ValueError):
                ROUTE_CLI.init_route(self.project, "Title", "en")

        self.assertFalse(self.project.exists())
        self.assertEqual(
            list(self.project.parent.glob(f".{self.project.name}.*.tmp")), []
        )
