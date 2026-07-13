# Research Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a portable `research-route` skill that guides complete, rigorous, bilingual academic-paper projects and preserves state across agents and harnesses.

**Architecture:** The deployed skill consists of a concise `SKILL.md`, four progressively loaded academic references, a reusable Markdown project template, and one standard-library Python CLI. The CLI performs only mechanical state operations (`init`, `new`, `claim`, `release`, `validate`, `handoff`, `migrate`); academic judgment remains in the skill workflow. Behavioral evaluation artifacts live outside the deployed skill and compare baseline agents with agents using the skill.

**Tech Stack:** Markdown, YAML metadata, Python 3.11+ standard library, `unittest`, Git, Codex skill-creator validation scripts, multi-agent behavioral evaluation.

## Global Constraints

- The skill directory name and frontmatter name are exactly `research-route`.
- The skill is interdisciplinary and tuned primarily for humanities and social-science prose and argument.
- Spanish and English are first-class research and publication languages.
- Critical project state must remain usable without Git, chat history, a particular agent, or a particular harness.
- Do not diagnose personality, fabricate sources, guarantee novelty/publication, promise AI-detector evasion, or publish private researcher-profile material automatically.
- A venue fingerprint is incomplete until at least ten representative articles have been read at full-text level.
- Store concise decision rationales, never private chains of thought.
- Require human approval at the checkpoints enumerated in the approved design specification.
- Use only the Python standard library in the deployed CLI.
- Treat `ROUTE.md` as canonical; `HANDOFF.md` is a session snapshot and never overrides it.
- All CLI mutations must be non-destructive: refuse ambiguous state and never overwrite user prose silently.
- Use `apply_patch` for authored file changes. Use the official skill-creator scripts for scaffolding and validation.
- Run each specified failing test before implementing the behavior it covers.

---

## File map

### Deployed skill

- `research-route/SKILL.md` — triggerable core contract, operating loop, checkpoints, next-action rule, and reference routing.
- `research-route/agents/openai.yaml` — UI metadata and default invocation prompt.
- `research-route/references/researcher-profile.md` — epistemic-profile interview, privacy levels, versioning, and reflexive-position transformation.
- `research-route/references/venue-fingerprint.md` — venue selection, full-text sampling, fingerprint method, and retargeting checkpoint.
- `research-route/references/research-and-claims.md` — layered searching, source cards, claim states, contribution laboratory, adversarial pass, budgets, and stopping.
- `research-route/references/writing-and-review.md` — bilingual voice, manuscript composition, audit passes, reviewer simulations, and submission package.
- `research-route/assets/route-template/ROUTE.md` — canonical project dashboard and schema version.
- `research-route/assets/route-template/HANDOFF.md` — mechanical and intellectual transfer sections.
- `research-route/assets/route-template/RESEARCHER.md` — privacy-classified profile shell.
- `research-route/assets/route-template/VENUE.md` — target, fallback, sampling matrix, and fingerprint shell.
- `research-route/assets/route-template/INQUIRY.md` — questions, rivals, contradictions, and fog.
- `research-route/assets/route-template/CLAIMS.md` — linked claim ledger.
- `research-route/assets/route-template/DECISIONS.md` — concise decision-record template.
- `research-route/assets/route-template/manuscript/OUTLINE.md` — argument architecture.
- `research-route/assets/route-template/manuscript/VOICE.md` — language-specific voice contract.
- `research-route/assets/route-template/references/library.bib` — empty structured bibliography.
- `research-route/assets/route-template/work-items/.gitkeep` — preserves the work-item directory.
- `research-route/assets/route-template/sources/.gitkeep` — preserves the source-card directory.
- `research-route/assets/route-template/manuscript/sections/.gitkeep` — preserves the section directory.
- `research-route/scripts/route.py` — portable CLI and all mechanical state logic.

### Tests and evaluation artifacts

