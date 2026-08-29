from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
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

    def write_docx(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
        )
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document)

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

    def test_prose_checkpoint_blocks_research_traceability_leaks(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text(
            "# Draft\n\n"
            "Screened via parent `referencias.bib` (50 sources).\n"
            "Search layers were logged in `references/source-search-rr002.md`.\n"
            "Source cards S-01..S-06c record the evidence.\n"
            "The cards remain at `excerpt/metadata`.\n"
            "The claim is pending full-text page verification.\n",
            encoding="utf-8",
        )
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n---\n',
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "prose", "r1")

        leak_lines = {
            issue.path.rsplit(":", 1)[-1]
            for issue in issues
            if issue.code == "prose-leak"
        }
        self.assertEqual(leak_lines, {"3", "4", "5", "6", "7"})

    def test_prose_checkpoint_accepts_publishable_methods_and_references(self) -> None:
        text = (
            "We searched Web of Science, Scopus, JSTOR, and SciELO for "
            "English- and Spanish-language scholarship published between "
            "1960 and 2024. We retained the principal positions and strongest "
            "rival accounts relevant to the argument.\n\n"
            "Lancy, D. F. (2015). The Anthropology of Childhood: Cherubs, "
            "Chattel, Changelings. Cambridge University Press.\n"
        )

        issues = ROUTE._prose_findings(Path("manuscript/draft.md"), text)

        self.assertFalse(any(issue.code == "prose-leak" for issue in issues))

    def test_argument_checkpoint_requires_structured_claims_for_legacy_index_entries(self) -> None:
        self.init()
        (self.root / "CLAIMS.md").write_text(
            "# Claims\n\n## Central claim\n\n"
            "- C-001 — The central claim.\n",
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "argument")

        self.assertTrue(any(issue.code == "claims-record" for issue in issues))

    def test_submission_blocks_provisional_claim_targeting_manuscript(self) -> None:
        self.init()
        claim = self.root / "claims" / "C-001-central.md"
        claim.write_text(
            "---\n"
            'id: "C-001"\n'
            'state: "provisional"\n'
            'risk: "material"\n'
            'scope: "central claim"\n'
            'evidence: ["S-01"]\n'
            'challenges: "rival"\n'
            'confidence: "medium"\n'
            'manuscript_targets: ["manuscript/draft.md"]\n'
            'review_status: "reviewed"\n'
            'reopening_condition: "inspect rival"\n'
            "---\n\nCentral claim.\n",
            encoding="utf-8",
        )
        (self.root / "CLAIMS.md").write_text(
            "# Claims\n\n## Central claim\n\n- C-001 — The central claim.\n",
            encoding="utf-8",
        )
        (self.root / "sources" / "S-01-test.md").write_text(
            "# S-01\n\n- access level: full text\n",
            encoding="utf-8",
        )
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text("An academic sentence with evidence.\n", encoding="utf-8")
        docx = self.root / "manuscript" / "draft.docx"
        self.write_docx(docx, "An academic sentence with evidence.")
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\ndocx: "manuscript/draft.docx"\n---\n',
            encoding="utf-8",
        )
        ROUTE.approve_release_record(
            self.root,
            "r1",
            "approval",
            {"author": "author", "decision": "submit"},
        )

        issues = ROUTE.validate_route(self.root, "submission", "r1")

        self.assertTrue(any(issue.code == "unresolved-manuscript-claim" for issue in issues))

    def test_argument_checkpoint_requires_claim_evidence_to_resolve_to_source_card(self) -> None:
        self.init()
        claim = self.root / "claims" / "C-001-central.md"
        claim.write_text(
            "---\n"
            'id: "C-001"\n'
            'state: "supported"\n'
            'risk: "material"\n'
            'scope: "central claim"\n'
            'evidence: ["S-99"]\n'
            'challenges: "rival"\n'
            'confidence: "high"\n'
            'manuscript_targets: ["manuscript/draft.md"]\n'
            'review_status: "reviewed"\n'
            'reopening_condition: "inspect rival"\n'
            "---\n\nCentral claim.\n",
            encoding="utf-8",
        )
        (self.root / "CLAIMS.md").write_text(
            "# Claims\n\n## Central claim\n\n- C-001 — The central claim.\n",
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "argument")

        self.assertTrue(any(issue.code == "missing-source-card" for issue in issues))

    def test_argument_checkpoint_rejects_supported_claim_without_full_text_source(self) -> None:
        self.init()
        claim = self.root / "claims" / "C-001-central.md"
        claim.write_text(
            "---\n"
            'id: "C-001"\n'
            'state: "supported"\n'
            'risk: "material"\n'
            'scope: "central claim"\n'
            'evidence: ["S-01"]\n'
            'challenges: "rival"\n'
            'confidence: "high"\n'
            'manuscript_targets: ["manuscript/draft.md"]\n'
            'review_status: "reviewed"\n'
            'reopening_condition: "inspect rival"\n'
            "---\n\nCentral claim.\n",
            encoding="utf-8",
        )
        (self.root / "CLAIMS.md").write_text(
            "# Claims\n\n## Central claim\n\n- C-001 — The central claim.\n",
            encoding="utf-8",
        )
        (self.root / "sources" / "S-01-test.md").write_text(
            "# S-01\n\n- access level: excerpt\n",
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "argument")

        self.assertTrue(any(issue.code == "unsupported-source-access" for issue in issues))

    def test_release_checkpoint_blocks_orphan_manuscript_artifacts(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text("An academic sentence.\n", encoding="utf-8")
        (self.root / "manuscript" / "draft.pdf").write_bytes(b"pdf")

        issues = ROUTE.validate_route(self.root, "release")

        self.assertTrue(any(issue.code == "orphan-release-artifact" for issue in issues))

    def test_prose_checkpoint_blocks_release_scaffolding_and_wrong_word_count(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text(
            "*Research Route `paper de research route/` — English — draft*\n"
            "*Provisional target: Journal of Family Theory & Review*\n"
            "Word count: ~7,500 (manuscript) + references\n"
            "An academic sentence.\n",
            encoding="utf-8",
        )
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n---\n',
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "prose", "r1")

        self.assertTrue(any(issue.code == "release-scaffolding" for issue in issues))
        self.assertTrue(any(issue.code == "word-count" for issue in issues))

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
        self.assertFalse(report["ready"])

    def test_advance_rejects_missing_output_without_partial_state(self) -> None:
        self.init()
        result = self.cli(
            "advance",
            "--root",
            str(self.root),
            "--title",
            "Missing output",
            "--type",
            "question",
            "--owner",
            "agent-a",
            "--output",
            "missing.md",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            list((self.root / "work-items").glob("rr-*.md")), []
        )
        self.assertEqual(
            list((self.root / ".research-route" / "claims").glob("*.lock")), []
        )

    def test_release_checkpoint_rejects_stale_release_approval(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text(
            "This manuscript contains a complete academic sentence for review.\n",
            encoding="utf-8",
        )
        docx = self.root / "manuscript" / "draft.docx"
        self.write_docx(docx, "This manuscript contains a complete academic sentence for review.")
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n'
            'docx: "manuscript/draft.docx"\n---\n',
            encoding="utf-8",
        )
        ROUTE.approve_release_record(
            self.root,
            "r1",
            "approval",
            {"author": "author", "decision": "submit"},
        )
        manuscript.write_text(
            "This manuscript was changed after the approval was recorded.\n",
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "release", "r1")

        self.assertTrue(any(issue.code == "stale-approval" for issue in issues))

    def test_release_checkpoint_rejects_manifest_path_escape(self) -> None:
        self.init()
        outside = self.root.parent / "outside.md"
        outside.write_text("An external manuscript.\n", encoding="utf-8")
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "../outside.md"\n'
            'docx: "../outside.md"\n---\n',
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "release", "r1")

        self.assertTrue(any(issue.code == "invalid-path" for issue in issues))

    def test_release_checkpoint_rejects_manifest_symlink(self) -> None:
        self.init()
        outside = self.root.parent / "outside.md"
        outside.write_text("An external manuscript.\n", encoding="utf-8")
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.symlink_to(outside)
        docx = self.root / "manuscript" / "draft.docx"
        self.write_docx(docx, "An academic sentence.")
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n'
            'docx: "manuscript/draft.docx"\n---\n',
            encoding="utf-8",
        )

        issues = ROUTE.validate_route(self.root, "release", "r1")

        self.assertTrue(any(issue.code == "missing-path" for issue in issues))

    def test_release_checkpoint_requires_authorizing_decision(self) -> None:
        self.init()
        manuscript = self.root / "manuscript" / "draft.md"
        manuscript.write_text("An academic sentence.\n", encoding="utf-8")
        docx = self.root / "manuscript" / "draft.docx"
        self.write_docx(docx, "An academic sentence.")
        release = self.root / "releases" / "r1"
        release.mkdir(parents=True)
        (release / "RELEASE.md").write_text(
            '---\nsource_manuscript: "manuscript/draft.md"\n'
            'docx: "manuscript/draft.docx"\n---\n',
            encoding="utf-8",
        )
        ROUTE.approve_release_record(
            self.root,
            "r1",
            "approval",
            {"author": "author", "decision": "reject"},
        )

        issues = ROUTE.validate_route(self.root, "release", "r1")

        self.assertTrue(any(issue.code == "author-approval" for issue in issues))

    def test_file_backed_route_replay_validates_handoff(self) -> None:
        self.init()
        route = self.root / "ROUTE.md"
        metadata, body = ROUTE.parse_frontmatter(route)
        body = body.replace(
            "## Destination\n",
            "## Destination\nA durable paper project.\n\n",
        ).replace(
            "## Exact next action\n",
            "## Exact next action\nReview the completed source map.\n\n",
        )
        ROUTE.write_frontmatter(route, metadata, body)

        output = self.root / "notes" / "source-map.md"
        output.parent.mkdir()
        output.write_text(
            "The source map records the relevant evidence and limits.\n",
            encoding="utf-8",
        )
        item = ROUTE.new_work_item(
            self.root, "Map sources", "source", "light", []
        )
        item_metadata, _ = ROUTE.parse_frontmatter(item)
        item_id = item_metadata["id"]
        ROUTE.claim_item(self.root, item_id, "agent-a")
        ROUTE.complete_item(
            self.root,
            item_id,
            "agent-a",
            "notes/source-map.md",
            verification=["notes/source-map.md"],
            result="Source map completed",
        )

        ROUTE.scaffold_handoff(self.root)
        handoff = self.root / "HANDOFF.md"
        handoff_text = handoff.read_text(encoding="utf-8")
        for heading, content in (
            ("## Intellectual change", "The source map is complete."),
            ("## Invalidated assumptions", "- None"),
            ("## Live contradiction", "- None"),
            ("## Researcher decisions needed", "- None"),
            ("## Exact next action and why", "Review the completed source map."),
        ):
            handoff_text = handoff_text.replace(
                heading + "\n", heading + "\n" + content + "\n\n"
            )
        handoff.write_text(handoff_text, encoding="utf-8")
        ROUTE.scaffold_handoff(self.root)

        self.assertEqual(ROUTE.validate_route(self.root, "handoff"), [])

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
