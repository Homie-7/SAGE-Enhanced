# Task: paper_edit

Produce the paper edit — the near-final editorial recommendation as a beat
table. This is the central artefact the human will review, lock, reject, and
approve.

## Canonical references
- 01_Project_Instructions_V3_2_Efficient.md — §9 Paper edit
- 03_Structuring_and_Approval_V3_2_Efficient.md — §Paper Edit Table,
  §Beat status meanings, §Uncertainty labels

## Task instruction
- One beat per row: BID (B1, B2, …), src, cid, func, quote_stub,
  est_duration (seconds), boundary_status, confidence, include_reason,
  seg_ids (real segment IDs from classification — required).
- DATA RULES (Compact-Mode discipline as data, not prose):
  - `quote_stub` only: "first words … last words". Never emit `exact_quote`;
    it is resolved deterministically from the transcript at locking.
  - `status` is `candidate` for every beat. Humans lock/reject; you do not.
- Apply the cleanup strategy and mode already settled. Respect contributor
  statuses (excluded contributors do not get beats).
- Surface uncertainty honestly via `uncertainty_labels`
  (e.g. SENTENCE_SEAM_RISK on tight boundaries).
- Add `representation_summary`, `clarity_summary`, `main_risks` at top level.
- Aim for smooth, non-choppy cutting: prefer fewer, well-bounded beats over
  many fragments.

## Context provided
Structured project state relevant to this task is appended as JSON.

## Output
A single JSON object valid against the appended schema. No prose.
