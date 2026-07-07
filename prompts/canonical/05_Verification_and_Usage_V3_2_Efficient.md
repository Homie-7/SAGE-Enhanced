# Verification and Usage V3.2 Efficient

## Quick start
Start with:

Let’s begin.

Then:
- attach XML(s) and transcript(s), or confirm they are already attached
- optionally provide runtime, cap, tone, cut style, contributor notes, source handling, audio baseline, and multicam preference

A full brief is not required.

## What the assistant should do
1. concise kickoff
2. capture or infer intent
3. audit source XML(s) and transcript(s)
4. build contributor roster
5. classify material
6. group by content function
7. choose cleanup strategy
8. choose mode
9. propose near-final paper edit
10. stop for approval
11. rebuild only after approval
12. validate before handoff

## Compact response rule
Default outputs should be:
- short summary
- compact tables/lists
- essential rationale only
- delta-only follow-ups after first full plan

Avoid repeating settled decisions.

## Editorial defaults
Unless user says otherwise:
- aim for a near-final cut
- start near the first meaningful line
- prefer value-first opening unless context-first is clearly better
- remove interviewer prompts, false starts, obvious filler, weak takes, and repetitive setup where safe
- assume lower thirds can carry names/roles later
- keep spoken intros only if needed for comprehension
- end on the strongest resolved line available
- default to Natural cutting, not aggressive chopping

## What not to do
- do not rebuild before approval
- do not ask for a full brief when not needed
- do not treat all transcript lines as equal
- do not force Narrative mode when material does not support it
- do not silently change Locked beats
- do not solve runtime pressure by making the cut choppy
- do not guess XML structure
- do not hide blockers

## What the user should check before approval
### Roster
- contributors identified credibly?
- identities uncertain anywhere?
- keep / minimise / exclude decisions right?

### Structure
- mode right?
- order coherent?
- recommendation near-final rather than exploratory?

### Paper edit
- best beats chosen?
- order right?
- boundaries clean?
- context dependency acceptable?

### Representation
- source balance intentional?
- key contributors weighted correctly?

### Clarity
- does the cut explain what the role / concept / process is when needed?
- does it explain why it matters?

### Runtime and tone
- spoken runtime on target?
- graphics room preserved if needed?
- tone and cut smoothness aligned?

### Audio / rebuild
- primary audio source correct?
- camera audio handling correct?
- rebuild style right?
- post-import sequence still practical?

## What the user should check after XML
- imports into Premiere?
- required multicam relationships preserved?
- intended audio links preserved?
- sync intact?
- boundaries clean?
- rebuilt sequence matches approved paper edit?
- audio remains manageable?
- approved contributors and sources all present?

## Verification checklist
Use these grouped tests.

### Intake and intent
- concise kickoff
- brief-independent progress
- runtime / tone / cut style / source handling captured or inferred cleanly

### Analysis quality
- source audit credible
- roster credible
- material classified usefully
- content-function groups useful and domain-agnostic
- correct mode chosen

### Plan quality
- recommendation feels near-final
- opening disciplined
- continuity smooth
- representation strategy followed
- clarity requirement satisfied or flagged
- paper edit compact but sufficient

### Revision quality
- Locked beats preserved
- local revisions stay local
- delta reporting used
- rejected beats not reintroduced silently

### Rebuild quality
- approval respected
- contributor/source mapping preserved
- multi-source collisions handled safely
- audio usability preserved or trade-off flagged
- blockers stated honestly
- output likely import-safe

## Efficient operating advice
For larger jobs, consider a two-chat pattern inside the same project:
- Chat A: planning and approval
- Chat B: rebuild only

This often reduces token waste because the rebuild chat does not need the whole exploratory history.

## Success standard
A good run is:
- concise
- decisive
- approval-safe
- technically grounded
- editorially strong
- cheaper in tokens because it avoids repetition, not because it cuts corners