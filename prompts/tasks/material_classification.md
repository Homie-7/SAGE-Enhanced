# Task: material_classification

Classify the transcript into contiguous segments using the canonical
material labels.

## Canonical references
- 01_Project_Instructions_V3_2_Efficient.md — §5 Material classification

## Task instruction
- Cover the meaningful transcript content with non-overlapping segments
  (S1, S2, …) in transcript order.
- `transcript_span` = [start, end) CHARACTER OFFSETS into the transcript
  exactly as provided (including timecodes/speaker labels inside the span is
  fine; offsets must be accurate).
- `time_span` = [start_seconds, end_seconds] on the source timeline, taken
  from the transcript timecodes bracketing the segment.
- Assign `cid` from the roster; use the canonical label set only.
- Mark interviewer prompts, false starts, and poor takes with their honest
  labels — they are how the edit stays clean.

## Context provided
Structured project state relevant to this task is appended as JSON.

## Output
A single JSON object valid against the appended schema. No prose.