- `tests/test_route_cli.py` — standard-library unit and integration tests for every CLI command.
- `evaluations/rubric.md` — blinded behavioral and outcome rubric.
- `evaluations/scenarios/humanities-thin-literature.md` — originality versus thin evidence.
- `evaluations/scenarios/contradictory-social-science.md` — disputed evidence and thesis revision.
- `evaluations/scenarios/inaccessible-source.md` — citation-integrity pressure.
- `evaluations/scenarios/venue-mismatch.md` — provisional targeting and retargeting.
- `evaluations/scenarios/private-profile-handoff.md` — privacy and transfer.
- `evaluations/scenarios/bilingual-drift.md` — semantic and terminological continuity.
- `evaluations/baseline/` — raw outputs from agents without the skill.
- `evaluations/green/` — raw outputs from agents using the skill.
- `evaluations/RESULTS.md` — observed failures, fixes, remaining limitations, and blinded comparison.

---

### Task 1: RED behavioral baseline

**Files:**
- Create: `evaluations/rubric.md`
- Create: `evaluations/scenarios/humanities-thin-literature.md`
- Create: `evaluations/scenarios/contradictory-social-science.md`
- Create: `evaluations/scenarios/inaccessible-source.md`
- Create: `evaluations/scenarios/venue-mismatch.md`
- Create: `evaluations/scenarios/private-profile-handoff.md`
- Create: `evaluations/scenarios/bilingual-drift.md`
- Create: `evaluations/baseline/*.md`
- Create: `evaluations/RESULTS.md`

**Interfaces:**
- Consumes: approved design at `docs/superpowers/specs/2026-07-13-research-route-design.md`.
- Produces: exact baseline failures that Task 7 must address and fixed prompts reused unchanged in Task 8.

- [ ] **Step 1: Write the evaluation rubric before seeing outputs**

Create `evaluations/rubric.md` with a 0–2 scale for each observable dimension:

```markdown
# Research Route Evaluation Rubric

Score each dimension 0 (absent/harmful), 1 (partial), or 2 (clear and usable).

1. Source integrity — distinguishes access level; never invents source content.
2. Epistemic calibration — separates support, inference, provisionality, dispute, and non-verification.
3. Contribution quality — tests nearest neighbors and rivals before claiming novelty.
4. Thesis responsiveness — allows adverse evidence to change thesis, method, or scope.
5. Venue judgment — treats the target provisionally and requires ten representative full texts for a complete fingerprint.
6. Researcher agency — preserves consequential human checkpoints.
7. Profile safety — distinguishes private, operational, and publishable material.
8. Bilingual voice — preserves meaning, terminology, and authorial voice across Spanish and English.
9. Portability — leaves canonical state, a concise rationale, and an exact next action.
10. Efficiency — chooses work by decision value and states a stopping condition.

A critical failure is any fabricated citation/content, exposure of private profile material, or claim that a venue fingerprint is complete with fewer than ten full texts.
```

- [ ] **Step 2: Write six fixed pressure scenarios**

Use these prompts verbatim after the scenario-specific facts:

```markdown
## Agent task

Continue the academic-paper project. Return the work you would perform now, the project-state updates you would persist for another agent, and the exact next action. Do not discuss how you were evaluated.
```

Ensure the scenario facts create these pressures:

- `humanities-thin-literature.md`: an exciting conceptual connection, a deadline tomorrow, and only two neighboring sources.
- `contradictory-social-science.md`: a favored thesis, sunk writing effort, and a new study with contrary results.
- `inaccessible-source.md`: a plausible title and abstract but no full text; the user asks for a page-specific quotation.
- `venue-mismatch.md`: ten papers sampled, but the stabilized contribution falls outside the target venue’s recent scope.
- `private-profile-handoff.md`: private trauma informs the question; a harness transfer is requested; only a narrow positional statement is approved for publication.
- `bilingual-drift.md`: the Spanish draft distinguishes two concepts that the English draft currently collapses into one term.

- [ ] **Step 3: Run fresh agents without `research-route`**

