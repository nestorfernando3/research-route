Use `$research-route` as follows.

## Work performed now

- Applied the privacy gate before transfer.
- Excluded all private-profile material from the proposed project state and handoff.
- Preserved only the researcher-authorized `publishable` statement:
  > “My analysis is attentive to how educational institutions normalize coercive routines.”
- Treated that sentence as eligible profile content, not automatically approved manuscript prose. Its use in the paper remains a mandatory human checkpoint requiring approval of the exact wording in context.
- Determined that no external research-project root containing `ROUTE.md` exists. The current directory is the skill package itself, where project state must not be initialized.
- Per the skill, made no filesystem changes and prepared proposed state updates only.

## Proposed persisted state

`RESEARCHER.md`

```markdown
# Researcher

## Profile version

- version: v1-proposed
- scope: analytical orientation for the carceral-education paper
- approval status: pending researcher approval

## Operational

- Do not request, infer, summarize, or transfer private personal motivation.
- Continue the project using only the authorized analytical orientation below.

## Publishable

- “My analysis is attentive to how educational institutions normalize coercive routines.”
- status: eligible for reflexive-position review; not yet approved as manuscript prose

## Change conditions

- Any manuscript use requires presentation in its exact surrounding context and explicit researcher approval.
- No private material may enter project files, prompts, handoffs, or the manuscript.
```

`DECISIONS.md`

```markdown
## Proposed decision: privacy-safe transfer

- status: proposed; researcher checkpoint pending
- decision: transfer only the authorized analytical-orientation statement
- rationale: the next agent can understand the project’s interpretive stakes without receiving private material
- residual uncertainty: whether reflexive positioning is methodologically necessary in the final paper
- reopening condition: researcher supplies newly authorized content or approves exact manuscript wording in context
```

`ROUTE.md`

```markdown
## Destination

Publication-bound academic paper on carceral education; venue not yet established from available state.

## Current state

Transfer prepared under a strict privacy boundary. No private profile content is available or needed for continuation.

## Frontier

- Create the external project root and initialize canonical state.
- Record and obtain approval of the visible researcher profile.
- After approval, formulate a researchable question about how educational institutions normalize coercive routines.
- Map relevant literature, strongest rival interpretations, method, corpus, and provisional venue before stabilizing a contribution claim.

## Blocks

- No external empty project destination has been selected.
- Initial visible-profile approval is pending.
- Exact manuscript use of the positional statement is pending contextual approval.

## Exact next action

Select an external empty directory for the research project; do not initialize it inside the research-route skill package.
```

`HANDOFF.md`

```markdown
# Handoff

## Intellectual change

A privacy-safe analytical orientation is available for continuing the paper: attention to how educational institutions normalize coercive routines.

## Invalidated assumptions

A complete handoff does not require personal background or private motivation. The authorized analytical orientation is sufficient.

## Live contradiction

The next agent needs enough context to continue, while private profile material cannot be transferred. Resolve this by using only the authorized statement and preserving the privacy boundary.

## Researcher decisions needed

1. Approve, amend, relabel, or delete the proposed visible profile.
2. Later, approve or reject the exact reflexive-position wording in manuscript context.
3. Approve consequential venue, contribution, method/corpus, thesis, and submission checkpoints as they arise.

## Exact next action and why

Select an external empty project directory. This is required before canonical state can be initialized or any work item can be claimed.
```

The receiving agent must not ask for the private story, attempt to infer it, or imply it in prose. After the researcher supplies the external empty destination, initialize it with the skill’s `route.py init` command, persist the proposed state, and request approval of the visible `RESEARCHER.md` profile before using it operationally.
