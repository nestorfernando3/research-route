---
name: research-route-slim
description: Use for sustained or multi-stage academic paper projects involving durable research state, venue or contribution work, bilingual argument revision, publication-bound prose, or transfer between agents and harnesses. Use the adaptive route to move quickly through reversible work and batch non-critical review debt. Do not activate for isolated proofreading, citation formatting, one-off summaries, or narrow lookups unless the user names Research Route.
---

# Research Route Slim

Maintain a portable academic project while matching rigor to consequence, reversibility, and correction cost.

## Contract

- Keep canonical state in the external project root. `ROUTE.md` governs; `HANDOFF.md` transfers a snapshot and never overrides it.
- Keep four layers separate: research state, reproducible materials, academic manuscript, and editorial release package.
- Preserve researcher agency, privacy, source integrity, rights, authorship, and accountable AI disclosure.
- Report the intellectual result first, then uncertainty, block or approval, and the exact next action.

## Start or resume

Set `<skill-dir>` to this directory and `<root>` to an external project directory. Never initialize inside the skill package.

```bash
python3 <skill-dir>/scripts/route.py init <root> --title "<title>" --language <language> --schema-version 2
```

For a legacy root, run `migrate --dry-run` before `migrate --apply`. Read `ROUTE.md` and `HANDOFF.md`, then open only artifacts linked to the objective. Keep private material outside the portable root and external prompts.

Before handling participants, personal, sensitive, Indigenous, community-governed, protected, copyrighted, or restricted material, complete the early ethics gate in `references/research-and-claims.md`. Critical work cannot be deferred.

## Adaptive route

Classify work as `routine`, `material`, or `critical`.

- `routine`: exploration, organization, provisional outlines, low-consequence wording, and reversible searches. Record it with the short path:

  ```bash
  python3 <skill-dir>/scripts/route.py advance --root <root> --title "<title>" --type <type> --owner <owner> --output <path> --review-later
  ```

- `material`: synthesis, secondary claims, venue orientation, method framing, and substantial prose. Accumulate it for the argument review.
- `critical`: ethics, privacy, source access, quotations, decisive claims, method, results, rights, authorial decisions, and submission. Verify immediately and never pass it through `--review-later`.

Use `new`, `claim`, `complete`, and `release` for shared or long-running work. A provisional item remains resumable and does not satisfy dependencies until verified.

Record complete source cards only for cited, decisive, or adverse sources. Keep candidate sources to verified identity, access level, and selection or discard reason. Track substantive claims in `claims/C-NNN-<slug>.md` with one of `supported | inferred | provisional | disputed | unverified`.

## Two joint reviews

Run the grouped argument review before stabilizing thesis, method, or publication-bound sections:

```bash
python3 <skill-dir>/scripts/route.py review --root <root> --stage argument
```

Resolve claims, evidence, inferences, rivals, method, and material review debt together. Run the release review for prosa, continuity, ethics, rights, references, venue, AI disclosure, artifacts, and final author approval:

```bash
python3 <skill-dir>/scripts/route.py review --root <root> --stage release
```

Use `light` rigor for reversible work and `deep` rigor for critical work. Merge editor, sympathetic-reviewer, and skeptical-reviewer perspectives into the grouped reviews; run independent adversarial passes only when a critical threat appears.

## Venue and validation

Use three full texts plus current official requirements for provisional venue orientation. Require ten representative full texts, stratified evidence, classification of conclusions, and researcher approval only before submission.

Run focused checkpoints:

```bash
python3 <skill-dir>/scripts/route.py validate --root <root> --checkpoint argument
python3 <skill-dir>/scripts/route.py validate --root <root> --checkpoint prose --release <id>
python3 <skill-dir>/scripts/route.py validate --root <root> --checkpoint venue
python3 <skill-dir>/scripts/route.py validate --root <root> --checkpoint submission --release <id>
```

`prose` checks Markdown, text, LaTeX, and DOCX for internal routes, hashes, IDs, scripts, version labels, draft language, ledger fragments, telegraphic sentences, and promotional or combative register. It skips code, tables, formulas, bibliography, headings, and metadata. Scripts detect and verify; they do not rewrite prose. Correct findings or record an author-approved exception tied to the artifact hash.

The clean-room review receives only the manuscript, venue guide, verified claims, and authorized voice profile. A release must show complete academic sentences, explicit connectors, continuous reasoning, and no unjustified production scaffolding. AI disclosure states functions, verification, and responsibility without narrating prompts, skills, scripts, or Codex internals.

## Close and transfer

Before release, recheck current ethics, permissions, rights, privacy, authorship, disclosure, and policy requirements. Then generate and validate the handoff:

```bash
python3 <skill-dir>/scripts/route.py handoff --root <root>
python3 <skill-dir>/scripts/route.py validate --root <root> --checkpoint handoff
```

Structural validation reports structural integrity only. `submission` composes structural, handoff, research, prose, venue, ethics, bibliography, review, and exact-version approval; it blocks every unresolved critical or material debt.

Read only the references needed for the active decision: `researcher-profile.md`, `venue-fingerprint.md`, `research-and-claims.md`, and `writing-and-review.md`.