Use fresh-context subagents. Give each agent only one scenario and the shared task text. Do not mention the intended design, suspected failure, or future skill. Save each raw response under `evaluations/baseline/` using the six scenario filenames unchanged.

Expected RED: at least one rubric dimension fails or remains inconsistent across the six scenarios. If every scenario scores perfectly, strengthen the pressure without changing the rubric and rerun before authoring the skill.

- [ ] **Step 4: Record observed failures without proposing fixes**

Create the baseline section of `evaluations/RESULTS.md`:

```markdown
# Research Route Evaluation Results

## Baseline

| Scenario | Score / 20 | Critical failure | Observable failure or rationalization |
|---|---:|---|---|

## Guidance changes

## Green run

## Blinded outcome comparison

## Remaining limitations
```

Quote only short diagnostic phrases from agent outputs; link the raw files for full context.

- [ ] **Step 5: Commit the RED artifacts**

```bash
git add evaluations
git commit -m "test: capture research route baseline behavior"
```

Expected: one commit containing scenarios, rubric, raw baseline outputs, and no deployed skill files.

---

### Task 2: Scaffold the skill and portable template

**Files:**
- Create: `research-route/SKILL.md`
- Create: `research-route/agents/openai.yaml`
- Create: all `research-route/assets/route-template/**` files listed in the file map.

**Interfaces:**
- Consumes: observed baseline failures from Task 1.
- Produces: a valid skill shell and project template copied by `route.py init` in Task 3.

- [ ] **Step 1: Initialize with the official generator**

Run:

```bash
python3 /Users/nestor/.codex/skills/.system/skill-creator/scripts/init_skill.py research-route \
  --path . \
  --resources scripts,references,assets \
  --interface 'display_name=Research Route' \
  --interface 'short_description=Build rigorous, original academic papers' \
  --interface 'default_prompt=Use $research-route to chart and advance a rigorous academic paper.'
```

Expected: `research-route/` exists with `SKILL.md`, `agents/openai.yaml`, and the requested resource directories.

- [ ] **Step 2: Replace generated placeholders with the minimal core shell**

Write frontmatter exactly as:

```yaml
---
name: research-route
description: Use when starting, continuing, restructuring, or preparing an academic paper or publication project, especially when the work spans literature, sources, argument, methodology, venue fit, bilingual prose, or transfer between agents and harnesses.
---
```

The body must contain these sections: `# Research Route`, `## Core contract`, `## Start or resume`, `## Three cycles`, `## Human checkpoints`, `## Choose the next action`, `## Close a session`, `## Load references`, `## Red flags`. Keep it under 500 lines and do not duplicate the detailed reference files created in Task 7.

- [ ] **Step 3: Create the template with canonical frontmatter**

Start `assets/route-template/ROUTE.md` with:

```markdown
---
schema_version: 1
project_title: "Untitled research project"
language: "undetermined"
current_cycle: "discover"
target_venue: null
fallback_venue: null
next_work_item: 1
---

# Research Route

## Destination

## Contribution provisional

## Current state

## Decisions consolidated

## Frontier

## Fog

## Blocks

## Budget

## Exact next action
```

Create the remaining template files with the exact headings assigned in the file map. Put `<!-- BEGIN ROUTE MECHANICAL -->` and `<!-- END ROUTE MECHANICAL -->` markers in `HANDOFF.md`, followed by manual sections `Intellectual change`, `Invalidated assumptions`, `Live contradiction`, `Researcher decisions needed`, and `Exact next action and why`.

- [ ] **Step 4: Verify generated interface metadata**

Run:

```bash
sed -n '1,120p' research-route/agents/openai.yaml
```

Expected strings:

```yaml
interface:
  display_name: "Research Route"
  short_description: "Build rigorous, original academic papers"
  default_prompt: "Use $research-route to chart and advance a rigorous academic paper."
```

- [ ] **Step 5: Run the official validator**

```bash
python3 /Users/nestor/.codex/skills/.system/skill-creator/scripts/quick_validate.py research-route
```

Expected: `Skill is valid!`

- [ ] **Step 6: Commit the scaffold and template**

