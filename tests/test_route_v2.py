from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "research-route" / "scripts" / "route.py"
SPEC = importlib.util.spec_from_file_location("research_route_v2_cli", CLI)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load route CLI")
ROUTE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ROUTE
SPEC.loader.exec_module(ROUTE)


class RouteV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "paper"

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def init(self, version: str = "2") -> None:
        result = self.cli(
            "init",
            str(self.root),
            "--title",
            "V2 paper",
            "--language",
            "es",
            "--schema-version",
            version,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_v2_init_creates_claim_and_release_layers(self) -> None:
        self.init()
        metadata, _ = ROUTE.parse_frontmatter(self.root / "ROUTE.md")
        self.assertEqual(metadata["schema_version"], 2)
        self.assertTrue((self.root / "claims").is_dir())
        self.assertTrue((self.root / "releases").is_dir())

    def test_v2_work_item_has_adaptive_risk_and_review_fields(self) -> None:
        self.init()
        path = ROUTE.new_work_item(self.root, "Explore terms", "question", "light", [])
        metadata, _ = ROUTE.parse_frontmatter(path)
        self.assertEqual(metadata["schema_version"], 2)
        self.assertEqual(metadata["risk"], "routine")
        self.assertEqual(metadata["review_status"], "none")

    def test_advance_records_routine_work_in_one_command(self) -> None:
        self.init()
        output = self.root / "notes" / "terms.md"
        output.parent.mkdir()
        output.write_text("Provisional notes.\n", encoding="utf-8")
        result = self.cli(
            "advance",
            "--root",
            str(self.root),
            "--title",
            "Explore terms",
            "--type",
            "question",
            "--owner",
            "agent-a",
            "--output",
            "notes/terms.md",
            "--review-later",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        items = list((self.root / "work-items").glob("rr-*.md"))
        self.assertEqual(len(items), 1)
        metadata, _ = ROUTE.parse_frontmatter(items[0])
        self.assertEqual(metadata["status"], "provisional")
        self.assertEqual(metadata["review_status"], "deferred")

    def test_prose_checkpoint_blocks_internal_pipeline_terms(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text(
            "# Draft\n\nVersion v1.3-final. TwExtract found the claim.\n",
            encoding="utf-8",
        )
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n---\n',
            encoding="utf-8",
        )
        issues = ROUTE.validate_route(self.root, "prose", "r1")
        self.assertTrue(any(issue.code == "prose-leak" for issue in issues))

    def test_review_argument_reports_deferred_work(self) -> None:
        self.init()
        output = self.root / "notes.md"
        output.write_text("Notes\n", encoding="utf-8")
        ROUTE.advance_work(
            self.root,
            "Deferred synthesis",
            "synthesis",
            "agent-a",
            "notes.md",
            review_later=True,
        )
        report = ROUTE.review_route(self.root, "argument")
        self.assertEqual(report["stage"], "argument")
        self.assertEqual(report["deferred_count"], 1)

    def test_migration_dry_run_does_not_mutate_v1_root(self) -> None:
        self.init("1")
        before = (self.root / "ROUTE.md").read_bytes()
        result = self.cli("migrate", "--root", str(self.root), "--to", "2", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "ROUTE.md").read_bytes(), before)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["from"], 1)
        self.assertEqual(payload["to"], 2)

    def test_migration_apply_requires_fresh_dry_run(self) -> None:
        self.init("1")
        direct = self.cli("migrate", "--root", str(self.root), "--to", "2", "--apply")
        self.assertNotEqual(direct.returncode, 0)
        self.assertIn("dry-run", direct.stderr)
        dry = self.cli("migrate", "--root", str(self.root), "--to", "2", "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        applied = self.cli("migrate", "--root", str(self.root), "--to", "2", "--apply")
        self.assertEqual(applied.returncode, 0, applied.stderr)

    def test_advance_rejects_deferred_critical_submission_work(self) -> None:
        self.init()
        output = self.root / "submission.md"
        output.write_text("Submission\n", encoding="utf-8")
        result = self.cli(
            "advance",
            "--root",
            str(self.root),
            "--title",
            "Submit paper",
            "--type",
            "submission",
            "--owner",
            "author",
            "--output",
            "submission.md",
            "--review-later",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("critical", result.stderr)

    def test_v2_complete_requires_verification_unless_provisional(self) -> None:
        self.init()
        output = self.root / "result.md"
        output.write_text("Result\n", encoding="utf-8")
        item = ROUTE.new_work_item(self.root, "Verify result", "synthesis", "light", [])
        item_metadata, _ = ROUTE.parse_frontmatter(item)
        item_id = item_metadata["id"]
        ROUTE.claim_item(self.root, item_id, "agent-a")
        with self.assertRaisesRegex(ValueError, "requires verification"):
            ROUTE.complete_item(self.root, item_id, "agent-a", "result.md")
        ROUTE.complete_item(
            self.root,
            item_id,
            "agent-a",
            "result.md",
            verification=["result.md"],
            result="Verified result",
        )

    def test_release_checkpoint_requires_docx_and_author_approval(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text("Academic sentence with an article.\n", encoding="utf-8")
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n---\n',
            encoding="utf-8",
        )
        issues = ROUTE.validate_route(self.root, "release", "r1")
        codes = {issue.code for issue in issues}
        self.assertIn("release-manifest", codes)
        self.assertIn("author-approval", codes)

    def test_prose_exception_is_bound_to_artifact_hash(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text("Version v1.3-final.\n", encoding="utf-8")
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n---\n',
            encoding="utf-8",
        )
        before = ROUTE.validate_route(self.root, "prose", "r1")
        self.assertTrue(before)
        artifact_hash = __import__("hashlib").sha256(manuscript.read_bytes()).hexdigest()
        (release / "EXCEPTIONS.md").write_text(
            f"finding: prose-leak manuscript/draft.md:1\nartifact_sha256: {artifact_hash}\n",
            encoding="utf-8",
        )
        after = ROUTE.validate_route(self.root, "prose", "r1")
        self.assertFalse(any(issue.code == "prose-leak" for issue in after))
        manuscript.write_text("Version v1.3-final changed.\n", encoding="utf-8")
        changed = ROUTE.validate_route(self.root, "prose", "r1")
        self.assertTrue(any(issue.code == "prose-leak" for issue in changed))


if __name__ == "__main__":
    unittest.main()
