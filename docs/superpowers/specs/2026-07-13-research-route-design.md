# Research Route — Design Specification

## Purpose

Create a portable Codex skill named `research-route` that guides a researcher through the complete academic cycle: positioning, venue selection, question formation, literature and source work, methodological or interpretive design, argument construction, writing, revision, and submission preparation.

The skill must help produce ambitious, original, publication-oriented papers while preserving intellectual honesty, a recognizably human authorial voice, and continuity across agents and harnesses. It is interdisciplinary, with its writing and argumentative guidance tuned primarily for the humanities and social sciences. Spanish and English are first-class working and publication languages.

“World-class” is not a publication guarantee. It is operationalized as controllable qualities: significance and precision of the question, defensible contribution, command of the debate, appropriate method, traceable reasoning, serious treatment of objections, distinctive voice, clarity, ethical integrity, and editorial fit.

## Design principles

1. **Portable state over chat memory.** No critical context may live only in a conversation or agent memory.
2. **Dual route.** Discovery and manuscript composition advance together and remain synchronized through claims and evidence.
3. **Research is iterative.** A venue, thesis, method, or interpretation may be reopened when evidence warrants it.
4. **Human authority at consequential checkpoints.** Agents act autonomously on reversible work but do not assume irreversible intellectual decisions.
5. **Traceability without hidden reasoning.** Store concise, auditable rationales rather than private chains of thought.
6. **Originality through inquiry.** Distinguish intellectual, argumentative, and expressive originality; never equate novelty with paraphrase.
7. **Risk-proportional rigor.** Spend verification effort where an error would materially affect the paper.
8. **Minimal administration.** Create independent work items only when they improve coordination, traceability, or reuse.
9. **Ethics and privacy by design.** Protect people, sensitive materials, author privacy, rights, and institutional obligations.
10. **Evidence-based stopping.** End research cycles when further work has low expected decision value, not when uncertainty has disappeared.

## Scope

### Included

- Theoretical, interpretive, qualitative, quantitative, computational, review, and mixed-method papers.
- Humanities and social-science prose, argument, reflexivity, and disciplinary variation.
- Spanish and English research and writing, including terminology and semantic consistency across languages.
- Researcher positioning, provisional journal targeting, source discovery and evaluation, contribution development, drafting, review, and submission materials.
- Local Markdown project state, structured bibliography, optional Git history, and safe collaboration between agents.

### Excluded

- Diagnosing the researcher’s personality or treating a profile as a fixed psychological truth.
- Guaranteeing novelty, acceptance, publication, or “AI-undetectable” writing.
- Inventing or completing unavailable sources, citations, pages, quotations, data, or findings.
- Evading institutional, journal, copyright, privacy, or research-ethics policies.
- Replacing the author’s intellectual responsibility or claiming authorship on the researcher’s behalf.

## Core operating model

Research Route uses three recurring cycles rather than a rigid pipeline:

1. **Discover:** situate the researcher, investigate questions, literature, materials, rivals, and methods.
2. **Argue:** form claims, connect evidence, expose inference, test alternatives, and calibrate novelty.
3. **Compose:** design and revise the manuscript’s architecture, voice, and editorial fit.

Each cycle may reopen the others. Auditing and submission preparation can send the project back to discovery or argument when they expose a material weakness.

Nine stations provide coverage without imposing order:

1. Researcher orientation.
2. Provisional venue selection.
3. Venue fingerprint construction.
4. Contribution formulation.
5. Debate and literature mapping.
6. Methodological or interpretive design.
7. Argument development.
8. Writing and rewriting.
9. Audit and submission preparation.

## Human checkpoints

Explicit researcher approval is required after:

- The initial epistemic profile.
- The provisional target-venue choice.
- The first defensible contribution statement.
- A consequential method, corpus, or interpretive-strategy choice.
- Stabilization of the central thesis.
- Any transformation of private profile material into publishable reflexive positioning.
- The version proposed for submission.

Between checkpoints, the agent may autonomously search, organize, compare, draft, validate, and propose alternatives when those actions are reversible and within the approved scope.

## Portable project model

Each research project is a self-contained local folder. Markdown is canonical for human-readable state. BibTeX or CSL JSON stores structured references. Git is useful but optional.

```text
<project>/
├── ROUTE.md
├── HANDOFF.md
├── RESEARCHER.md
├── VENUE.md
├── INQUIRY.md
├── CLAIMS.md
├── DECISIONS.md
├── work-items/
├── sources/
│   └── <source-key>.md
├── manuscript/
│   ├── OUTLINE.md
│   ├── VOICE.md
│   └── sections/
└── references/
    └── library.bib
```

