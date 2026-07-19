# Research Route Slim Improvements — Design Specification

## Purpose

Make Research Route Slim operationally complete, safer by default, and precise about what its tooling validates without expanding its scholarly workflow or adding dependencies.

The work covers all six findings from the 2026-07-19 audit: work-item lifecycle coherence, portable-profile privacy, activation scope, validation semantics, public evidence consistency, and removable technical debt.

## Design principles

1. **Preserve the slim prompt.** `research-route/SKILL.md` remains at or below 800 words.
2. **Make the documented path executable.** An agent can create, claim, complete, validate, and hand off work using documented commands.
3. **Keep private material outside portable state.** No project template invites private disclosure, and diagnostics never echo private text.
4. **Name mechanical guarantees honestly.** Structural checks do not claim to establish scholarly quality or submission readiness.
5. **Preserve compatibility where it carries value.** Existing schema-v1 projects remain usable; dangerous legacy private content becomes an explicit validation error.
6. **Delete speculative machinery.** No migration framework remains until a second schema exists.
7. **Use standard-library Python only.** No runtime or test dependency is added.

## Delivery architecture

The work ships in three independently testable phases. Each phase receives a focused commit and may be reviewed or reverted without requiring the next phase.

### Phase 1: Coherence and privacy

Change prompt metadata, the portable researcher template, privacy validation, README claims, benchmark errata, platform documentation, and repository ignores.

Phase 1 restores the documented `new` command before `claim` and narrows skill activation to sustained or multi-stage paper projects, durable research state, venue or contribution work, bilingual argument revision, and agent/harness transfer. The description explicitly excludes isolated proofreading, citation formatting, one-off summaries, and narrow lookups unless the user names Research Route.

Researcher orientation becomes optional and proportional to methodological or authorial need. User-facing language uses “epistemic and authorial orientation,” never “psychological profile.”

The `RESEARCHER.md` template removes `## Private`. It instead contains a privacy-boundary notice stating that private material remains in a researcher-controlled location outside the portable project root and outside hosted/external prompts.

Default validation reports a privacy error when a legacy `RESEARCHER.md` contains substantive text under `## Private`. Empty content and comments do not trigger the error. The diagnostic names the file and rule but never includes the section contents.

### Phase 2: Work-item lifecycle and honest validation

The supported lifecycle is:

```text
new → claim → work → complete
```

`release` means relinquish unfinished work. `complete` means persist a finished work item and release its active claim.

The new command is:

```bash
python3 <skill-dir>/scripts/route.py complete <item-id> --root <root> --owner <owner> --output <relative-path>
```

`complete` runs under the existing claims guard and:

1. verifies the work item and active claim;
2. verifies that the claim belongs to `owner`;
3. accepts only a non-empty project-relative output path that resolves to an existing regular file inside the opened project root;
4. sets `status` to `closed`, `owner` to the completing owner, and `output` to the normalized relative path;
5. writes the work-item frontmatter atomically;
6. deletes the active claim.

If the process stops after step 5 but before step 6, retrying the same command with the same owner and output succeeds by deleting the matching residual claim. A different owner, a different output, a missing claim on an open item, or an output outside the project remains an error. Diagnostics never alter the work item or claim on validation failure.

Validation has two explicit scopes:

- `route.py validate --root <root>` checks structural integrity only: required paths, supported frontmatter, work-item and dependency consistency, claims, Markdown links, privacy boundary, and handoff freshness.
- `route.py validate --root <root> --checkpoint handoff` runs structural validation plus deterministic transfer checks: a non-empty `ROUTE.md` `Destination`, a non-empty canonical exact next action, and declared content in every intellectual section of `HANDOFF.md`. Sections with no applicable change may say `- None`; the exact next action may not.

The CLI does not add a submission checkpoint. Originality, evidence quality, ethics approval, venue fit, and author approval remain human/reference-driven gates that cannot be established from file shape.

The unused `MigrationPlan`, `MIGRATIONS`, `migrate_route`, `migrate` parser branch, and migration tests are removed. Schema version remains `1`.

### Phase 3: Evaluation and continuous verification

Evaluation expands beyond one-shot proposed state:

