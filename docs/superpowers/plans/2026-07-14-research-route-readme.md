# Research Route README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public-facing `README.md` that explains what Research Route does, why it matters, and how to install it in Codex, Claude Code, and OpenCode.

**Architecture:** One new Markdown file at the repository root. The README will reuse the already-validated skill contract and evaluation results, then present the installation paths as copy-paste shell snippets that point each harness at the same full `research-route/` directory from a stable local clone.

**Tech Stack:** Markdown, Git, shell snippets.

## Global Constraints

- `research-route` is interdisciplinary and tuned primarily for humanities and social-science prose and argument.
- Spanish and English are first-class research and publication languages.
- `ROUTE.md` is canonical project state; `HANDOFF.md` is only a session snapshot.
- Do not promise novelty, publication, or AI-detector evasion.
- Protect private profile material and source integrity.
- A venue fingerprint is incomplete until at least ten representative articles have been read at full-text level.
- The README must be written in English only.

---

### Task 1: Draft the public README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: `research-route/SKILL.md` for the actual operating contract, `evaluations/RESULTS.md` for honest validation claims, and the current harness-install conventions already verified in this workspace.
- Produces: one root-level `README.md` that sells the skill without exaggeration and gives clear install instructions for Codex, Claude Code, and OpenCode.

- [ ] **Step 1: Write the README with these sections**

Use this exact structure:

```markdown
# Research Route

## What It Is

## Why It Exists

## What It Helps You Do

## Key Features

## Installation

### Codex

### Claude Code

### OpenCode

### One-Prompt Install for Any Agent

## Validation

## Limits
```

Include honest feature copy for:

- human-like academic prose without pretending to be human,
- a researcher profile with private, operational, and publishable boundaries,
- venue fingerprinting from at least 10 full-text articles,
- portable project state that survives agent or harness switches,
- contribution testing against nearest neighbors, rivals, and adverse evidence,
- stepwise guidance that keeps work efficient and auditable.

Use this install pattern in the README so every harness points at the same full skill directory:

```bash
git clone https://github.com/nestorfernando3/research-route.git ~/.local/share/research-route
mkdir -p ~/.codex/skills ~/.claude/skills ~/.config/opencode/skills
ln -s ~/.local/share/research-route/research-route ~/.codex/skills/research-route
ln -s ~/.local/share/research-route/research-route ~/.claude/skills/research-route
ln -s ~/.local/share/research-route/research-route ~/.config/opencode/skills/research-route
```

Add a short note that OpenCode can also discover Claude-compatible skill locations when they are already installed.

Add a short validation note that cites the existing evaluation result in plain language, including:

- baseline median `10.5 / 20`,
- final GREEN median `16.5 / 20`,
- blinded comparison `GREEN 4, baseline 2, ties 0`,
- no critical failures observed in the selected GREEN runs.

- [ ] **Step 2: Keep the copy honest**

Run a quick scan over the draft to ensure it does not claim:

- guaranteed publication,
- guaranteed novelty,
- AI-detector evasion,
- automatic access to restricted material,
- or that a venue fingerprint is complete before 10 full-text papers.

If any of those phrases appear, rewrite them immediately into a limitation or a capability boundary.

- [ ] **Step 3: Check formatting and wording**

Run:

```bash
rg -n "guaranteed publication|guaranteed novelty|AI-detector evasion|undetectable writing|automatic access to restricted material" README.md
git diff --check
```

Expected:

- `rg` returns no matches for the banned hype list.
- `git diff --check` returns clean output.

- [ ] **Step 4: Commit the README**

```bash
git add README.md
git commit -m "docs: add research route README"
```

Expected: one commit with the new public README and no unrelated file changes.
