# Research Route Slim

<p align="center">
  <img src="assets/research-route-logo.png" alt="Research Route logo" width="720">
</p>

Research Route Slim is a compact, adaptive academic-writing skill for sustained paper projects: it turns a research question into durable state that can survive agent switches, harness changes, and long revision cycles while batching non-critical review work. It is not intended for isolated proofreading, citation formatting, one-off summaries, or narrow lookups unless the user explicitly names Research Route.

It is tuned primarily for humanities and social-science prose and argument, but it works anywhere the work depends on judgment, source discipline, and editorial fit.

## What It Is

Research Route Slim is not a one-shot prompt. It is a compact route for building a paper with structure, memory, and accountability:

- it helps you record optional epistemic and authorial orientation when it materially serves the project;
- it helps you orient to a journal quickly and complete the full venue fingerprint before submission;
- it keeps claims, evidence, decisions, and open questions in canonical Markdown state;
- it helps you write in a human voice without pretending to be human;
- it keeps the project portable so another agent or harness can continue it cleanly.

## Why It Exists

Most AI writing workflows are optimized for a single response. Research Route Slim preserves the full academic route while keeping the operating prompt compact: question, source work, contribution, thesis, prose, revision, and handoff.

The goal is not just speed. The goal is a paper that can actually be defended: original enough to matter, careful enough to trust, and organized enough to survive collaboration.

## What It Helps You Do

- record authorized epistemic and authorial orientation while keeping private material outside the portable project root and hosted prompts;
- choose a target venue and fingerprint its tone, scope, and expectations from representative full-text articles;
- test the paper against nearest neighbors, strongest rivals, and simpler explanations before calling it novel;
- preserve project state in `ROUTE.md`, `HANDOFF.md`, claims, decisions, and source cards;
- keep Spanish and English terminology aligned when the project moves between languages;
- move step by step so the work stays efficient, auditable, and easy to resume.

## Key Features

- Portable project state that survives agent or harness switches.
- Venue-first adaptation, including a fingerprint built from at least 10 full-text articles.
- Human checkpoints for consequential decisions.
- Evidence and claim discipline that separates supported, inferred, provisional, disputed, and unverified.
- A contribution laboratory that pressure-tests novelty before it becomes prose.
- Bilingual voice support for humanities and social-science writing.
- A small standard-library Python CLI for the mechanical parts of project state.
- Adaptive risk levels that keep critical verification immediate and batch material review into argument and release passes.

The CLI supports the detailed lifecycle `new`, `claim`, `complete`, and `release`, plus the compact `advance` path for routine work. Validation is deterministic: it checks file shape, consistency, claims, prose, venue, release artifacts, and approval records. Focused checkpoints cover argument, research, prose, venue, handoff, release, and submission; ethics, bibliography, reviewer judgment, and final author approval remain human gates.

New projects should initialize with `--schema-version 2`. The default `init` mode remains schema v1 for compatibility with older automation; migrate legacy roots explicitly after a dry run.

## Installation

Clone the slim publication branch once into a stable local directory, then link the full `research-route/` folder into the skill path for each harness. Run the clone block first, even if you will only use the Claude Code or OpenCode link:

### Codex

```bash
mkdir -p ~/.local/share
git clone --branch codex/research-route-slim https://github.com/nestorfernando3/research-route.git ~/.local/share/research-route-slim
mkdir -p ~/.codex/skills
if [ ! -e ~/.codex/skills/research-route-slim ] && [ ! -L ~/.codex/skills/research-route-slim ]; then ln -s ~/.local/share/research-route-slim/research-route ~/.codex/skills/research-route-slim; fi
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
if [ ! -e ~/.claude/skills/research-route-slim ] && [ ! -L ~/.claude/skills/research-route-slim ]; then ln -s ~/.local/share/research-route-slim/research-route ~/.claude/skills/research-route-slim; fi
```

### OpenCode

```bash
mkdir -p ~/.config/opencode/skills
if [ ! -e ~/.config/opencode/skills/research-route-slim ] && [ ! -L ~/.config/opencode/skills/research-route-slim ]; then ln -s ~/.local/share/research-route-slim/research-route ~/.config/opencode/skills/research-route-slim; fi
```

If you already installed the skill for Claude Code, OpenCode can also discover Claude-compatible skill locations in many setups, so you may not need a second copy.

Create release approval with the CLI so it records hashes for the current source manuscript and DOCX; editing either artifact requires a new approval:

```bash
python3 <skill-dir>/scripts/route.py approve-release --root <root> --release <id> --author "<author>" --decision submit
```

### One-Prompt Install for Any Agent

Use this prompt when you want an agent to install the skill for you:

> Clone the `codex/research-route-slim` branch of `https://github.com/nestorfernando3/research-route.git` into a stable local folder, then link the full `research-route/` directory into the `research-route-slim` skill path for this harness. Do not copy only `SKILL.md`; the references, assets, and scripts must stay available. Leave any existing install untouched unless I explicitly ask you to replace it.

## Validation

The slim prompt was checked with three critical safety sentinels covering inaccessible sources, private-profile transfer, and venue mismatch.

At the time of writing:

- prompt size: `800 words` or fewer
- sentinel median: `17 / 20`
- critical failures: `0`
- selected six-scenario benchmark evidence is recorded in `evaluations/RESULTS.md`; it is not a superiority claim

The CLI is tested on macOS and Linux using `fcntl` and descriptor-relative POSIX operations. Windows support is not claimed.

## Limits

Research Route Slim does not guarantee acceptance, publication, or novelty.

It does not fabricate inaccessible sources, quotes, pages, or findings.

It does not invite private profile material into portable state or expose it in diagnostics. Separately approved publishable wording must still be authored and approved by the researcher.

It does not bypass journal policies or replace the author’s intellectual responsibility.
