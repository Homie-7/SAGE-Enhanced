# Prompt architecture

Four layers, physically separated:

- `canonical/` — the SAGE V3.2 Efficient files, **verbatim**. The editorial
  source of truth. Never edited per provider, never edited by scaffolding.
- `tasks/` — one template per LLM task. Templates *reference* canonical
  sections; they do not paraphrase or restate the SAGE brain.
- `overlays/` — small per-provider deltas (formatting/instruction quirks
  only). If an overlay restates workflow logic, that is a design violation.
- `configs/` — provider capability JSON (limits, chunking, JSON strategy).

Assembly per task = canonical excerpts + task template + structured state
context + provider overlay + output JSON schema.
(See `backend/app/orchestration/tasks/assembly.py`.)