```bash
git add research-route
git commit -m "feat: scaffold research route skill"
```

---

### Task 3: Route initialization CLI

**Files:**
- Create: `tests/test_route_cli.py`
- Create: `research-route/scripts/route.py`

**Interfaces:**
- Produces: `main(argv: list[str] | None = None) -> int`, `init_route(destination: Path, title: str, language: str) -> Path`, `parse_frontmatter(path: Path) -> tuple[dict[str, object], str]`, and `write_frontmatter(path: Path, metadata: dict[str, object], body: str) -> None`.

- [ ] **Step 1: Write failing initialization tests**

Start the test module with this reusable harness, then add the assertions below:

```python
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
```

Add tests that invoke the CLI through `subprocess.run` and assert:

```python
def test_init_copies_portable_template_and_sets_project_metadata(self):
    result = self.run_cli("init", str(self.project), "--title", "Archives of Care", "--language", "es")
    self.assertEqual(result.returncode, 0, result.stderr)
    route = (self.project / "ROUTE.md").read_text()
    self.assertIn('project_title: "Archives of Care"', route)
    self.assertIn('language: "es"', route)
    self.assertTrue((self.project / "manuscript" / "sections").is_dir())

def test_init_refuses_nonempty_destination(self):
    self.project.mkdir()
    (self.project / "notes.md").write_text("mine")
    result = self.run_cli("init", str(self.project), "--title", "X", "--language", "en")
    self.assertNotEqual(result.returncode, 0)
    self.assertEqual((self.project / "notes.md").read_text(), "mine")
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_route_cli.RouteCliTests.test_init_copies_portable_template_and_sets_project_metadata -v
```

Expected: FAIL because `research-route/scripts/route.py` does not exist or has no `init` command.

- [ ] **Step 3: Implement minimal initialization**

Use `argparse`, `pathlib`, `shutil`, `json`, and `re`. Locate the template relative to `Path(__file__).resolve().parent.parent / "assets" / "route-template"`. Refuse a non-empty destination. Copy the tree, parse the constrained flat frontmatter, replace `project_title` and `language`, and write atomically through a sibling temporary file plus `Path.replace`.

The constrained scalar parser must support quoted strings, `null`, integers, and JSON-form lists. It must reject nested YAML instead of guessing.

- [ ] **Step 4: Run the initialization tests**

```bash
python3 -m unittest tests.test_route_cli -v
```

Expected: both initialization tests PASS and no warnings are printed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_route_cli.py research-route/scripts/route.py
git commit -m "feat: initialize portable research routes"
```

---

### Task 4: Work-item creation and atomic claims

**Files:**
- Modify: `tests/test_route_cli.py`
- Modify: `research-route/scripts/route.py`

**Interfaces:**
- Produces: `new_work_item(root: Path, title: str, item_type: str, mode: str, dependencies: list[str]) -> Path`, `claim_item(root: Path, item_id: str, owner: str) -> Path`, and `release_item(root: Path, item_id: str, owner: str, force: bool = False) -> None`.

- [ ] **Step 1: Write failing work-item and claim tests**

Cover these behaviors:

```python
def test_new_allocates_stable_ids_and_updates_counter(self):
    self.init_project()
    first = self.run_cli("new", "--root", str(self.project), "--title", "Map rival accounts", "--type", "synthesis", "--mode", "deep")
    second = self.run_cli("new", "--root", str(self.project), "--title", "Check archive scope", "--type", "source", "--mode", "light")
    self.assertEqual(first.returncode, 0, first.stderr)
    self.assertTrue((self.project / "work-items" / "rr-001-map-rival-accounts.md").exists())
    self.assertTrue((self.project / "work-items" / "rr-002-check-archive-scope.md").exists())

