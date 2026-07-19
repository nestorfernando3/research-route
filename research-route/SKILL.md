---
name: research-route-slim
description: Use for sustained or multi-stage academic paper projects involving durable research state, venue or contribution work, bilingual argument revision, or transfer between agents and harnesses. Do not activate for isolated proofreading, citation formatting, one-off summaries, or narrow lookups unless the user names Research Route.
---

# Research Route Slim

Build a paper project whose evidence, decisions, questions, and next action survive session, agent, or harness changes.

## Contract

- Keep critical state in project files. `ROUTE.md` is canonical; `HANDOFF.md` is a session snapshot and never overrides it.
- Work toward one primary objective. Keep decisions reopenable when evidence, ethics, scope, method, thesis, or venue fit changes.
- Persist concise, auditable rationales and links, not hidden reasoning or duplicated prose. Protect researcher agency, privacy, source integrity, rights, and obligations.
- Report the intellectual result first, then material uncertainty, approval or block, and the exact next action.

## Start or resume

Set `<skill-dir>` to this directory and `<root>` to an external research-project directory. Never initialize inside the skill package.

1. If `<root>/ROUTE.md` exists, read `ROUTE.md` and `HANDOFF.md` first. Resolve conflicts in favor of `ROUTE.md`, flag the discrepancy, and open only artifacts linked to the objective.
2. Otherwise require an empty destination and initialize it:

   ```bash
   python3 <skill-dir>/scripts/route.py init <root> --title "<project title>" --language <language>
   ```

3. Confirm objective and output type. Researcher epistemic and authorial orientation is optional and proportional to methodological or authorial need; private material stays outside the portable root and external prompts.
4. Before handling participants, personal, sensitive, Indigenous, community-governed, protected, copyrighted, or restricted material, run the early ethics gate in `references/research-and-claims.md` and block until consent, governance, storage, and AI-transmission conditions are recorded.

## Work and lifecycle

Advance discovery, argument, and composition through linked claims, evidence, decisions, and prose. Choose open, unblocked work by decision value per cost. Use `light` rigor for reversible exploration and `deep` rigor for thesis, decisive evidence, method, interpretation, quotation, novelty, and publication-bound text.

Create, claim, work, and complete items in this order:

```bash
python3 <skill-dir>/scripts/route.py new --root <root> --title "<title>" --type <type> --mode <light|deep>
python3 <skill-dir>/scripts/route.py claim <item-id> --root <root> --owner <owner>
python3 <skill-dir>/scripts/route.py complete <item-id> --root <root> --owner <owner> --output <relative-path>
```

`complete` requires the active claim, the same owner, and an existing regular file inside `<root>`; it closes the item, records its normalized output path, atomically persists metadata, and releases the claim. Use `release` to relinquish unfinished work. Never overwrite another claim.

Persist sources in `sources/`, claims in `CLAIMS.md`, decisions in `DECISIONS.md`, contradictions and fog in `INQUIRY.md`, and blocks, frontier, links, and summaries in `ROUTE.md`. Do not invent parallel state files or literal path placeholders.

## Quality gates

Distinguish access, observation, interpretation, inference, support, dispute, and non-verification. Never fabricate citations, pages, quotations, findings, data, or unseen text. Test nearest neighbors, the strongest rival, simpler explanations, and adverse evidence before contribution or thesis approval. A venue fingerprint is provisional until at least ten representative full texts are read. Obtain researcher approval for consequential profile, venue, contribution, method, thesis, reflexive-position, and submission decisions. Preserve meaning, entailment, uncertainty, evidence strength, argumentative function, and voice across Spanish and English.

## Close and transfer

Update `HANDOFF.md`'s intellectual sections without private profile material, and leave the exact next action plus why it has highest value. Then run structural validation and handoff generation:

```bash
python3 <skill-dir>/scripts/route.py validate --root <root>
python3 <skill-dir>/scripts/route.py handoff --root <root>
python3 <skill-dir>/scripts/route.py validate --root <root> --checkpoint handoff
```

The default `validate` checks structural integrity only. The `handoff` checkpoint additionally requires a non-empty `ROUTE.md` `Destination`, a canonical exact next action, and declared content in every intellectual handoff section (`- None` is valid where no change applies, but not for the exact next action). It does not establish originality, evidence quality, ethics approval, venue fit, or submission readiness; those remain human or reference-driven gates.

Before release, recheck current ethics, permissions, rights, privacy, authorship, disclosure, and applicable policies. Cold-test major transfers so a fresh agent can distinguish settled decisions, reopenable questions, blocks, and executable frontier work from `ROUTE.md`, `HANDOFF.md`, and linked artifacts.

## References

Read only what the task needs: `researcher-profile.md`, `venue-fingerprint.md`, `research-and-claims.md`, and `writing-and-review.md`.