1. Add trigger cases for three intended uses and non-trigger cases for isolated proofreading, citation formatting, one-off summary, and narrow lookup.
2. Run a file-backed two-turn route in an external temporary root: initialize, create, claim, persist a real output, complete, update canonical state, generate handoff, and validate the handoff checkpoint.
3. Cold-restart with a fresh agent that receives only the project root and must identify the objective, completed output, settled state, block status, and exact next action without invention.
4. Run three fresh contexts for the inaccessible-source and private-profile sentinels.
5. Run one fresh context for each of the other four existing scenarios.
6. Preserve every raw output and record score vector, total, critical-failure status, word count, decision-first status, and any state mutation performed.

A minimal GitHub Actions workflow runs the Python unit suite and CLI help smoke check on Linux with Python 3.11. The README documents macOS and Linux as supported while `fcntl` and descriptor-relative POSIX operations remain requirements. Windows support is not added.

## File responsibilities

- `research-route/SKILL.md`: activation boundary and executable route commands; no detailed schemas.
- `research-route/assets/route-template/RESEARCHER.md`: safe portable orientation template with no private-content slot.
- `research-route/scripts/route.py`: deterministic lifecycle, privacy, structural, and handoff-readiness checks.
- `tests/test_route_cli.py`: all deterministic CLI and compatibility checks.
- `README.md`: public behavior, support boundary, privacy wording, and evidence claim.
- `CHANGELOG.md`: released behavior and validation evidence.
- `evaluations/`: scenarios, raw outputs, scoring, and provenance.
- `.github/workflows/test.yml`: dependency-free automated unit and smoke checks.
- `.gitignore`: `.DS_Store`, `__pycache__/`, `*.pyc`, `.worktrees/`, and `.superpowers/`.

No new state file or schema field is introduced.

## Error handling and compatibility

- Existing schema-v1 roots with no substantive legacy private section continue to validate.
- Legacy roots containing private text fail safely and receive a non-disclosing instruction to relocate/delete that content under researcher control.
- Existing `release` behavior and ownership checks remain unchanged.
- `complete` never accepts absolute paths, `..` traversal, symlinks, directories, or missing outputs.
- The removed `migrate` command is not retained as a compatibility stub because no migration has ever been available.
- Published raw benchmark artifacts remain immutable. `evaluations/RESULTS.md` records an erratum for false path/provenance statements and excludes those statements from evidence; intellectual answers and scores remain unchanged.

## Testing strategy

Implementation is test-driven. Each behavior begins with one focused failing `unittest`, followed by the minimum implementation and the narrow test run. The full 86-test baseline must remain green except for deliberate migration-test removal, and the final total must include new lifecycle, privacy, checkpoint, and CLI parser coverage.

Required deterministic cases include:

- fresh initialization produces no private-content section;
- substantive legacy private content fails without appearing in diagnostics;
- `complete` closes an owned item and persists its real output;
- wrong-owner, missing-output, external-path, directory, and symlink completion fail without mutation;
- retry after a simulated post-write/pre-unlink interruption succeeds;
- default validation accepts structurally valid incomplete intellectual state and identifies itself as structural in help/docs;
- handoff checkpoint rejects each missing intellectual requirement and accepts a completed handoff;
- CLI help exposes `new`, `claim`, `complete`, `release`, `validate`, and `handoff`, but not `migrate`.

## Acceptance criteria

- All deterministic tests pass on Python 3.11.
- `quick_validate.py research-route` passes.
- `research-route/SKILL.md` contains no more than 800 words.
- No new dependency or schema version is introduced.
- No private content appears in output, diagnostics, handoffs, or evaluation artifacts.
- The selected six scenario scores remain within one point of their current values and retain zero critical failures.
- README, changelog, evaluation results, and raw-artifact provenance agree.
- Each phase is independently testable and committed separately.

## Non-goals

- Windows support.
- Schema v2 or a migration system.
- Automated assessment of novelty, ethics approval, evidence quality, or submission readiness.
- A general workflow engine or database.
- Additional researcher-profile questions or mandatory profiling.
- Rewriting historical evaluation answers to improve their scores.