### Canonical responsibilities

- `ROUTE.md`: destination, project schema version, current cycle, provisional contribution and venue, consolidated decisions, frontier, fog, blocks, budget, and exact recommended next action. It is the canonical low-resolution state.
- `HANDOFF.md`: a validated session snapshot for cold continuation. It never overrides `ROUTE.md`.
- `RESEARCHER.md`: versioned epistemic profile, voice, private/operational/publishable classification, and changes in the researcher’s position.
- `VENUE.md`: venue candidates, target and fallback, explicit requirements, sampling frame, editorial fingerprint, uncertainty, and reassessment checkpoints.
- `INQUIRY.md`: live questions, hypotheses, rival interpretations, contradictions, and not-yet-specifiable fog.
- `CLAIMS.md`: central and supporting claims with evidence, inference, objections, confidence, and manuscript destination.
- `DECISIONS.md`: concise decision record: decision, evidence, alternatives, rationale, residual uncertainty, and reopening condition.
- `sources/`: one source card per consulted source, including access level, provenance, summary, observations, interpretations, limitations, quotations with locations, and possible uses.
- `manuscript/`: argument architecture, voice specification, sections, and integrated drafts.
- `references/`: structured citation library.

Each piece of substantive information has one canonical home. Index files link and summarize; they do not duplicate full content.

## Researcher profile

The profile is an editable epistemic and authorial instrument, not a clinical assessment. A guided dialogue explores:

- Intellectual traditions and values.
- Lived or disciplinary experiences relevant to the inquiry.
- Preferred forms of explanation and evidence.
- Tolerance for ambiguity and conflict.
- Recurring intuitions, sensitivities, and conceptual attractions.
- Anticipated blind spots and confirmation risks.
- Productive unresolved tensions.
- Writing samples and voice preferences, when authorized.
- Questions or evidence capable of changing the researcher’s view.

Each field is classified as:

- **Private:** remains local and never appears in handoffs or manuscripts.
- **Operational:** may guide authorized agents but is not publishable.
- **Publishable:** may be transformed into reflexive positioning only after explicit approval.

The profile is versioned. A final comparison records how the research changed the researcher’s position. This change may inform reflexivity but is never automatically published.

## Venue selection and fingerprint

The target venue is a provisional hypothesis, not an irreversible destination. Select a target and at least one plausible alternative early; reassess the choice after the contribution stabilizes.

Build a venue fingerprint from:

- Current author instructions, ethics and AI policies, scope, article types, and formal limits.
- Editorials, calls, special issues, or policy texts when relevant.
- At least ten representative articles, expanding the sample until it is sufficiently informative.

The article sample should balance recency, influence, topic proximity, method, authorship patterns, ordinary and special issues, and articles that reveal the venue’s boundaries. Store metadata and original analytical notes, not complete copyrighted texts unless permitted. A venue fingerprint is not complete until at least ten articles have been read at full-text level. If access prevents this, record the block and ask the researcher to obtain access or approve another venue; do not silently lower the threshold.

Every venue conclusion is classified as:

- Explicit requirement.
- Strong observed pattern.
- Tentative inference.
- Unknown.
- Trait not to imitate.
- Opportunity for productive differentiation.

The goal is to understand a scholarly community’s expectations, not imitate its authors’ language or structure.

## Evidence and source integrity

Every substantive claim uses one of five states:

- **Supported:** verifiable, located evidence exists.
- **Inferred:** evidence exists, but the interpretive step is explicit.
- **Provisional:** useful for exploration but not ready as a conclusion.
- **Disputed:** material rival evidence or interpretation exists.
- **Unverified:** cannot enter the manuscript as fact.

Never fabricate or silently complete a reference, DOI, page, quotation, finding, or inaccessible source. Record the level of access: metadata, abstract, excerpt, full text, dataset, or primary material. Verify quotations against the original before publication.

Search in purposeful layers: seminal work, recent work, direct rivals, adverse evidence, adjacent disciplines, and citation trails. Each search round should be tied to a decision it could change. Maintain query and selection records when systematic or reproducible retrieval matters.

## Laboratory of contribution

Originality is developed through a deliberate cycle:

