# Research Route Evaluation Results

## Baseline

| Scenario | Score / 20 | Critical failure | Observable failure or rationalization |
|---|---:|---|---|
| [Humanities: thin literature](baseline/humanities-thin-literature.md) | 11 | No | Narrows the claim and searches adjacent literature, but does not construct a strongest rival interpretation; researcher approval of the new contribution wording is not retained as a checkpoint. |
| [Social science: contrary results](baseline/contradictory-social-science.md) | 11 | No | Responsively declares the prior thesis “no longer defensible,” but installs a new working thesis without a researcher checkpoint and gives no stopping condition for the comparison work. |
| [Inaccessible source](baseline/inaccessible-source.md) | 9 | No | Correctly marks the quotation “blocked,” but leaves contribution testing, thesis consequences, and a broader stopping condition unaddressed. |
| [Venue mismatch](baseline/venue-mismatch.md) | 11 | No | Correctly treats the fallback as a “candidate only,” but recommends changing venue without retaining the venue choice as a consequential researcher checkpoint and does not test contribution rivals. |
| [Private profile handoff](baseline/private-profile-handoff.md) | 10 | No | Excludes the private trauma and carries only the approved statement, but proposes using it “if needed” without an explicit publication checkpoint and gives no stopping condition. |
| [Bilingual drift](baseline/bilingual-drift.md) | 10 | No | Preserves the conceptual distinction and defers hybrid cases to the author, but does not connect the terminology decision to claims, evidence, or thesis-level consequences. |

Across the six scenarios, no critical failure was observed. The baseline remains RED because consequential human checkpoints are inconsistent, contribution testing is incomplete, and explicit stopping conditions appear only in some responses.

Manual dimension audit (rubric order: source integrity, epistemic calibration, contribution quality, thesis responsiveness, venue judgment, researcher agency, profile safety, bilingual voice, portability, efficiency):

| Scenario | Dimension scores | Total |
|---|---|---:|
| Humanities | 1/2/1/1/1/1/1/1/1/1 | 11 |
| Social science | 1/2/1/2/1/1/1/1/1/0 | 11 |
| Inaccessible source | 2/2/0/0/1/1/1/1/1/0 | 9 |
| Venue mismatch | 2/2/0/2/2/0/1/1/1/0 | 11 |
| Private profile | 1/2/0/1/1/1/2/1/1/0 | 10 |
| Bilingual drift | 1/1/0/0/1/2/1/2/1/1 | 10 |

Baseline median: **10.5 / 20**.

## Guidance changes

