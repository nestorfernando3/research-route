# Changelog

All notable changes to this project are documented here.

## Unreleased

### Cleaner release prose

- Blocked local research paths, bibliography and matrix filenames, source-card and work-item identifiers, access-state labels, and pending-verification language from publication prose.
- Required search and verification history to be rewritten as scholarly method before release.
- Added a regression case based on an observed traceability leak in a rendered manuscript.

### Stronger argument and release gates

- Required structured claim records at argument and release checkpoints, reconciled `CLAIMS.md` with `claims/`, and linked claim evidence to existing source cards.
- Blocked unresolved manuscript-targeted claims and orphan PDF, DOCX, and HTML artifacts at release.
- Checked release scaffolding and declared word counts against the artifact.
- Bound release approval to current source-manuscript and DOCX hashes, and kept material review debt blocking the argument review.
- Made failed `advance` calls validate their output before creating work state.
- Added regression tests for stale approval, unsafe release paths, deferred material work, partial `advance` state, and file-backed handoff replay; the suite now passes 114 tests.

## [Research Route Slim — 2026-08-08]

### Faster everyday work

- Added an adaptive route that moves routine exploration quickly and reserves deep checks for decisions that can damage the paper.
- Added `advance` for recording a small result in one command.
- Grouped deferred work into two reviews: one for argument and evidence, and one for final release quality.
- A local replay of five routine tasks used 55.6% fewer commands and 54.6% less elapsed time than the detailed route.

### Cleaner academic manuscripts

- Added prose checks for internal file names, scripts, version labels, ledger fragments, telegraphic sentences, and promotional or combative language.
- Added release checks for Markdown, text, LaTeX, and DOCX artifacts.
- Kept the final manuscript separate from research ledgers, reproducibility materials, and internal production notes.
- Added progressive venue work: three full texts can support an early orientation; ten are required before submission.

### Safer project state

- Added schema v2 with structured claims, release records, risk levels, verification, review debt, and author approval.
- Added `research`, `venue`, `prose`, `release`, and `submission` checkpoints.
- Added safe v1 migration with a mandatory dry run, legacy-cycle normalization, handoff refresh, and explicit privacy blocks.
- Existing schema-v1 projects remain readable until their owner chooses to migrate.

### Validation

- 100 automated tests pass.
- Skill validation and Python compilation pass.
- Migration and adaptive-route replays pass on temporary copies of PAIDEIA, *Suicidal Empathy*, and the fascism project. Existing parallel state and private material remain visible as intentional blocks.

## [Research Route Slim — 2026-07-18]

### Added

- Published `research-route-slim`, a compact 800-word variant with decision-first responses.
- Added public six-scenario benchmark evidence: median 16.5/20 and zero critical failures.
- Updated installation instructions and agent metadata for the Slim variant.

### Validation

- 86 tests pass.
- Skill validation passes.
- All six Slim scenario scores match their selected GREEN scores.
- No superiority claim over the original Research Route version is made.
