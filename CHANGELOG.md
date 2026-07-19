# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Changed

- Restored the executable `new → claim → work → complete` lifecycle and made `release` the unfinished-work operation.
- Added privacy-boundary validation for legacy `RESEARCHER.md` private sections without echoing their contents.
- Added structural validation and the deterministic `--checkpoint handoff` readiness scope.
- Removed the unused migration framework and CLI command; schema version remains `1`.
- Narrowed activation guidance, made orientation proportional, and documented macOS/Linux support boundaries.

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