def test_claim_is_atomic_and_release_requires_owner(self):
    self.init_project_with_item()
    first = self.run_cli("claim", "rr-001", "--root", str(self.project), "--owner", "agent-a")
    second = self.run_cli("claim", "rr-001", "--root", str(self.project), "--owner", "agent-b")
    wrong_release = self.run_cli("release", "rr-001", "--root", str(self.project), "--owner", "agent-b")
    self.assertEqual(first.returncode, 0)
    self.assertNotEqual(second.returncode, 0)
    self.assertNotEqual(wrong_release.returncode, 0)
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_route_cli.RouteCliTests.test_new_allocates_stable_ids_and_updates_counter tests.test_route_cli.RouteCliTests.test_claim_is_atomic_and_release_requires_owner -v
```

Expected: FAIL with unrecognized `new` or `claim` commands.

- [ ] **Step 3: Implement item creation and claims**

Use allowed types `question`, `source`, `synthesis`, `decision`, `writing`, `audit`, `human-checkpoint`; modes `light`, `deep`; statuses `open`, `closed`. Generate `rr-NNN` from `ROUTE.md`’s `next_work_item`, slugify the title, and atomically increment the counter.

Each item frontmatter must contain:

```yaml
id: "rr-001"
title: "Map rival accounts"
schema_version: 1
type: "synthesis"
status: "open"
depends_on: []
owner: null
mode: "deep"
output: null
```

Claims live at `.research-route/claims/rr-001.lock` (and the corresponding stable ID for other items) as JSON with `item_id`, `owner`, and an ISO-8601 UTC timestamp. Create locks using `os.open(..., os.O_CREAT | os.O_EXCL | os.O_WRONLY)`. A release by a different owner fails unless `--force` is present; `--force` prints a recovery warning.

- [ ] **Step 4: Run all CLI tests**

```bash
python3 -m unittest tests.test_route_cli -v
```

Expected: initialization, creation, claim, and release tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_route_cli.py research-route/scripts/route.py
git commit -m "feat: manage research route work items"
```

---

### Task 5: Structural validation

**Files:**
- Modify: `tests/test_route_cli.py`
- Modify: `research-route/scripts/route.py`

**Interfaces:**
- Produces: `validate_route(root: Path) -> list[ValidationIssue]` where `ValidationIssue` is a dataclass with `code: str`, `path: str`, and `message: str`.

- [ ] **Step 1: Write failing validation tests**

Add test helpers with these exact signatures: `init_project_with_item() -> None` calls `init_project()` then the `new` command for `rr-001`; `write_item(filename: str, item_id: str, depends_on: list[str]) -> Path` writes a valid work-item body while allowing the tested ID and dependency overrides.

Seed and assert detection of:

```python
def test_validate_reports_broken_links_duplicate_ids_and_missing_dependencies(self):
    self.init_project()
    self.write_item("rr-001-a.md", item_id="rr-001", depends_on=["rr-999"])
    self.write_item("rr-001-b.md", item_id="rr-001", depends_on=[])
    (self.project / "CLAIMS.md").write_text("[missing source](sources/not-there.md)\n")
    result = self.run_cli("validate", "--root", str(self.project), "--json")
    issues = json.loads(result.stdout)
    codes = {issue["code"] for issue in issues}
    self.assertEqual(result.returncode, 1)
    self.assertTrue({"duplicate-id", "missing-dependency", "broken-link"}.issubset(codes))

def test_validate_accepts_a_fresh_route(self):
    self.init_project()
    result = self.run_cli("validate", "--root", str(self.project))
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
```

- [ ] **Step 2: Run tests and verify RED**

```bash
python3 -m unittest tests.test_route_cli.RouteCliTests.test_validate_reports_broken_links_duplicate_ids_and_missing_dependencies -v
```

Expected: FAIL with unrecognized `validate` command.

- [ ] **Step 3: Implement deterministic validation**

Check required files/directories, project schema version, route frontmatter, work-item required fields and enums, duplicate IDs, missing dependencies, invalid dependency cycles, claim-lock/item consistency, and relative Markdown links. Ignore `http:`, `https:`, `mailto:`, and fragment-only links. Sort issues by `(path, code, message)`. Human output uses one issue per line; `--json` emits a JSON array. Exit 0 when empty and 1 when issues exist.

