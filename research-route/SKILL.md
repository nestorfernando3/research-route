---
name: research-route
description: Use when starting, continuing, restructuring, or preparing an academic paper or publication project, especially when the work spans literature, sources, argument, methodology, venue fit, bilingual prose, or transfer between agents and harnesses.
---

# Research Route

Build a rigorous, portable academic-paper project whose evidence, decisions, open questions, and next action survive changes of session, agent, or harness.

## Core contract

- Keep critical state in project files, not only in chat or memory. Treat `ROUTE.md` as canonical low-resolution state and `HANDOFF.md` as a session snapshot that never overrides it.
- Advance discovery and manuscript composition together through linked claims, evidence, decisions, and prose. Let evidence reopen the venue, thesis, method, corpus, interpretation, or scope.
- Store concise, auditable rationales, not hidden reasoning. Put each substantive result in its canonical artifact and update links or summaries; never duplicate the full prose across files.
- Protect researcher agency, privacy, source integrity, rights, and applicable institutional or venue obligations. Verify current policies when they matter; do not encode mutable policy details as timeless facts.

## Start or resume

Set `<skill-dir>` to this skill's directory and `<root>` to the research-project directory.

1. Detect whether `<root>/ROUTE.md` exists.
2. If it exists, resume: read `<root>/ROUTE.md` and `<root>/HANDOFF.md` first. Resolve conflicts in favor of `ROUTE.md`, flag the discrepancy, and open only artifacts linked to the current objective.
3. If it does not exist, require an empty destination and initialize it:

   ```bash
   python3 <skill-dir>/scripts/route.py init <root> --title "<project title>" --language <language>
   ```

4. Confirm one primary intellectual objective for the session and whether its output is exploratory or publication-bound.

## Cover the route

Move recursively through three cycles:

- **Discover:** situate the researcher; investigate questions, literature, materials, rivals, methods, and provisional venue.
- **Argue:** form claims; connect evidence; expose inference; test alternatives; calibrate contribution.
- **Compose:** design and revise architecture, bilingual voice, argument movement, and editorial fit.

Cover nine stations without forcing a sequence: researcher orientation; provisional venue selection; venue fingerprint construction; contribution formulation; debate and literature mapping; methodological or interpretive design; argument development; writing and rewriting; audit and submission preparation. Reopen earlier cycles when evidence or review changes a material decision.

## Preserve human authority

Obtain explicit researcher approval at every mandatory checkpoint:

- initial epistemic profile;
- provisional target venue;
- first defensible contribution statement;
- consequential method, corpus, or interpretive strategy;
- stabilized central thesis;
- any proposed conversion of private profile material into publishable reflexive positioning: first require explicit, versioned relabeling to `publishable`, then approve the exact manuscript wording; while labeled `private`, it remains excluded;
- version proposed for submission.

Between checkpoints, proceed autonomously only with reversible work inside the approved scope. Record the decision, concise rationale, residual uncertainty, and reopening condition in the canonical project state.

## Choose and claim frontier work

1. Consider only work items that are `open`, have all dependencies closed, and are neither blocked nor claimed.
2. Prefer the item with the greatest expected decision value: important uncertainty reduction relative to estimated cost. Use this as a judgment heuristic, not a fake precision score.
3. Select **light** rigor for exploration, alternatives, provisional prose, and other reversible work. Select **deep** rigor for thesis, decisive evidence, method or interpretation, quotations, novelty, and publication-bound text; increase rigor when error consequences are high or reversal is costly.
4. Claim before working:

   ```bash
   python3 <skill-dir>/scripts/route.py claim <item-id> --root <root> --owner <owner>
   ```

5. Never overwrite another claim. A stale timestamp is suspicion, not takeover authority; inspect the handoff, recent changes, temporary files, and evidence of an active session before any explicit recovery.

Create traceable work only when needed:

```bash
python3 <skill-dir>/scripts/route.py new --root <root> --title "<title>" --type <question|source|synthesis|decision|writing|audit|human-checkpoint> --mode <light|deep> [--depends-on <item-id>]
```

## Persist and close

Save the result in its canonical artifact; update affected source cards, claims, decisions, contradictions, fog, blocks, budget, frontier, and `ROUTE.md` links or concise summaries. Close the work-item metadata when its closure condition is met, then release its claim:

```bash
python3 <skill-dir>/scripts/route.py release <item-id> --root <root> --owner <owner>
```

At every session close, update the intellectual sections of `HANDOFF.md`, then run:

```bash
python3 <skill-dir>/scripts/route.py validate --root <root>
python3 <skill-dir>/scripts/route.py handoff --root <root>
python3 <skill-dir>/scripts/route.py validate --root <root>
```

Leave the exact next action and why it has highest value. Exclude private profile material. At major checkpoints or intentional transfer, cold-test whether a fresh agent can distinguish settled decisions, reopenable questions, blocks, and executable frontier work from `ROUTE.md`, `HANDOFF.md`, and their links.

## Load the exact reference

- Read [researcher-profile.md](references/researcher-profile.md) for profile interviews, classification, approvals, version comparison, or reflexive positioning.
- Read [venue-fingerprint.md](references/venue-fingerprint.md) for candidates, sampling, venue requirements, fit, or retargeting.
- Read [research-and-claims.md](references/research-and-claims.md) for searches, source cards, access, claims, contribution testing, adversarial work, rigor, or stopping.
- Read [writing-and-review.md](references/writing-and-review.md) for bilingual voice, terminology, drafting, revision, review simulation, ethics audit, or submission artifacts.

## Counter observed RED rationalizations

- **“The abstract makes the missing quotation reconstructable.”** No. Never fabricate or silently complete references, DOI, pages, quotations, findings, data, source content, or unseen full text. Record the access block, use only what the inspected access level supports, and obtain the source or replace it.
- **“Approved private material may be published later if useful.”** No. `private`, `operational`, and `publishable` are separate permissions. While content is labeled `private`, exclude it categorically. Publication requires explicit, versioned relabeling to `publishable` and then a separate checkpoint on the exact contextualized wording; hand off only authorized operational guidance.
- **“The evidence clearly changes the thesis, so the agent can install the replacement.”** Propose and test the revision, then retain the thesis checkpoint. Research effort already spent is not evidence.
- **“A promising venue candidate can become the target now.”** Compare target and fallback using a complete fingerprint, then retain researcher approval for the consequential venue decision.
- **“Nearby literature is enough to state the contribution.”** Test nearest neighbors, the strongest rival interpretation, simpler explanations, adverse evidence, and a stopping condition before asking for contribution approval.
- **“A terminology choice is only stylistic.”** Link bilingual terminology to the claim, evidence, inference, and thesis consequences it governs; escalate conceptually hybrid cases to the researcher.
