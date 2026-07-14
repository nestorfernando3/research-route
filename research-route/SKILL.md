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
5. Before collecting, accessing, recording, transmitting, scraping, or analyzing participants, personal data, sensitive archives or corpora, Indigenous or community-governed material, protected or copyrighted material, or restricted sources, run the early ethics gate in [research-and-claims.md](references/research-and-claims.md). Block the work until applicable consent or ethics review, permissions and community/archive terms, storage and security, and AI-tool transmission conditions are recorded and satisfied.

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
- any proposed conversion of private profile material into publishable reflexive positioning: the researcher must first relabel it locally and supply only the newly `publishable` content, then approve the exact manuscript wording; while labeled `private`, a hosted or external agent never reads it;
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

## Respond to observed RED

Use prohibition plus a concrete counter only for genuine discipline risks:

- **“The abstract makes the missing quotation reconstructable.”** No. Never fabricate or silently complete references, DOI, pages, quotations, findings, data, source content, or unseen full text. Record the access block, use only what the inspected access level supports, and obtain the source or replace it.
- **“The next agent needs the private story.”** No. A hosted or external agent never receives `private` answers. The researcher self-records them locally and supplies only a researcher-authored, authorized operational consequence. A truly local/offline harness may process private material only with explicit authorization and must exclude it from handoff and manuscript.

### Observed omissions → required recipe

- **Consequential checkpoint omitted:** keep the replacement thesis, target venue, contribution, method/corpus/interpretive strategy, reflexive positioning, or submission version proposed until the corresponding researcher approval is recorded.
- **Contribution opposition omitted:** test nearest neighbors, the strongest rival interpretation, simpler explanations, and adverse evidence before asking for contribution approval.
- **Stopping condition omitted:** state what evidence would close, narrow, or block comparison, search, or transformation work; a time box ends activity, not uncertainty.
- **Bilingual propagation omitted:** link every consequential term decision to affected claims, evidence, inference, and thesis consequences; escalate conceptually hybrid cases to the researcher.
