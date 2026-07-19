---
name: research-route
description: Use when starting, continuing, restructuring, or preparing an academic paper or publication project, especially when the work spans literature, sources, argument, methodology, venue fit, bilingual prose, or transfer between agents and harnesses.
---

# Research Route

Build a portable paper project whose evidence, decisions, questions, and next action survive session, agent, or harness changes.

## Contract

- Keep critical state in project files. `ROUTE.md` is canonical state; `HANDOFF.md` is a session snapshot and never overrides it.
- Work toward one primary objective. Decisions remain reopenable when evidence, review, ethics, scope, method, thesis, or venue fit changes.
- Persist concise, auditable rationales and links, not hidden reasoning or duplicated prose. Protect researcher agency, privacy, source integrity, rights, and current obligations.
- Report the intellectual result first; unless full state is requested, report only material uncertainty, needed approval or block, and exact next action.

## Start/resume

Set `<skill-dir>` to this directory and `<root>` to the research-project directory. `<root>` must be outside `<skill-dir>`; never initialize there.

1. If `<root>/ROUTE.md` exists, read `ROUTE.md` and `HANDOFF.md` first. Resolve conflicts in favor of `ROUTE.md`, flag the discrepancy, and open only artifacts linked to objective.
2. Otherwise require an empty destination and initialize it:

   ```bash
   python3 <skill-dir>/scripts/route.py init <root> --title "<project title>" --language <language>
   ```

   Without an external root, propose state updates, mark persistence pending, and take the highest-value safe action.
3. Confirm objective and output type.
4. Before collecting, accessing, recording, transmitting, scraping, or analyzing participants, personal data, sensitive, Indigenous, community-governed, protected, copyrighted, or restricted material, run the early ethics gate in [research-and-claims.md](references/research-and-claims.md). Block work until consent or review, permissions/governance, storage/security, and AI-transmission conditions are recorded and satisfied.

## Work

- Advance discovery, argument, and composition through linked claims, evidence, decisions, and prose; let evidence reopen material decisions.
- Consider only open, unblocked work with closed dependencies. Choose the highest decision value per cost. Use `light` rigor for reversible exploration and `deep` rigor for thesis, decisive evidence, method, interpretation, quotations, novelty, and publication-bound text.
- Claim before working and never overwrite another claim:

  ```bash
  python3 <skill-dir>/scripts/route.py claim <item-id> --root <root> --owner <owner>
  ```

- Persist each result in its canonical artifact: sources in `sources/`, claims in `CLAIMS.md`, decisions in `DECISIONS.md`, contradictions and fog in `INQUIRY.md`, and blocks, budget, frontier, links, and summaries in `ROUTE.md`. Do not invent parallel state files or literal path placeholders. Close completed work metadata and release the claim:

  ```bash
  python3 <skill-dir>/scripts/route.py release <item-id> --root <root> --owner <owner>
  ```

## Quality gates

- **Integrity and calibration:** distinguish access level, observation, source interpretation, inference, support, dispute, and non-verification. Never fabricate or silently complete citations, DOI, pages, quotations, findings, data, or unseen text. If access is blocked, record consequences and obtain the source, narrow the claim, use an attributed abstract-level statement, or replace it.
- **Responsiveness and contribution:** test nearest neighbors, the strongest rival, simpler explanations, and adverse evidence before contribution or thesis approval. Let results change the claim, method, scope, or thesis.
- **Venue and approvals:** treat venue as provisional. A complete fingerprint requires at least ten representative full texts; fewer is provisional. Obtain explicit researcher approval for the initial profile, target venue, first defensible contribution, consequential method/corpus/interpretation, stabilized thesis, any private-to-publishable reflexive positioning, and submission version.
- **Privacy and stopping:** private profile material never enters a hosted/external handoff or manuscript. Use only researcher-authored, authorized operational consequences or separately approved publishable content; exact manuscript wording requires separate approval. State what evidence would close, narrow, or block each search, comparison, or transformation. A time box ends activity, not uncertainty; stop when uncertainty is declared non-fatal, or ethics, access, or a checkpoint blocks responsible work.
- **Bilingual propagation:** preserve meaning, entailment, uncertainty, evidence strength, argumentative function, and authorial voice across Spanish and English. For each consequential terminology decision, return a terminology ledger and persist separate thesis, claim, evidence, and inference impacts; use `pending real ID` only beside a concrete consequence, and escalate conceptually hybrid cases to the researcher.

## References

Read the needed reference: [researcher-profile.md](references/researcher-profile.md) for profiles, approvals, and reflexive positioning; [venue-fingerprint.md](references/venue-fingerprint.md) for candidates, sampling, requirements, fit, and retargeting; [research-and-claims.md](references/research-and-claims.md) for searches, sources, access, claims, contribution, adversarial work, rigor, and stopping; [writing-and-review.md](references/writing-and-review.md) for bilingual voice, terminology, drafting, revision, review, ethics, and submission artifacts.

## Close

Update `HANDOFF.md`'s intellectual sections, excluding private profile material, and leave the exact next action plus why it has highest value. Then run:

```bash
python3 <skill-dir>/scripts/route.py validate --root <root>
python3 <skill-dir>/scripts/route.py handoff --root <root>
python3 <skill-dir>/scripts/route.py validate --root <root>
```

Before release, recheck current ethics, permissions, rights, privacy, authorship, disclosure, and applicable policies. Cold-test at major checkpoints or transfer that a fresh agent can distinguish settled decisions, reopenable questions, blocks, and executable frontier work from `ROUTE.md`, `HANDOFF.md`, and linked artifacts. Report release, validation, handoff, any material block or approval, and the exact next action; never include private material.
