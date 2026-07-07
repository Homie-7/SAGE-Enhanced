# SAGE Internal V1 — Stage 7 checkpoint

Date: 2026-07-07 · Intent: first live-provider benchmark on LND ·
Outcome: **no live LLM run was possible in this environment** — recorded
honestly below — but the pass produced the first structural validation of
the deterministic pipeline against real Premiere exports, and left the live
run exactly one credential away.

## What ran

- **Real-export rebuild probes (new validation result).** All three real
  Premiere exports — LND ElectroTech (xmeml v4, 30fps NTSC, V2/A6), LND
  Interior Design (v4, V3/A6), TSS rough cut (xmeml **v5**, 25fps, 147
  clips, non-zero in-points, 2-link groups) — pass the full
  parse → deterministic rebuild → XML integrity suite with **zero code
  changes**. This is the first time SAGE's XML engine has been exercised
  against genuinely real production files. Import safety remains WARN by
  design (only Premiere can prove it).
- **Provider gate, in priority order.** VAL attempt: blocked — no
  `endpoint.base_url`/`api_style`/`model` in `prompts/configs/val.json`
  and no `VAL_API_KEY` (facts never supplied). Claude fallback attempt:
  blocked — no `ANTHROPIC_API_KEY` on this host (verified: the API
  correctly refuses keyless calls). Both attempts failed fast at the
  readiness gate with the exact missing facts, before creating any state —
  the designed managed-service failure behaviour, now demonstrated on real
  inputs.
- **LND fully prepared.** SAGE-ingest transcripts generated for both
  sources (`derived/*_transcript_sage.txt`, correct `[HH:MM:SS] SPEAKER:`
  format). The live run is one command, printed by
  `benchmark_case.py prepare` — nothing else stands in the way.
- Run record persisted at
  `benchmarks/cases/lnd_showcase/runs/stage7-preflight/record.json`.

## Validation distinctions (unchanged, deliberately)

- **Benchmark validation**: framework + comparator ready; awaits a SAGE
  output to compare (needs a live provider).
- **Provider validation**: neither VAL nor Claude has produced a task on
  this material yet.
- **Premiere re-import validation**: untouched; only Premiere can provide it.

## LND status

Planning + comparison benchmark within V1 scope, per source:
ElectroTech is the primary target (aligned transcript, ~7k tokens — fits
Claude comfortably; exceeds nothing). A full V1 run produces a
single-source cut from one synced timeline; the human final combines two
sources, so comparison against it measures single-source selection quality,
not a like-for-like replication — stated in every report by the comparator's
limits. Interior Design (~14–18k tokens) exceeds the assumed VAL 16k context
single-pass; Claude fits.

## TSS status (constrained heritage benchmark — caveat preserved)

Transcript belongs to a longer sequence than the rough cut (4537s vs 2022s);
recorded permanently in `case.json`. Additionally only ~50% of the human
final's material exists in the rough cut. TSS still contributes: the only
xmeml v5 structural test, the only non-zero-in-point rebuild test on real
media, and a worked example of the framework refusing to hide bad input
alignment.

## To run the live benchmark (operator, admin/dev deployment)

VAL: fill `prompts/configs/val.json` endpoint block + `export VAL_API_KEY=…`.
Claude fallback: `export ANTHROPIC_API_KEY=…`. Then:
`python scripts/benchmark_case.py prepare lnd_showcase --source electrotech`
and run the printed live-loop command; compare with the printed compare
command using `--run-label <provider>-<date>`.

## Privacy

Real transcripts live under `backend/benchmarks/cases/*/inputs/`. Treat as
sensitive; confirm consent/policy before pushing anywhere shared.