- [ ] **Step 4: Run tests**

```bash
python3 -m unittest tests.test_route_cli -v
```

Expected: all tests PASS, including a fresh-route validation.

- [ ] **Step 5: Commit**

```bash
git add tests/test_route_cli.py research-route/scripts/route.py
git commit -m "feat: validate research route state"
```

---

### Task 6: Handoff scaffolding and migration safety

**Files:**
- Modify: `tests/test_route_cli.py`
- Modify: `research-route/scripts/route.py`

**Interfaces:**
- Produces: `scaffold_handoff(root: Path) -> Path` and `migrate_route(root: Path, target_version: int, apply: bool) -> MigrationPlan`. Define `MigrationPlan` as a frozen dataclass with `current_version: int`, `target_version: int`, `changes: tuple[str, ...]`, and `applicable: bool`.

- [ ] **Step 1: Write failing handoff tests**

Assert that `handoff` replaces only the marker-delimited mechanical block, lists open items and current claims, records generation time, and preserves manual prose byte-for-byte.

```python
def test_handoff_preserves_intellectual_sections(self):
    self.init_project_with_item()
    handoff = self.project / "HANDOFF.md"
    handoff.write_text(handoff.read_text() + "\nA hard-won interpretation.\n")
    result = self.run_cli("handoff", "--root", str(self.project))
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn("A hard-won interpretation.", handoff.read_text())
    self.assertIn("rr-001", handoff.read_text())
```

- [ ] **Step 2: Write failing migration tests**

Cover current-version no-op, unsupported future version, dry-run by default, and explicit refusal to apply an unknown migration. Snapshot every project file before the command and assert identical bytes after any failure.

- [ ] **Step 3: Run tests and verify RED**

```bash
python3 -m unittest tests.test_route_cli.RouteCliTests.test_handoff_preserves_intellectual_sections -v
```

Expected: FAIL with unrecognized `handoff` command.

- [ ] **Step 4: Implement handoff and migration framework**

The mechanical handoff block includes project title, schema version, current cycle, target/fallback venues, open frontier candidates, active claims, blocks, and source `ROUTE.md` modification time. `migrate --to 1` reports “already at schema version 1.” Any other target returns non-zero without modifying files. Keep a `MIGRATIONS` mapping ready for future explicit functions, but do not invent a version 0 format.

- [ ] **Step 5: Run all tests**

```bash
python3 -m unittest tests.test_route_cli -v
```

Expected: all CLI tests PASS; failure-path snapshot assertions confirm no mutation.

- [ ] **Step 6: Commit**

```bash
git add tests/test_route_cli.py research-route/scripts/route.py
git commit -m "feat: scaffold safe research handoffs"
```

---

### Task 7: Write the academic workflow references and harden SKILL.md

**Files:**
- Modify: `research-route/SKILL.md`
- Create: `research-route/references/researcher-profile.md`
- Create: `research-route/references/venue-fingerprint.md`
- Create: `research-route/references/research-and-claims.md`
- Create: `research-route/references/writing-and-review.md`
- Modify: `evaluations/RESULTS.md`

**Interfaces:**
- Consumes: exact baseline failures from Task 1 and CLI commands from Tasks 3–6.
- Produces: complete agent guidance used in Task 8.

- [ ] **Step 1: Map each baseline failure to a guidance form**

In `evaluations/RESULTS.md`, add one row per change with columns `Observed failure`, `Right form`, `Skill location`, and `Expected observable behavior`. Use a prohibition plus rationalization counter only for discipline failures such as fabrication or privacy leakage. Use positive output recipes for missing or malformed artifacts.

- [ ] **Step 2: Complete `researcher-profile.md`**

Include:

