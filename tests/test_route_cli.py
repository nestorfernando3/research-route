from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "research-route" / "scripts" / "route.py"
SPEC = importlib.util.spec_from_file_location("research_route_cli", CLI)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load route CLI from {CLI}")
ROUTE_CLI = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ROUTE_CLI
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

    def init_project(self) -> None:
        result = self.run_cli(
            "init", str(self.project), "--title", "Test route", "--language", "en"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def init_project_with_item(self) -> None:
        self.init_project()
        result = self.run_cli(
            "new",
            "--root",
            str(self.project),
            "--title",
            "Map rival accounts",
            "--type",
            "synthesis",
            "--mode",
            "deep",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def write_item(
        self, filename: str, item_id: str, depends_on: list[str]
    ) -> Path:
        path = self.project / "work-items" / filename
        path.write_text(
            ROUTE_CLI._frontmatter_text(
                {
                    "id": item_id,
                    "title": "Test work item",
                    "schema_version": 1,
                    "type": "synthesis",
                    "status": "open",
                    "depends_on": depends_on,
                    "owner": None,
                    "mode": "deep",
                    "output": None,
                },
                "\n# Work item\n",
            ),
            encoding="utf-8",
        )
        return path

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

    def test_new_allocates_stable_ids_and_updates_counter(self):
        self.init_project()

        first = self.run_cli(
            "new",
            "--root",
            str(self.project),
            "--title",
            "Map rival accounts",
            "--type",
            "synthesis",
            "--mode",
            "deep",
        )
        second = self.run_cli(
            "new",
            "--root",
            str(self.project),
            "--title",
            "Check archive scope",
            "--type",
            "source",
            "--mode",
            "light",
            "--depends-on",
            "rr-001",
        )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        first_item = self.project / "work-items" / "rr-001-map-rival-accounts.md"
        second_item = self.project / "work-items" / "rr-002-check-archive-scope.md"
        self.assertTrue(first_item.exists())
        self.assertTrue(second_item.exists())
        first_metadata, _ = ROUTE_CLI.parse_frontmatter(first_item)
        second_metadata, _ = ROUTE_CLI.parse_frontmatter(second_item)
        self.assertEqual(
            first_metadata,
            {
                "id": "rr-001",
                "title": "Map rival accounts",
                "schema_version": 1,
                "type": "synthesis",
                "status": "open",
                "depends_on": [],
                "owner": None,
                "mode": "deep",
                "output": None,
            },
        )
        self.assertEqual(second_metadata["depends_on"], ["rr-001"])
        route_metadata, _ = ROUTE_CLI.parse_frontmatter(self.project / "ROUTE.md")
        self.assertEqual(route_metadata["next_work_item"], 3)

    def test_claim_is_atomic_and_release_requires_owner(self):
        self.init_project_with_item()

        first = self.run_cli(
            "claim", "rr-001", "--root", str(self.project), "--owner", "agent-a"
        )
        second = self.run_cli(
            "claim", "rr-001", "--root", str(self.project), "--owner", "agent-b"
        )
        wrong_release = self.run_cli(
            "release", "rr-001", "--root", str(self.project), "--owner", "agent-b"
        )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotEqual(second.returncode, 0)
        self.assertNotEqual(wrong_release.returncode, 0)
        lock = self.project / ".research-route" / "claims" / "rr-001.lock"
        claim = json.loads(lock.read_text(encoding="utf-8"))
        self.assertEqual(claim["item_id"], "rr-001")
        self.assertEqual(claim["owner"], "agent-a")
        self.assertRegex(claim["timestamp"], r"^\d{4}-\d{2}-\d{2}T.*\+00:00$")

        owner_release = self.run_cli(
            "release", "rr-001", "--root", str(self.project), "--owner", "agent-a"
        )
        self.assertEqual(owner_release.returncode, 0, owner_release.stderr)
        self.assertFalse(lock.exists())

    def test_force_release_warns_and_removes_another_owners_claim(self):
        self.init_project_with_item()
        claimed = self.run_cli(
            "claim", "rr-001", "--root", str(self.project), "--owner", "agent-a"
        )
        self.assertEqual(claimed.returncode, 0, claimed.stderr)

        released = self.run_cli(
            "release",
            "rr-001",
            "--root",
            str(self.project),
            "--owner",
            "agent-b",
            "--force",
        )

        self.assertEqual(released.returncode, 0, released.stderr)
        self.assertIn("warning", released.stderr.lower())
        self.assertFalse(
            (self.project / ".research-route" / "claims" / "rr-001.lock").exists()
        )

    def test_new_rejects_unsupported_type_and_mode_without_changing_counter(self):
        self.init_project()

        invalid_type = self.run_cli(
            "new",
            "--root",
            str(self.project),
            "--title",
            "Invalid",
            "--type",
            "note",
            "--mode",
            "light",
        )
        invalid_mode = self.run_cli(
            "new",
            "--root",
            str(self.project),
            "--title",
            "Invalid",
            "--type",
            "question",
            "--mode",
            "medium",
        )

        self.assertNotEqual(invalid_type.returncode, 0)
        self.assertNotEqual(invalid_mode.returncode, 0)
        route_metadata, _ = ROUTE_CLI.parse_frontmatter(self.project / "ROUTE.md")
        self.assertEqual(route_metadata["next_work_item"], 1)
        self.assertEqual(list((self.project / "work-items").glob("rr-*.md")), [])

    def test_new_transliterates_spanish_titles_without_changing_frontmatter(self):
        self.init_project()

        first = ROUTE_CLI.new_work_item(
            self.project, "Ética pública", "question", "light", []
        )
        second = ROUTE_CLI.new_work_item(
            self.project, "Niñez", "writing", "deep", []
        )

        self.assertEqual(first.name, "rr-001-etica-publica.md")
        self.assertEqual(second.name, "rr-002-ninez.md")
        first_metadata, _ = ROUTE_CLI.parse_frontmatter(first)
        second_metadata, _ = ROUTE_CLI.parse_frontmatter(second)
        self.assertEqual(first_metadata["title"], "Ética pública")
        self.assertEqual(second_metadata["title"], "Niñez")

    def test_new_skips_interrupted_reservation_and_advances_counter(self):
        self.init_project()
        reservations = self.project / ".research-route" / "allocations"
        reservations.mkdir(parents=True)
        (reservations / "rr-001.reserve").write_text(
            '{"item_id": "rr-001"}\n', encoding="utf-8"
        )

        item = ROUTE_CLI.new_work_item(
            self.project, "Recovered allocation", "audit", "light", []
        )

        self.assertEqual(item.name, "rr-002-recovered-allocation.md")
        route_metadata, _ = ROUTE_CLI.parse_frontmatter(self.project / "ROUTE.md")
        self.assertEqual(route_metadata["next_work_item"], 3)
        self.assertTrue((reservations / "rr-002.reserve").exists())

    def test_new_ignores_stale_legacy_counter_lock(self):
        self.init_project()
        state = self.project / ".research-route"
        state.mkdir()
        stale_lock = state / "counter.lock"
        stale_lock.write_text("abandoned\n", encoding="utf-8")

        item = ROUTE_CLI.new_work_item(
            self.project, "After old crash", "audit", "light", []
        )

        self.assertEqual(item.name, "rr-001-after-old-crash.md")
        self.assertEqual(stale_lock.read_text(encoding="utf-8"), "abandoned\n")

    def test_concurrent_new_calls_allocate_distinct_stable_ids(self):
        self.init_project()
        first_at_route_write = threading.Event()
        allow_first_write = threading.Event()
        original_write = ROUTE_CLI.write_frontmatter

        def delayed_write(path, metadata, body):
            if (
                path == self.project / "ROUTE.md"
                and threading.current_thread().name == "allocation_0"
            ):
                first_at_route_write.set()
                self.assertTrue(allow_first_write.wait(2))
            return original_write(path, metadata, body)

        with mock.patch.object(ROUTE_CLI, "write_frontmatter", delayed_write):
            with ThreadPoolExecutor(
                max_workers=2, thread_name_prefix="allocation"
            ) as executor:
                first = executor.submit(
                    ROUTE_CLI.new_work_item,
                    self.project,
                    "First concurrent item",
                    "source",
                    "light",
                    [],
                )
                self.assertTrue(first_at_route_write.wait(2))
                second = executor.submit(
                    ROUTE_CLI.new_work_item,
                    self.project,
                    "Second concurrent item",
                    "source",
                    "light",
                    [],
                )
                wait([second], timeout=0.2)
                allow_first_write.set()
                paths = [first.result(timeout=2), second.result(timeout=2)]

        self.assertEqual({path.name[:6] for path in paths}, {"rr-001", "rr-002"})
        route_metadata, _ = ROUTE_CLI.parse_frontmatter(self.project / "ROUTE.md")
        self.assertEqual(route_metadata["next_work_item"], 3)

    def test_release_guard_prevents_deleting_a_replacement_claim(self):
        self.init_project_with_item()
        ROUTE_CLI.claim_item(self.project, "rr-001", "agent-a")
        lock = self.project / ".research-route" / "claims" / "rr-001.lock"
        release_has_read = threading.Event()
        allow_release = threading.Event()
        replacement_finished = threading.Event()
        original_read_text = Path.read_text

        def delayed_read_text(path, *args, **kwargs):
            text = original_read_text(path, *args, **kwargs)
            if path == lock and threading.current_thread().name == "releaser":
                release_has_read.set()
                self.assertTrue(allow_release.wait(2))
            return text

        release_error: list[Exception] = []

        def release_old_claim() -> None:
            try:
                ROUTE_CLI.release_item(self.project, "rr-001", "agent-a")
            except Exception as error:
                release_error.append(error)

        def create_replacement() -> None:
            ROUTE_CLI.claim_item(self.project, "rr-001", "agent-c")
            replacement_finished.set()

        with mock.patch.object(Path, "read_text", delayed_read_text):
            releaser = threading.Thread(target=release_old_claim, name="releaser")
            releaser.start()
            self.assertTrue(release_has_read.wait(2))
            lock.unlink()
            replacement = threading.Thread(target=create_replacement)
            replacement.start()
            finished_during_release = replacement_finished.wait(0.2)
            allow_release.set()
            releaser.join(2)
            replacement.join(2)

        self.assertFalse(finished_during_release)
        self.assertFalse(releaser.is_alive())
        self.assertFalse(replacement.is_alive())
        self.assertTrue(release_error)
        claim = json.loads(lock.read_text(encoding="utf-8"))
        self.assertEqual(claim["owner"], "agent-c")

    def test_new_rejects_symlinked_work_items_without_touching_target(self):
        self.init_project()
        external = Path(self.temporary_directory.name) / "external-work-items"
        external.mkdir()
        shutil.rmtree(self.project / "work-items")
        (self.project / "work-items").symlink_to(external, target_is_directory=True)

        with self.assertRaises(ValueError):
            ROUTE_CLI.new_work_item(
                self.project, "Escaping item", "question", "light", []
            )

        self.assertEqual(list(external.iterdir()), [])
        route_metadata, _ = ROUTE_CLI.parse_frontmatter(self.project / "ROUTE.md")
        self.assertEqual(route_metadata["next_work_item"], 1)

    def test_new_rejects_symlinked_state_directory_without_touching_target(self):
        self.init_project()
        external = Path(self.temporary_directory.name) / "external-state"
        external.mkdir()
        (self.project / ".research-route").symlink_to(
            external, target_is_directory=True
        )

        with self.assertRaises(ValueError):
            ROUTE_CLI.new_work_item(
                self.project, "Escaping state", "question", "light", []
            )

        self.assertEqual(list(external.iterdir()), [])
        route_metadata, _ = ROUTE_CLI.parse_frontmatter(self.project / "ROUTE.md")
        self.assertEqual(route_metadata["next_work_item"], 1)

    def test_claim_rejects_symlinked_claims_without_touching_target(self):
        self.init_project_with_item()
        external = Path(self.temporary_directory.name) / "external-claims"
        external.mkdir()
        claims = self.project / ".research-route" / "claims"
        claims.parent.mkdir(exist_ok=True)
        claims.symlink_to(external, target_is_directory=True)

        with self.assertRaises(ValueError):
            ROUTE_CLI.claim_item(self.project, "rr-001", "agent-a")

        self.assertEqual(list(external.iterdir()), [])

    def test_concurrent_new_calls_race_safely_creating_state_directory(self):
        self.init_project()
        state = self.project / ".research-route"
        creation_barrier = threading.Barrier(2)
        original_mkdir = Path.mkdir

        def synchronized_mkdir(path, *args, **kwargs):
            if path == state:
                creation_barrier.wait(2)
            return original_mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", synchronized_mkdir):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        ROUTE_CLI.new_work_item,
                        self.project,
                        f"State race {index}",
                        "source",
                        "light",
                        [],
                    )
                    for index in range(2)
                ]
                paths = [future.result(timeout=3) for future in futures]

        self.assertEqual({path.name[:6] for path in paths}, {"rr-001", "rr-002"})
        self.assertTrue(state.is_dir())
        self.assertFalse(state.is_symlink())

    def test_concurrent_new_calls_race_safely_creating_allocations_directory(self):
        self.init_project()
        state = self.project / ".research-route"
        state.mkdir()
        allocations = state / "allocations"
        creation_barrier = threading.Barrier(2)
        original_mkdir = Path.mkdir

        def synchronized_mkdir(path, *args, **kwargs):
            if path == allocations:
                creation_barrier.wait(2)
            return original_mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", synchronized_mkdir):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        ROUTE_CLI.new_work_item,
                        self.project,
                        f"Allocation directory race {index}",
                        "source",
                        "light",
                        [],
                    )
                    for index in range(2)
                ]
                paths = [future.result(timeout=3) for future in futures]

        self.assertEqual({path.name[:6] for path in paths}, {"rr-001", "rr-002"})
        self.assertTrue(allocations.is_dir())
        self.assertFalse(allocations.is_symlink())

    def test_concurrent_claims_race_safely_creating_claims_directory(self):
        self.init_project()
        first_item = ROUTE_CLI.new_work_item(
            self.project, "Claim race one", "source", "light", []
        )
        second_item = ROUTE_CLI.new_work_item(
            self.project, "Claim race two", "source", "light", []
        )
        claims = self.project / ".research-route" / "claims"
        creation_barrier = threading.Barrier(2)
        original_mkdir = Path.mkdir

        def synchronized_mkdir(path, *args, **kwargs):
            if path == claims:
                creation_barrier.wait(2)
            return original_mkdir(path, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", synchronized_mkdir):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(
                        ROUTE_CLI.claim_item,
                        self.project,
                        item_id,
                        owner,
                    )
                    for item_id, owner in (
                        (first_item.name[:6], "agent-a"),
                        (second_item.name[:6], "agent-b"),
                    )
                ]
                locks = [future.result(timeout=3) for future in futures]

        self.assertEqual({lock.name for lock in locks}, {"rr-001.lock", "rr-002.lock"})
        self.assertTrue(claims.is_dir())
        self.assertFalse(claims.is_symlink())

    def test_validate_reports_broken_links_duplicate_ids_and_missing_dependencies(self):
        self.init_project()
        self.write_item("rr-001-a.md", item_id="rr-001", depends_on=["rr-999"])
        self.write_item("rr-001-b.md", item_id="rr-001", depends_on=[])
        (self.project / "CLAIMS.md").write_text(
            "[missing source](sources/not-there.md)\n", encoding="utf-8"
        )

        result = self.run_cli("validate", "--root", str(self.project), "--json")

        issues = json.loads(result.stdout)
        codes = {issue["code"] for issue in issues}
        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            {"duplicate-id", "missing-dependency", "broken-link"}.issubset(codes)
        )
        self.assertEqual(
            issues,
            sorted(
                issues,
                key=lambda issue: (issue["path"], issue["code"], issue["message"]),
            ),
        )

    def test_validate_accepts_a_fresh_route(self):
        self.init_project()

        result = self.run_cli("validate", "--root", str(self.project))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validate_reports_schema_fields_enums_cycles_and_claim_inconsistency(self):
        self.init_project()
        route = self.project / "ROUTE.md"
        route_metadata, route_body = ROUTE_CLI.parse_frontmatter(route)
        route_metadata["schema_version"] = 99
        route_metadata.pop("language")
        ROUTE_CLI.write_frontmatter(route, route_metadata, route_body)
        first = self.write_item("rr-001-first.md", "rr-001", ["rr-002"])
        self.write_item("rr-002-second.md", "rr-002", ["rr-001"])
        first_metadata, first_body = ROUTE_CLI.parse_frontmatter(first)
        first_metadata.pop("output")
        first_metadata["type"] = "unsupported"
        first_metadata["status"] = "running"
        first_metadata["mode"] = "medium"
        ROUTE_CLI.write_frontmatter(first, first_metadata, first_body)
        claims = self.project / ".research-route" / "claims"
        claims.mkdir(parents=True)
        (claims / "rr-003.lock").write_text(
            json.dumps(
                {
                    "item_id": "rr-004",
                    "owner": "agent-a",
                    "timestamp": "2026-07-13T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)
        codes = {issue.code for issue in issues}

        self.assertTrue(
            {
                "unsupported-schema",
                "missing-field",
                "invalid-enum",
                "dependency-cycle",
                "claim-mismatch",
                "orphan-claim",
            }.issubset(codes)
        )
        self.assertEqual(
            issues,
            sorted(issues, key=lambda issue: (issue.path, issue.code, issue.message)),
        )

    def test_validate_reports_missing_paths_and_malformed_frontmatter(self):
        self.init_project()
        shutil.rmtree(self.project / "sources")
        (self.project / "VENUE.md").unlink()
        (self.project / "work-items" / "rr-001-bad.md").write_text(
            "not frontmatter\n", encoding="utf-8"
        )

        issues = ROUTE_CLI.validate_route(self.project)
        codes = {issue.code for issue in issues}

        self.assertIn("missing-path", codes)
        self.assertIn("invalid-frontmatter", codes)

    def test_validate_ignores_external_fragment_and_durable_state_artifacts(self):
        self.init_project_with_item()
        claims = self.project / ".research-route" / "claims"
        claims.mkdir(exist_ok=True)
        (claims / "rr-001.lock").write_text(
            json.dumps(
                {
                    "item_id": "rr-001",
                    "owner": "agent-a",
                    "timestamp": "2026-07-13T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        (self.project / "CLAIMS.md").write_text(
            "[web](https://example.com) [mail](mailto:a@example.com) "
            "[fragment](#claims)\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertEqual(issues, [])

    def test_validate_human_output_uses_one_issue_per_line(self):
        self.init_project()
        (self.project / "CLAIMS.md").write_text(
            "[one](sources/one.md) [two](sources/two.md)\n", encoding="utf-8"
        )

        result = self.run_cli("validate", "--root", str(self.project))

        self.assertEqual(result.returncode, 1)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("broken-link" in line for line in lines))

    def test_validate_reports_non_scalar_enum_values_without_crashing(self):
        self.init_project()
        route = self.project / "ROUTE.md"
        metadata, body = ROUTE_CLI.parse_frontmatter(route)
        metadata["current_cycle"] = ["discover"]
        ROUTE_CLI.write_frontmatter(route, metadata, body)
        item = self.write_item("rr-001-item.md", "rr-001", [])
        item_metadata, item_body = ROUTE_CLI.parse_frontmatter(item)
        item_metadata["type"] = ["source"]
        ROUTE_CLI.write_frontmatter(item, item_metadata, item_body)

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertGreaterEqual(
            sum(issue.code == "invalid-enum" for issue in issues), 2
        )

    def test_validate_reports_non_scalar_claim_id_without_crashing(self):
        self.init_project()
        claims = self.project / ".research-route" / "claims"
        claims.mkdir(parents=True)
        (claims / "rr-001.lock").write_text(
            json.dumps({"item_id": ["rr-001"], "owner": "agent-a"}),
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertIn("invalid-claim", {issue.code for issue in issues})

    def test_validate_reports_invalid_route_and_item_field_types(self):
        self.init_project()
        route = self.project / "ROUTE.md"
        route_metadata, route_body = ROUTE_CLI.parse_frontmatter(route)
        route_metadata["project_title"] = ["not", "a", "title"]
        route_metadata["language"] = None
        ROUTE_CLI.write_frontmatter(route, route_metadata, route_body)
        item = self.write_item("rr-001-item.md", "rr-001", [])
        item_metadata, item_body = ROUTE_CLI.parse_frontmatter(item)
        item_metadata["title"] = ["not", "a", "title"]
        item_metadata["owner"] = 7
        item_metadata["output"] = ["not", "a", "path"]
        ROUTE_CLI.write_frontmatter(item, item_metadata, item_body)

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertGreaterEqual(
            sum(issue.code == "invalid-field" for issue in issues), 5
        )

    def test_validate_reports_null_required_enums(self):
        self.init_project()
        route = self.project / "ROUTE.md"
        route_metadata, route_body = ROUTE_CLI.parse_frontmatter(route)
        route_metadata["current_cycle"] = None
        ROUTE_CLI.write_frontmatter(route, route_metadata, route_body)
        item = self.write_item("rr-001-item.md", "rr-001", [])
        item_metadata, item_body = ROUTE_CLI.parse_frontmatter(item)
        for field in ("type", "status", "mode"):
            item_metadata[field] = None
        ROUTE_CLI.write_frontmatter(item, item_metadata, item_body)

        issues = ROUTE_CLI.validate_route(self.project)
        enum_messages = {
            issue.message for issue in issues if issue.code == "invalid-enum"
        }

        self.assertEqual(
            enum_messages,
            {
                "unsupported current_cycle: None",
                "unsupported type: None",
                "unsupported status: None",
                "unsupported mode: None",
            },
        )

    def test_validate_handles_a_1200_item_acyclic_dependency_chain(self):
        self.init_project()
        for index in range(1, 1201):
            item_id = f"rr-{index:04d}"
            dependency = [f"rr-{index + 1:04d}"] if index < 1200 else []
            self.write_item(f"{item_id}-item.md", item_id, dependency)

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertNotIn("dependency-cycle", {issue.code for issue in issues})

    def test_validate_reports_a_1200_item_cycle_as_valid_json(self):
        self.init_project()
        for index in range(1, 1201):
            item_id = f"rr-{index:04d}"
            dependency = (
                [f"rr-{index + 1:04d}"] if index < 1200 else ["rr-0001"]
            )
            self.write_item(f"{item_id}-item.md", item_id, dependency)

        result = self.run_cli("validate", "--root", str(self.project), "--json")
        issues = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(issues), 1200)
        self.assertTrue(all(issue["code"] == "dependency-cycle" for issue in issues))
        self.assertEqual(
            issues,
            sorted(
                issues,
                key=lambda issue: (issue["path"], issue["code"], issue["message"]),
            ),
        )

    def test_validate_reports_broken_reference_style_markdown_link(self):
        self.init_project()
        (self.project / "CLAIMS.md").write_text(
            "[missing][src]\n\n[src]: sources/missing.md\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)
        broken = [issue for issue in issues if issue.code == "broken-link"]

        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0].path, "CLAIMS.md")
        self.assertIn("sources/missing.md", broken[0].message)

    def test_validate_accepts_valid_and_ignored_reference_style_links(self):
        self.init_project()
        (self.project / "sources" / "present.md").write_text(
            "# Present\n", encoding="utf-8"
        )
        (self.project / "CLAIMS.md").write_text(
            "[present][local] [web][external] [mail][email] [section][fragment]\n\n"
            "[local]: sources/present.md\n"
            "[external]: https://example.com/source\n"
            "[email]: mailto:editor@example.com\n"
            "[fragment]: #claims\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertEqual(issues, [])

    def test_validate_reports_broken_shortcut_reference_link(self):
        self.init_project()
        (self.project / "CLAIMS.md").write_text(
            "Read [src].\n\n[src]: sources/missing.md\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)
        broken = [issue for issue in issues if issue.code == "broken-link"]

        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0].path, "CLAIMS.md")
        self.assertIn("sources/missing.md", broken[0].message)

    def test_validate_accepts_valid_shortcut_reference_link(self):
        self.init_project()
        (self.project / "sources" / "present.md").write_text(
            "# Present\n", encoding="utf-8"
        )
        (self.project / "CLAIMS.md").write_text(
            "Read [src].\n\n[src]: sources/present.md\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertEqual(issues, [])

    def test_validate_ignores_external_and_fragment_shortcut_references(self):
        self.init_project()
        (self.project / "CLAIMS.md").write_text(
            "Read [web] and [section].\n\n"
            "[web]: https://example.com/source\n"
            "[section]: #claims\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertEqual(issues, [])

    def test_validate_does_not_treat_ordinary_brackets_as_shortcut_links(self):
        self.init_project()
        (self.project / "CLAIMS.md").write_text(
            "This [ordinary bracketed text] has no reference definition.\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)

        self.assertEqual(issues, [])

    def test_validate_preserves_collapsed_reference_links(self):
        self.init_project()
        (self.project / "CLAIMS.md").write_text(
            "Read [src][].\n\n[src]: sources/missing.md\n",
            encoding="utf-8",
        )

        issues = ROUTE_CLI.validate_route(self.project)
        broken = [issue for issue in issues if issue.code == "broken-link"]

        self.assertEqual(len(broken), 1)
        self.assertIn("sources/missing.md", broken[0].message)
