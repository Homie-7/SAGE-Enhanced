# Task: rebuild_plan

Plan the rebuild. You map beats to real source material; deterministic code
builds the XML. You never write XML.

## Canonical references
- 04_XML_Builder_Spec_and_Audio_Behaviour_V3_2_Efficient.md —
  §Structural source rule, §Beat fidelity rule, §Rebuild styles,
  §External audio policy, §Provenance rule

## Task instruction
- One mapping per LOCKED beat, in the approved beat order. Every locked beat
  must be mapped; rejected beats must not appear.
- `in_seconds` / `out_seconds`: positions on the SOURCE TIMELINE (matching
  transcript timecodes), taken from the beat's segment time spans. Trim to
  clean boundaries; never extend beyond the segment's material.
- `clipitem_refs`: real clipitem IDs from source_facts.track_structure that
  cover the span. Never invent IDs.
- `audio_handling` / `track_handling`: short notes per Style B — preserve
  sync, keep external audio independently manageable, avoid over-linking.
- `provenance_notes`: one line per beat (BID, source position, boundary
  status, uncertainty if any).
- Flag seam risks in `seam_risks`.

## Context provided
Structured project state relevant to this task is appended as JSON.

## Output
A single JSON object valid against the appended schema. No prose.
