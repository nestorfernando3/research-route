# Research Route Slim

<p align="center">
  <img src="assets/research-route-logo.png" alt="Research Route logo" width="720">
</p>

Research Route Slim is a compact academic-writing skill for turning a research question into a durable paper project that can survive agent switches, harness changes, and long revision cycles.

It is tuned primarily for humanities and social-science prose and argument, but it works anywhere the work depends on judgment, source discipline, and editorial fit.

## What It Is

Research Route Slim is not a one-shot prompt. It is a compact route for building a paper with structure, memory, and accountability:

- it helps you shape a researcher profile before drafting;
- it helps you choose and test a journal or venue before you overfit the paper;
- it keeps claims, evidence, decisions, and open questions in canonical Markdown state;
- it helps you write in a human voice without pretending to be human;
- it keeps the project portable so another agent or harness can continue it cleanly.

## Why It Exists

Most AI writing workflows are optimized for a single response. Research Route Slim preserves the full academic route while keeping the operating prompt compact: question, source work, contribution, thesis, prose, revision, and handoff.

The goal is not just speed. The goal is a paper that can actually be defended: original enough to matter, careful enough to trust, and organized enough to survive collaboration.

## What It Helps You Do

- build a philosophical or psychological researcher profile with private, operational, and publishable boundaries;
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

## Installation

Clone the slim publication branch once into a stable local directory, then link the full `research-route/` folder into the skill path for each harness.

### Codex

```bash
mkdir -p ~/.local/share
git clone --branch codex/research-route-slim https://github.com/nestorfernando3/research-route.git ~/.local/share/research-route-slim
mkdir -p ~/.codex/skills
test ! -e ~/.codex/skills/research-route-slim && ln -s ~/.local/share/research-route-slim/research-route ~/.codex/skills/research-route-slim
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
test ! -e ~/.claude/skills/research-route-slim && ln -s ~/.local/share/research-route-slim/research-route ~/.claude/skills/research-route-slim
```

### OpenCode

```bash
mkdir -p ~/.config/opencode/skills
test ! -e ~/.config/opencode/skills/research-route-slim && ln -s ~/.local/share/research-route-slim/research-route ~/.config/opencode/skills/research-route-slim
```

If you already installed the skill for Claude Code, OpenCode can also discover Claude-compatible skill locations in many setups, so you may not need a second copy.

### One-Prompt Install for Any Agent

Use this prompt when you want an agent to install the skill for you:

> Clone the `codex/research-route-slim` branch of `https://github.com/nestorfernando3/research-route.git` into a stable local folder, then link the full `research-route/` directory into the `research-route-slim` skill path for this harness. Do not copy only `SKILL.md`; the references, assets, and scripts must stay available. Leave any existing install untouched unless I explicitly ask you to replace it.

## Validation

The slim prompt was checked with three critical safety sentinels covering inaccessible sources, private-profile transfer, and venue mismatch.

At the time of writing:

- prompt size: `800 words`
- sentinel median: `17 / 20`
- critical failures: `0`
- the full six-scenario benchmark remains outside this slim publication's claim

## Limits

Research Route Slim does not guarantee acceptance, publication, or novelty.

It does not fabricate inaccessible sources, quotes, pages, or findings.

It does not expose private profile material unless the researcher explicitly authorizes publishable wording.

It does not bypass journal policies or replace the author’s intellectual responsibility.
