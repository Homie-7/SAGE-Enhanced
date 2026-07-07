# XML Builder Spec and Audio Behaviour V3.2 Efficient

## Purpose
Define rebuild rules that preserve technical validity and practical editability while staying concise.

## Rebuild preconditions
Do not rebuild until these are approved or explicitly accepted:
- contributor roster
- paper edit
- representation strategy
- source handling plan if multi-source
- audio strategy
- acceptable unresolved risks

## Structural source rule
Use synced source XML(s) as the structural source.
Use them to:
- clone
- trim
- reorder
- preserve timing baseline
- preserve real source mapping

Do not invent unmappable structure.

## Beat fidelity rule
The rebuild must preserve the approved paper edit.
Before handoff, verify:
- each Approved/Locked beat maps to a real source segment
- no Locked beat was dropped
- Rejected beats did not reappear
- any forced substitute is disclosed

## Rebuild styles
State one style.

### Style A — Maximum structural preservation
Use when preserving original relationships is the priority.
- preserve multicam aggressively
- preserve original-like linking aggressively

### Style B — Editorial usability first
Use when finishing flexibility in Premiere matters most.
- preserve sync
- preserve primary external audio
- avoid unnecessary link complexity
- keep external audio independently manageable where possible

### Style C — Simplified handoff
Use when a cleaner finishing sequence matters more than full structural preservation.
- preserve sync and approved content
- simplify angle/audio complexity where safe

If user does not specify, infer and state the choice before rebuild.

## Multi-source rules
If multiple source packages exist:
- namespace file IDs by source
- prevent cross-source collisions
- preserve source provenance per beat
- preserve approved source balance
- make cross-source transitions intentional

## Provenance rule
For each rebuilt beat, keep or report:
- BID
- source
- contributor
- approximate source position
- boundary status
- uncertainty marker if any

## External audio policy
If external master audio exists:
- preserve sync alignment
- preserve intended audio baseline
- do not assume strict linking is always best
- keep external audio manageable after import where possible
- avoid over-linking if it reduces practical control

## Audio capture when relevant
Capture or infer:
- primary sync audio source
- camera audio mute/retain rule
- whether external audio should stay independently manageable
- whether strict link preservation is required
- preferred channel handling if known: original / stereo / dual_mono / editor_decides
- multicam preserve/simplify rule

## Camera audio rule
If camera audio should be muted:
- do not treat it as active editorial bed
- preserve only what is structurally needed unless requested otherwise
- state handling clearly

## Multicam rule
If multicam exists:
- preserve where required
- state preserve_both or single_angle_handoff
- do not assume one style fits every job

## Sentence integrity rule
If a beat cannot be rebuilt cleanly without an unnatural sentence break:
- replace the beat
- shorten elsewhere
- or flag for review

Do not silently force bad seams.

## XML integrity rules
- preserve required track structure
- preserve valid file definitions and references
- preserve or rebuild valid link structures for chosen style
- recalc timing correctly
- preserve coherent pproTicks where needed
- keep clipitems and source refs real and mappable

## Timing rules
- preserve sync alignment
- use source XML frame/sample logic for timing
- use Premiere tick scale only for pproTicks
- do not guess missing technical structure

## Validation checklist
Before handoff, verify:
- XML well formed
- timing coherent
- file definitions valid
- links valid for chosen style
- required tracks preserved
- sync preserved
- contributor mapping correct
- source mapping correct
- sequence matches approved plan
- result likely import-safe
- audio still practical after import

## Audio usability check
State clearly if relevant:
- primary audio remains manageable
- stereo flexibility preserved or reduced
- dual-mono flexibility preserved or reduced
- external audio linked more aggressively than necessary or not
- trade-off between integrity and editability

## Failure rule
If safe rebuild cannot be generated:
- state exact blocker
- explain why it blocks generation
- state what is needed

Do not generate guessed XML.