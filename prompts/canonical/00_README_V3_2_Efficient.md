# AI Narrative Builder V3.2 Efficient

## What this is
A full replacement of V3.2 tuned to reduce Claude token usage without weakening the workflow.

It keeps the same core strengths:
- near-final editorial recommendation
- human approval before rebuild
- XML/output discipline
- contributor-safe logic
- editability-first audio behaviour
- smooth, non-choppy cutting
- general-purpose applicability across interviews, tutorials, explainers, walkthroughs, course content, case studies, promos, and mixed edits

## What changed
This edition adds a token-efficiency layer on top of the same editorial system.

Key changes:
- compact-by-default responses
- structured outputs before prose
- decision ledger to avoid rethinking settled choices
- delta-only revisions after the first full plan
- quote stubs first, exact quotes only when shortlisted
- compact approval gates
- local revision discipline around locked beats
- optional split-chat workflow for rebuild-heavy jobs

## What stays unchanged
The workflow still requires:
- kickoff and intent capture
- source audit
- contributor resolution
- material classification
- content-function grouping
- cleanup strategy
- mode selection
- paper edit approval
- rebuild only after approval
- validation before handoff

## File structure
- 01_Project_Instructions_V3_2_Efficient.md
- 02_Kickoff_Intent_and_Presets_V3_2_Efficient.md
- 03_Structuring_and_Approval_V3_2_Efficient.md
- 04_XML_Builder_Spec_and_Audio_Behaviour_V3_2_Efficient.md
- 05_Verification_and_Usage_V3_2_Efficient.md

## Claude project setup
### Instructions tab
Paste the full contents of:
- 01_Project_Instructions_V3_2_Efficient.md

### Files tab
Upload at minimum:
- 02_Kickoff_Intent_and_Presets_V3_2_Efficient.md
- 03_Structuring_and_Approval_V3_2_Efficient.md
- 04_XML_Builder_Spec_and_Audio_Behaviour_V3_2_Efficient.md
- 05_Verification_and_Usage_V3_2_Efficient.md

Optional but recommended:
- 00_README_V3_2_Efficient.md
- 01_Project_Instructions_V3_2_Efficient.md

## Best operating pattern for lower usage
For routine jobs, stay in one chat.

For large or multi-source jobs, this is usually more efficient:
1. Chat A: planning only
   - intake
   - audit
   - roster
   - grouping
   - structure
   - paper edit
   - approval
2. Chat B in the same project: rebuild only
   - paste approved paper edit
   - paste approved audio/rebuild assumptions
   - attach source XML(s)
   - request rebuild and validation

This keeps the rebuild chat narrow and reduces context bloat.

## First-run trigger
Start with:

Let’s begin.

Then attach or confirm:
- synced source XML(s)
- transcript(s)
- optional notes

If useful, also provide:
- target runtime
- hard cap
- tone
- cut style
- representation strategy
- must-keep / minimise contributors
- audio baseline
- multicam preference

## Design principle
The pipeline remains:
- domain-agnostic at the core
- project-specific by configuration
- editorially specific through contributor roles, content functions, paper edit approval, and rebuild rules

Efficiency should reduce waste, not reduce judgement.