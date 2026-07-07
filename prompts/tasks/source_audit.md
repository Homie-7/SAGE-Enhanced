# Task: source_audit

Assess editorial and technical risk for this job. Deterministic structural
facts (frame rate, tracks, clipitems, multicam/external-audio detection) are
already extracted by code and provided as context — do not restate or second-
guess them. Your job is judgement: what could make this edit risky, and what
kind of material is this?

## Canonical references
- 01_Project_Instructions_V3_2_Efficient.md — §3 Source audit, §4 Contributor handling

## Task instruction
From the transcript and the deterministic source facts:
- list concrete tech/editorial risks (`tech_risks`) — e.g. crosstalk,
  long-pause sections, identity ambiguity, sync doubts. Empty list if none.
- state the material type (`material_type_guess`) — e.g. interview, tutorial,
  walkthrough, case study, mixed.
- optional short `notes` (one or two sentences max).

Do not invent risks the material does not show. Uncertainty is fine; guessing
is not.

## Context provided
Structured project state relevant to this task is appended as JSON.

## Output
A single JSON object valid against the appended schema. No prose.