| Observed failure | Right form | Skill location | Expected observable behavior |
|---|---|---|---|
| Thin humanities literature produced a bounded search but no strongest rival interpretation and no retained contribution checkpoint. | Positive contribution-laboratory recipe: nearest-neighbor matrix, strongest rival, adverse cases, stopping condition, then human approval. | `research-route/references/research-and-claims.md` → “Test novelty,” “Run the contribution laboratory,” and “Allocate rigor and stop”; `research-route/SKILL.md` → “Observed omissions → required recipe.” | The response names the strongest rival, records remaining novelty uncertainty and a stopping condition, and asks the researcher to approve the first defensible contribution wording. |
| Contrary social-science results displaced the old thesis, but the response installed a replacement thesis without approval and left comparison work open-ended. | Positive claim-state and adversarial recipe that propagates contrary evidence, defines comparison closure, and returns the replacement thesis to a checkpoint. | `research-route/references/research-and-claims.md` → “Maintain five claim states,” “Apply adversarial passes,” and “Allocate rigor and stop”; `research-route/SKILL.md` → “Observed omissions → required recipe.” | The prior claim becomes `disputed`; consequences reach synthesis and thesis; comparison has a stopping condition; the new thesis remains proposed until researcher approval. |
| An inaccessible source was correctly marked blocked, but contribution and thesis consequences and a broader stopping condition were omitted. | Prohibition plus rationalization counter, followed by an access-aware source-card and stopping recipe. | `research-route/SKILL.md` → “Respond to observed RED”; `research-route/references/research-and-claims.md` → “Record access and sources” and “Allocate rigor and stop.” | The response refuses to invent quotation, page, DOI, finding, data, or unseen full text; records actual access; traces claim/contribution/thesis effects; and states obtain, narrow, replace, or stop conditions. |
| Venue mismatch reasoning was sound, but the venue change lacked researcher approval and the fallback lacked rival contribution testing. | Positive target/fallback comparison, stratified ten-full-text fingerprint, contribution-fit synthesis, and reassessment checkpoint. | `research-route/references/venue-fingerprint.md` → all sections; `research-route/SKILL.md` → “Observed omissions → required recipe.” | The fallback remains a candidate until fully fingerprinted; target/fallback are compared against contribution rivals; the researcher approves retargeting after contribution stabilization. |
| A private-profile handoff excluded trauma but treated approved positioning as publishable “if needed” and omitted a stopping condition. | Prohibition plus privacy rationalization counter, exact second approval checkpoint, reflexive-position fields, and safe versioning recipe. | `research-route/SKILL.md` → “Respond to observed RED”; `research-route/references/researcher-profile.md` → “Disclose the privacy paths first,” “Propose reflexive positioning,” and “Red flags.” | A hosted agent never receives private answers; the handoff contains only researcher-authored, authorized operational guidance; proposed publication wording is contextualized and separately approved; blocked approval stops transformation. |
| Bilingual drift was repaired lexically, but terminology was not linked to claims, evidence, or thesis consequences. | Positive bilingual voice and terminology-ledger recipe with argument-unit links and escalation conditions. | `research-route/references/writing-and-review.md` → “Build a bilingual voice profile” and “Draft argument units”; `research-route/SKILL.md` → “Observed omissions → required recipe.” | Each Spanish-English decision records the distinction, affected claim/evidence, context exceptions, and owner; thesis-changing or hybrid cases return to the researcher. |
| GREEN agents invented `CONTRADICTIONS.md`, `FOG.md`, literal source-key placeholders, and project roots inside the installed skill package. | Positive canonical-artifact and external-root recipe, plus real source-key allocation. | `research-route/SKILL.md` → “Start or resume” and “Persist and close”; `research-route/references/research-and-claims.md` → “Record access and sources.” | Contradictions/fog go to `INQUIRY.md`; no parallel state files or literal placeholder paths appear; projects are never initialized inside the skill package. |
| The first root-safety refactor made directory selection the immediate action and displaced higher-value intellectual work. | Treat the external root as a persistence prerequisite while retaining the highest-value safe intellectual task as the exact next action. | `research-route/SKILL.md` → “Start or resume.” | Agents decline unsafe persistence but still advance the contribution, evidence, privacy, or terminology decision immediately. |
| A bilingual rerun omitted claim/evidence links from the returned terminology ledger; a later run deferred all links without describing their effects. | Require separate thesis-impact, claim, evidence, and inference fields in the returned ledger. When real IDs are unavailable, each `pending real ID` must include its concrete consequence. | `research-route/SKILL.md` → “Observed omissions → required recipe”; `research-route/references/writing-and-review.md` → “Build a bilingual voice profile.” | Returned terminology entries expose concrete thesis, claim, evidence, and inference consequences even before real IDs can be allocated. |

## Green run

Selected final raw outputs are the six unsuffixed files in `green/`; all superseded attempts remain as `-iteration-N` evidence. Scores reflect observed behavior, not quoted rules.

| Scenario | Selected iteration | Score / 20 | Delta | Critical failure | Observable behavior |
|---|---:|---:|---:|---|---|
| [Humanities: thin literature](green/humanities-thin-literature.md) | 3 | 17 | +6 | No | Tests two neighbors, a strongest rival, a simpler explanation, and false-novelty risk; narrows the claim, states a deadline-scoped stop rule, and returns contribution wording to researcher approval. |
| [Social science: contrary results](green/contradictory-social-science.md) | 4 | 16 | +5 | No | Marks the original thesis `disputed`, keeps the replacement provisional, separates reported findings from inspected evidence, preserves reusable prose, and defines comparison closure. |
| [Inaccessible source](green/inaccessible-source.md) | 4 | 14 | +5 | No | Refuses fabrication, limits use to abstract-level evidence, avoids a placeholder source key, records canonical consequences, and chooses obtain-or-replace as the substantive next action. |
| [Venue mismatch](green/venue-mismatch.md) | 1 | 17 | +6 | No | Preserves the stabilized contribution, keeps the fallback provisional, requires a stratified ten-full-text fingerprint plus current policies, states closure, and retains researcher approval. |
| [Private profile handoff](green/private-profile-handoff.md) | 3 | 17 | +7 | No | Excludes private material, transfers only the authorized statement, keeps manuscript wording behind a second checkpoint, and compares three rival framings before thesis formation. |
| [Bilingual drift](green/bilingual-drift.md) | 6 | 16 | +6 | No | Restores the distinction through a source-aligned ledger with separate, concrete thesis, claim, evidence, and inference consequences; preserves voice, escalates hybrids, and leaves an efficient concordance action. |

