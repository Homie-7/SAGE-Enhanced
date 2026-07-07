# Task: contributor_roster

Build the contributor roster from the transcript.

## Canonical references
- 01_Project_Instructions_V3_2_Efficient.md — §4 Contributor resolution,
  §Uncertainty labels

## Task instruction
- Assign a stable CID per distinct speaker (C1, C2, …).
- Use provisional labels where identity is not certain; note ambiguity in
  `ambiguity_note` and reflect it in `confidence` (high/medium/low).
- Set `status` per canonical rules: interviewer prompts and off-mic voices
  that should not appear in the cut are `exclude` or `minimise`.
- `value_note`: one short phrase on what this contributor offers the edit.
- Never merge speakers you cannot confidently resolve as the same person.

## Context provided
Structured project state relevant to this task is appended as JSON.

## Output
A single JSON object valid against the appended schema. No prose.
