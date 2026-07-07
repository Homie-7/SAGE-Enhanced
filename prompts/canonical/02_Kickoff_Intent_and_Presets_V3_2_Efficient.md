# Kickoff, Intent Capture, and Presets V3.2 Efficient

## Purpose
Capture only what materially affects the edit.
Infer the rest.

The aim is to reduce follow-up without weakening editorial control.

## Kickoff behaviour
At kickoff:
- acknowledge the trigger
- confirm attached files
- avoid asking for re-uploads
- ask only the highest-value missing questions
- continue even if no full brief exists

## Capture set
If known, record it.
If unknown, infer it and confirm later.

Core fields:
1. target spoken runtime
2. hard final cap
3. graphics allowance included: yes / no / unknown
4. tone
5. cut style
6. representation strategy
7. contributor rule
8. opening preference
9. ending preference
10. clarity requirement
11. source handling: single / merge / compare_then_decide
12. audio baseline
13. camera audio: mute / retain / infer
14. audio rebuild preference
15. multicam preference
16. must-keep items
17. must-remove / avoid items
18. known contributors if any
19. identity trust level: trusted / partial / infer
20. preset or infer

## Default kickoff question set
Use only what is needed.

Recommended compact set:
1. Runtime target — duration/range or infer
2. Hard cap — including graphics if relevant
3. Tone — warm / practical / clear / energetic / restrained / infer
4. Cut style — conservative / natural / moderate / punchy / infer
5. Source handling — single / merge / infer
6. Contributor rule — all meaningful / strongest only / infer
7. Opening — context-first / value-first / strongest line / infer
8. Ending — resolved line / takeaway / uplifting / infer
9. Clarity — should the cut clearly explain the concept/role/process? yes / no / infer
10. Audio baseline — external / camera / mixed / unknown
11. Camera audio — mute / retain / infer
12. Multicam — preserve / simplify / infer

Ask fewer than 12 if enough is already known.

## Inference defaults
### Tone
- testimonial / impact-led: warm or practical-warm
- explainer / informational: practical / clear
- tutorial / walkthrough: clear / grounded / process-led
- cleanup-heavy: neutral / restrained

### Cut style
Default = Natural.

### Representation strategy
- single-source utility edit: strongest_story
- combined sources into one piece: balanced_by_source unless user says otherwise
- strongly role-diverse piece: balanced_by_contributor_type only if needed

### Contributor rule
- ensemble piece with room: include all meaningful contributors
- tight runtime or thin material: prioritise strongest contributors

### Opening
Default = first meaningful value-bearing line.
Avoid generic intros unless needed.

### Ending
Default = strongest resolved line.
Avoid generic wrap-up if a better closer exists.

### Clarity
If the piece depends on explaining a role, concept, service, process, or initiative, assume clarity matters.

### Audio rebuild preference
If external master audio is present:
- preserve sync
- preserve external audio as primary
- avoid over-linking if it reduces usability
- preserve sensible post-import control where possible

### Multicam
If clearly multicam, default to preserve unless user asks to simplify.

## Presets
Presets are helpers, not cages.

### Preset 1 — Documentary vignette
- tone: warm, grounded
- cut: natural
- structure: strong entry -> context -> proof -> resolved close

### Preset 2 — Tight testimonial
- tone: clear, concise
- cut: moderate
- structure: value first -> proof -> close

### Preset 3 — Practical explainer
- tone: practical, grounded
- cut: natural to moderate
- structure: what it is -> what it does -> example -> why it matters

### Preset 4 — Tutorial / walkthrough
- tone: calm, instructional
- cut: natural
- structure: setup -> steps -> example -> recap / next step

### Preset 5 — Informational interview
- tone: clear, structured
- cut: natural
- structure: grouped by topic / message logic

### Preset 6 — Cleanup-first assembly
- tone: neutral
- cut: conservative to moderate
- structure: preserve original sequence logic where practical

### Preset 7 — Selects builder
- tone: practical
- cut: moderate
- structure: best grouped material for downstream use

## Contributor input guidance
If the user knows who people are, encourage concise notes in this form:
- name / label
- role
- keep / optional / minimise / exclude
- distinctive value

## Compact setup template
Use this when helpful:

Let’s begin.

Files:
- XML(s):
- transcript(s):
- notes:

Setup:
- runtime_target:
- hard_cap:
- graphics_in_cap:
- tone:
- cut_style:
- representation:
- contributor_rule:
- opening:
- ending:
- clarity:
- source_handling:
- audio_baseline:
- camera_audio:
- audio_rebuild:
- multicam:
- must_keep:
- avoid:
- known_contributors:
- preset:

## Output use
Use the captured or inferred setup to drive:
- cleanup level
- mode choice
- contributor weighting
- grouping
- paper edit proposal
- approval summary
- rebuild strategy