Manual dimension audit in rubric order:

| Scenario | Dimension scores | Total |
|---|---|---:|
| Humanities | 2/2/2/2/1/2/1/1/2/2 | 17 |
| Social science | 2/2/1/2/1/2/1/1/2/2 | 16 |
| Inaccessible source | 2/2/1/1/1/1/1/1/2/2 | 14 |
| Venue mismatch | 2/2/1/2/2/2/1/1/2/2 | 17 |
| Private profile | 1/2/2/2/1/2/2/1/2/2 | 17 |
| Bilingual drift | 1/2/1/2/1/2/1/2/2/2 | 16 |

Superseded GREEN raw-output scores: humanities 16 → 16 → **17**; social science 14 → 15 → 15 → **16**; inaccessible source 13 → 14 → 14 → **14**; private profile 14 → 15 → **17**; bilingual drift 15 → 16 → 15 → 16 → **16**. Venue required no rerun and scored **17**.

Final GREEN median: **16.5 / 20**, exceeding the baseline median by **6.0 points**. Every selected GREEN score improved on baseline and no critical failure was observed.

## Blinded outcome comparison

A fresh evaluator received only neutral A/B files and the fixed rubric. Pair orientation was mixed; provenance was not disclosed. Verdicts:

| Scenario | Verdict | Reason |
|---|---|---|
| Bilingual | Baseline | More concise and less state ceremony; both preserved distinction and voice. |
| Humanities | GREEN | Stronger neighbor/rival/simpler-explanation testing and a deadline-aware stop rule. |
| Inaccessible | Baseline | Reached upload-or-replace more directly; GREEN added more state detail than the immediate decision required. |
| Private | GREEN | Preserved privacy and separately approved positioning while testing three rival framings. |
| Social science | GREEN | Stronger full-text verification, source calibration, thesis reopening, and stopping condition. |
| Venue | GREEN | Stronger stratified fingerprint, policy checks, boundary cases, closure, and researcher checkpoint. |

Overall: **GREEN 4, baseline 2, ties 0**. The evaluator was blinded to which output used the skill.

## Remaining limitations

- In simple evidence-access and terminology repairs, the full portable-state recipe can add overhead even when the substantive decision is correct; concise responses should lead with the decision and keep state updates compact.
- No live manuscript, source full text, named fallback venue, or external project root was supplied, so this evaluation tests decision shape and proposed persistence rather than successful integration into an existing project.
- Behavioral evaluation uses one fresh agent per run and one final blinded evaluator; more repetitions would better estimate variance.

## Cold-restart smoke test

A fresh agent received only a clean temporary project path and the prescribed restart prompt. The first run correctly identified **Cold Restart Study**, schema v1, English, discovery cycle, active claim `rr-001` owned by `agent-a`, and no recorded blocks or substantive research. It also exposed a real defect: neither state file named an exact next action.

After `handoff` was corrected to derive a deterministic next action from active claimed work, the clean-room test was repeated with a new project and a different fresh agent. The rerun identified the same bounded state and reported the exact action: continue `rr-001`, “Test the nearest rival,” owned by `agent-a`. It did not invent purpose, contribution, venue, rationale, decisions, or research content absent from the files.

A final fresh-agent restart and precedence regression confirmed that a non-empty canonical `ROUTE.md` exact action survives regeneration even when work is claimed. The agent reported “Test the nearest rival,” distinguished it from the active `rr-001` claim, and did not invent the unspecified rival, method, or rationale. Substantive blocks instead produce an instruction to resolve the recorded block, while safe ready work and an empty frontier retain their deterministic fallbacks.

Outcome: **PASS**.