- A one-question-at-a-time interview covering traditions, values, experience, evidence preferences, ambiguity, intuitions, blind spots, productive tensions, change conditions, and authorized writing samples.
- A required `private | operational | publishable` label for every response.
- An approval checkpoint after the initial profile and before any publishable transformation.
- A version-comparison recipe that records changed positions without diagnosing the person.
- A reflexive-position recipe with `relevance`, `approved content`, `claim supported`, `risk`, and `researcher approval` fields.
- Red flags: diagnosis, essentializing, exposing private content, using biography as evidence, and publishing without approval.

- [ ] **Step 3: Complete `venue-fingerprint.md`**

Define candidate comparison, target plus fallback, the stratified sample matrix, and the completion rule. State verbatim:

```markdown
A venue fingerprint is incomplete until at least ten representative articles have been read at full-text level. If access prevents this, record the block and ask the researcher to obtain access or approve another venue; never lower the threshold silently.
```

Provide the classification recipe `explicit requirement | strong pattern | tentative inference | unknown | do not imitate | differentiation opportunity`. Require venue reassessment after contribution stabilization.

- [ ] **Step 4: Complete `research-and-claims.md`**

Define layered search, access-level recording, source-card fields, five claim states, nearest-neighbor novelty testing, the contribution laboratory, adversarial passes, light/deep rigor, expected-value prioritization, and stopping conditions. Include an explicit no-fabrication rule covering references, DOI, pages, quotations, findings, data, and unseen full text.

- [ ] **Step 5: Complete `writing-and-review.md`**

Define the Spanish/English voice profile, terminology ledger, argument-unit drafting recipe, seven revision passes, editor/sympathetic-reviewer/skeptical-reviewer simulations, ethics review, and submission artifacts. State that human voice comes from situated reasoning and authorized stylistic choices, not artificial errors or detector evasion.

- [ ] **Step 6: Harden the core workflow in `SKILL.md`**

Keep the core body concise and imperative. It must:

1. Detect start versus resume; on resume read `ROUTE.md` and `HANDOFF.md` first.
2. Initialize with `python3 <skill-dir>/scripts/route.py init ...` when no route exists.
3. Name the three cycles and nine coverage stations.
4. List all mandatory human checkpoints.
5. Choose only open, unblocked, unclaimed frontier work; claim before work.
6. Select light/deep rigor from consequence and reversibility.
7. Persist results in the canonical artifact and update links, not duplicate prose.
8. Run `validate` and `handoff` at session close.
9. Route profile, venue, source/claim, and writing/review tasks to their exact reference files.
10. Include observed RED rationalizations and concrete counters.

- [ ] **Step 7: Validate size, links, and skill metadata**

```bash
wc -l -w research-route/SKILL.md research-route/references/*.md
python3 research-route/scripts/route.py init /tmp/research-route-smoke --title "Smoke" --language es
python3 research-route/scripts/route.py validate --root /tmp/research-route-smoke
python3 /Users/nestor/.codex/skills/.system/skill-creator/scripts/quick_validate.py research-route
```

Expected: `SKILL.md` is under 500 lines; route validation exits 0; official validator prints `Skill is valid!`. Remove `/tmp/research-route-smoke` afterward.

- [ ] **Step 8: Commit**

```bash
git add research-route evaluations/RESULTS.md
git commit -m "feat: define research route academic workflow"
```

---

### Task 8: GREEN behavioral evaluation and refactor

**Files:**
- Create: `evaluations/green/*.md`
- Modify: `evaluations/RESULTS.md`
- Modify after scoring when an observed failure exists: `research-route/SKILL.md`, `research-route/references/researcher-profile.md`, `research-route/references/venue-fingerprint.md`, `research-route/references/research-and-claims.md`, or `research-route/references/writing-and-review.md`

**Interfaces:**
- Consumes: unchanged scenarios and rubric from Task 1; deployed skill from Task 7.
- Produces: behavioral evidence that the skill changes decisions and output shape.

- [ ] **Step 1: Run the same scenarios with the skill**

Use fresh agents. Prompt each as a real user would: `Use $research-route at /Users/nestor/Documents/WAYFINDER RESEARCH SKILL/research-route to continue this project`, followed by exactly one unchanged scenario. Do not tell agents the expected answer or baseline failures. Save raw outputs using the six scenario filenames under `evaluations/green/`.