1. Generate multiple plausible answers or interpretive routes.
2. Search for prior equivalents and the closest neighboring contributions.
3. Construct the strongest rival interpretation and simpler explanations.
4. Test candidates against adverse evidence and difficult cases.
5. Identify the distinctive combination of problem, material, concept, method, or inference.
6. State what the contribution adds, to which conversation, within what limits.
7. Record rejected alternatives and the reasons for rejection.

The skill distinguishes:

- **Intellectual originality:** a defensible new question, connection, distinction, interpretation, or answer.
- **Argumentative originality:** a non-trivial inferential route rather than a rearrangement of existing summaries.
- **Expressive originality:** author-owned prose without patchwriting, source imitation, or artificial errors.

The skill never asserts that a contribution is wholly unprecedented. It reports the tested novelty scope and remaining uncertainty.

## Adversarial function

At consequential points, require an opposition pass that searches for:

- The strongest rival interpretation.
- Evidence that would weaken or reverse the thesis.
- Simpler explanations.
- Apparent novelty caused by a literature gap in the search.
- Uncomfortable implications of the chosen position.
- Boundary cases and populations or archives the account excludes.

Objections must be allowed to change the thesis, method, corpus, or venue. They are not relegated to a cosmetic limitations paragraph.

## Writing and bilingual voice

Maintain a versioned voice profile derived from authorized samples and explicit preferences: rhythm, conceptual density, sentence range, use of first person, terminology, rhetorical stance, and disallowed habits.

Do not simulate humanity with mistakes. Favor situated thought, functional syntactic variation, precise verbs, motivated transitions, calibrated uncertainty, and language shaped by the argument. Preserve semantic and terminological consistency when moving between Spanish and English; translation is an intellectual revision step, not a word substitution task.

Revise in separate passes:

1. Argument advancement.
2. Evidence and claim calibration.
3. Researcher positioning and reflexivity.
4. Voice and prose movement.
5. Editorial fit without imitation.
6. Verbal and structural independence from sources.
7. Ethical and epistemic honesty.

## Work items and frontier

Create a work item only when the task resolves a significant uncertainty, blocks later work, needs independent traceability, can be delegated, or produces a reusable decision or artifact. Small actions remain checklists inside a parent item.

Work-item types are question, source, synthesis, decision, writing, audit, and human checkpoint. Every item includes a stable identifier, editable human title, schema version, status, dependencies, owner, rigor mode, intended output, question or deliverable, and closure criteria.

Use stable identifiers for links and titles in all human-facing narration. The frontier is the set of open, unblocked, unclaimed work items. Fog contains in-scope concerns that cannot yet be formulated precisely enough to become work items.

A session has one primary intellectual objective. It may close several small items sharing the same context, but it must not silently mix independent decisions.

## Claiming and collaboration

Claim an item before work. Where supported, use an atomic local lock. A stale timestamp marks a suspicious claim; it never authorizes automatic takeover. Recovery requires checking the handoff, recent changes, temporary files, and evidence of an active session.

Closing a substantive result requires:

1. Save sources and outputs in their canonical locations.
2. Update affected claims and decisions.
3. Register new uncertainty and contradiction.
4. Close, release, or explicitly retain claimed items.
5. Update `ROUTE.md`.
6. Prepare and intellectually complete `HANDOFF.md`.
7. Run structural validation.

## Handoff and cold restart

The CLI may prefill mechanical facts in `HANDOFF.md`, but an agent must add:

- What changed intellectually.
- What assumptions no longer hold.
- The contradiction or uncertainty that matters now.
- Decisions awaiting the researcher.
- The exact next step and why it has the highest value.

Private profile fields are excluded by default. Every session runs a lightweight portability check for completeness, links, and an exact next action. At major checkpoints and before an intentional transfer between agents or harnesses, run a full cold-restart test: a fresh agent reads `ROUTE.md` and `HANDOFF.md`, opens only linked artifacts, identifies what can proceed, and distinguishes settled decisions from questions that may be reopened.

## Resource allocation and stopping

Record the project’s time, access, length, deadline, and ambition constraints. Use two rigor modes:

- **Light:** exploration, alternatives, provisional prose, and reversible work.
- **Deep:** thesis, decisive evidence, method, quotations, novelty claims, and publication-bound text.

Prioritize the next task using expected value: uncertainty reduction multiplied by importance to the paper, divided by estimated cost. This is a heuristic, not a fake precision score.

Stop a research cycle when:

