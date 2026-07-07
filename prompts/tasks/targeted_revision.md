# Task: targeted_revision

Targeted Revision Mode (canonical: 01 §Revision rule, 03 §Targeted Revision Mode).

Hard rules:
- Locked beats are provided as **read-only context**. Do not modify, replace,
  materially shorten, reorder, or reframe them. They are not candidates.
- Rejected beats must not be reintroduced unless listed as explicitly reopened.
- Revise only the affected beats. Output a delta, never a full replan.
- If a technical blocker affects a locked beat, flag it explicitly in the
  delta's risk_effect — do not work around it silently.

(The deterministic lock engine independently verifies all of the above;
violations are hard failures.)

## Canonical references
- 01_Project_Instructions_V3_2_Efficient.md — §Revision rule, §Uncertainty labels
- 03_Structuring_and_Approval_V3_2_Efficient.md — §Targeted Revision Mode, §Locked beat rule

## Context provided
- locked beats (read-only), rejected BIDs, editable beats, decision ledger,
  the user's revision instruction, explicitly reopened BIDs (if any)

## Output
A single JSON object valid against the RevisionOutput schema. No prose.