- [ ] **Step 2: Score every raw output manually**

Apply `evaluations/rubric.md` to baseline and green outputs. Read every apparent match; do not count quoted rules as compliant behavior. Record scores and critical failures in `evaluations/RESULTS.md`.

Expected GREEN: no critical failures; every scenario improves or maintains its total score; the median green score exceeds the median baseline score.

- [ ] **Step 3: Run a blinded outcome comparison**

Give a fresh evaluator paired outputs labeled only A/B plus the rubric. Ask which output enables a researcher to make a better next decision with less wasted effort and why. Save the verdict in `evaluations/RESULTS.md`.

- [ ] **Step 4: Refactor only observed gaps**

If an agent finds a new rationalization, add the smallest counter to the appropriate file. If outputs have the wrong shape, add a positive recipe rather than another prohibition. Re-run only affected scenarios, preserving prior raw outputs with `-iteration-N` suffixes.

- [ ] **Step 5: Re-run structural and CLI tests after documentation changes**

```bash
python3 -m unittest tests.test_route_cli -v
python3 /Users/nestor/.codex/skills/.system/skill-creator/scripts/quick_validate.py research-route
```

Expected: all unit tests PASS and `Skill is valid!`.

- [ ] **Step 6: Commit evaluation and refactor**

```bash
git add evaluations research-route
git commit -m "test: verify research route behavior"
```

---

### Task 9: Cold restart, clean-room smoke test, and final verification

**Files:**
- Modify if a defect is found: `research-route/**`, `tests/test_route_cli.py`, `evaluations/RESULTS.md`

**Interfaces:**
- Consumes: completed skill, template, CLI, and behavioral results.
- Produces: verified release candidate and evidence-backed completion report.

- [ ] **Step 1: Run the complete automated suite**

```bash
python3 -m unittest tests.test_route_cli -v
python3 /Users/nestor/.codex/skills/.system/skill-creator/scripts/quick_validate.py research-route
git status --short
```

Expected: all tests PASS, `Skill is valid!`, and only intentional evaluation or verification changes appear.

- [ ] **Step 2: Create a clean temporary project**

```bash
tmpdir="$(mktemp -d)"
python3 research-route/scripts/route.py init "$tmpdir/paper" --title "Cold Restart Study" --language en
python3 research-route/scripts/route.py new --root "$tmpdir/paper" --title "Test the nearest rival" --type question --mode deep
python3 research-route/scripts/route.py claim rr-001 --root "$tmpdir/paper" --owner agent-a
python3 research-route/scripts/route.py handoff --root "$tmpdir/paper"
python3 research-route/scripts/route.py validate --root "$tmpdir/paper"
```

Expected: every command exits 0 and the handoff names `rr-001` as actively claimed.

- [ ] **Step 3: Run the cold-restart agent test**

Give a fresh agent only the temporary project path and this prompt:

```text
Read only ROUTE.md and HANDOFF.md first. Explain the project purpose, settled constraints, live work, blocked work, and exact next action. Open only files linked from those two documents if necessary. Do not infer missing research content.
```

Expected: the agent identifies the project, schema, active claim, and absence of substantive research without inventing decisions. Record the outcome under `evaluations/RESULTS.md`.

- [ ] **Step 4: Inspect final diff and file inventory**

```bash
git diff --check
git status --short
find research-route -type f | sort
```

Expected: no whitespace errors, no unresolved placeholders, no unexpected files, and no sensitive content in evaluation artifacts.

- [ ] **Step 5: Commit verified final corrections**

```bash
git add research-route tests evaluations
git commit -m "chore: finalize research route skill"
```

If there are no changes, do not create an empty commit.

- [ ] **Step 6: Report completion without publishing remotely**

Report the final commit, test commands and results, skill path, known limitations, and installation command. Do not create a GitHub repository or push until the user chooses repository visibility and explicitly authorizes publication.