- Another search has low probability of changing a material decision.
- Central and rival positions are represented.
- Main claims have support appropriate to their scope.
- Remaining uncertainty is declared and does not invalidate the contribution.
- Further reduction would cost more than its expected effect.
- The paper meets the agreed standard for its current phase.

## Ethics, privacy, and rights

Before using participants, personal data, sensitive archives, restricted corpora, or protected material, record applicable consent, institutional approval, risks, confidentiality, storage, licensing, quotation limits, conflicts, and journal or institutional AI policies.

Do not transmit private profile content or sensitive research material to external services without explicit authority. Do not let editorial fit override ethical or epistemic obligations.

## Review and submission

Before submission, run separate simulations of:

- A screening editor deciding whether to send the paper to review.
- A knowledgeable reviewer sympathetic to the project.
- A knowledgeable skeptical reviewer.

Each returns a reasoned recommendation and prioritized changes, not a decorative score. The final audit covers contribution, sources, claims, method, ethics, originality, voice, bilingual consistency, venue requirements, references, abstract, keywords, and cover letter.

## Skill package

```text
research-route/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── researcher-profile.md
│   ├── venue-fingerprint.md
│   ├── research-and-claims.md
│   └── writing-and-review.md
├── assets/
│   └── route-template/
└── scripts/
    └── route.py
```

`SKILL.md` contains only the core contract, cycles, checkpoints, next-action logic, and routing to references. The template contains the minimal portable project structure. A single CLI provides `init`, `new`, `claim`, `release`, `validate`, `handoff`, and `migrate` commands. Automation handles schemas and consistency only; it never chooses a thesis, interpretation, method, or publication claim.

Projects declare a schema version. Validation recognizes supported older versions and proposes non-destructive migration with backup and confirmation; it never rewrites a project silently.

## Failure behavior

- **Inaccessible source:** record access level and do not represent unseen content as read.
- **Contradictory evidence:** mark affected claims disputed and reopen the relevant decision.
- **Venue mismatch:** compare target and fallback, preserve the fingerprint, and request approval before retargeting.
- **Sensitive profile content:** keep it private; hand off only derived operational guidance.
- **Broken or stale claim:** block publication-bound text until the source or inference is repaired.
- **Concurrent claim:** do not overwrite; recover only after the explicit stale-claim audit.
- **Insufficient novelty evidence:** describe the contribution provisionally and prioritize a nearest-neighbor search.
- **Budget exhaustion:** surface unresolved risks, reduce scope with approval, and preserve a usable handoff.

## Validation strategy

### Structural validation

Validate skill frontmatter, naming, interface metadata, project schema, links, statuses, required fields, duplicate identifiers, claim-source references, and handoff freshness.

### CLI tests

In temporary directories, test route initialization, work-item creation, atomic claiming and release, seeded inconsistency detection, handoff scaffolding, supported migration, and non-destructive failure.

### Behavioral RED–GREEN–REFACTOR

Run equivalent scenarios without and with the skill:

- A humanities theory paper with an original intuition and thin bibliography.
- A social-science paper with contradictory findings.
- A target venue that ceases to fit after the contribution stabilizes.
- An inaccessible source that tempts citation fabrication.
- A mid-project agent or harness transfer.
- A profile containing private and potentially publishable material.
- A bilingual draft whose terminology drifts between languages.

Record baseline failures before authoring the skill, then write the minimal guidance that corrects observed failures. Re-run scenarios, close new loopholes, and retain raw evaluation artifacts outside the deployed skill.

### Outcome evaluation

Use blinded comparisons where practical. Evaluate whether the skill improves question precision, genuine disagreement discovery, thesis responsiveness to adverse evidence, authorial voice, handoff continuity, and uncertainty reduction per unit of effort. Compliance without improved academic judgment is not success.

## Acceptance criteria

The completed skill must:

- Initialize and validate a portable project without requiring Git or a specific harness.
- Preserve state and enable a successful cold restart.
- Keep private, operational, and publishable profile material distinct.
- Treat target venues provisionally and do not complete a venue fingerprint until at least ten representative articles have been read at full-text level.
- Prevent fabricated or overclaimed source use.
- Distinguish fact, inference, hypothesis, dispute, and lack of verification.
- Expose claims to meaningful opposition and allow revision.
- Support original Spanish and English prose with a researcher-owned voice.
- Allocate effort by risk and decision value.
- Stop research cycles using explicit sufficiency criteria.
- Preserve human approval at consequential checkpoints.
- Pass structural, CLI, behavioral, handoff, and outcome-oriented tests.
