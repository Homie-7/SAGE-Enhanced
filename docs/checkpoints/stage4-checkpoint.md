# SAGE Internal V1 — Stage 4 checkpoint

Date: 2026-07-07 · Status: core loop working end-to-end; awaiting real
Premiere round-trip · Posture: internal managed service (VAL-first,
provider-agnostic skeleton, provider choice hidden from standard users).

## What works

- **Full core loop**, engine- and HTTP-verified (21 tests + live server
  smoke): create project → upload XML + transcript → quick setup (blank =
  infer) → canonical planning pipeline (source audit → contributor roster →
  material classification → function grouping → mode/structure → paper edit)
  → review with per-beat lock / reject / reopen → targeted revision with
  deterministic lock enforcement (illegal revisions rejected with blockers,
  state untouched) → approval gate (locks kept beats, resolves exact quotes
  verbatim from the transcript) → deterministic Style B rebuild from real
  source clipitems → full validation suite → download of the edited FCP7 XML.
- **Rebuild refused before approval (403); download refused before
  completion (409, with blockers).**
- **Premiere-realistic XML handling**: parser/rebuilder tested against the
  structural shape of real Premiere FCP7-XML exports (project wrapper,
  pproTicks, masterclipid, id-only file refs, sourcetrack, stereo pairs on
  two mono tracks, transitions, generators, markers, filters). Clip
  resolution is deterministic from the timeline span; beats spanning two
  source clips are refused with an exact blocker; dropped-intent elements
  (transitions/titles) are reported, never silently ignored.
- **Real-export tooling**: `backend/scripts/audit_real_export.py`
  (`--rebuild-probe`) audits any export and integrity-checks a deterministic
  rebuild; `docs/real-export-checklist.md` is the full round-trip procedure.
- **Managed-service rules, server-enforced**: standard deployments assign the
  configured provider (VAL in production), reject provider selection (403),
  and redact `provider`/`provider_history` from API responses. Admin/dev
  mode (`SAGE_ADMIN_MODE=1`) enables per-project selection and explicit,
  reason-recorded provider changes. Provider facts are always recorded in
  project state for audit. No silent switching anywhere.
- **Frontend**: all seven pages of the core loop wired, lean plain HTML,
  type-checked, production build passing. Admin provider controls appear
  only when `/api/meta` reports admin mode.
- **Benchmark**: Teacher Success Story fixtures drive the mock provider so
  the entire loop runs deterministically at zero LLM cost.

## What remains stubbed

- **VAL adapter** — clean stub; fails honestly until programmatic access is
  confirmed. Wiring it touches only `providers/val.py` +
  `prompts/configs/val.json`.
- **Benchmark source XML** — structurally faithful but synthetic, flagged in
  `benchmark.json`; to be replaced by a real Premiere export.
- **LND Specialist Showcase** — fixture structure wired, awaiting material.
- **`validation_review` LLM task** — unused in V1 (deterministic validation
  covers it).
- **Transcript chunking** — single-pass; oversized input fails explicitly.
- **Rebuild styles A and C** — explicitly refused; Style B only in V1.

## Next highest-value step

Obtain one real Premiere FCP7-XML export of a synced interview (plus its
timecoded transcript), run `audit_real_export.py --rebuild-probe`, run the
loop, and complete the Premiere re-import checklist. That single file
converts the largest remaining unknown into evidence and replaces the
synthetic benchmark XML.

## Key production risks

1. **Premiere import acceptance is unproven** — media relinking (`pathurl`),
   sequence-header tolerance, AV sync at beat boundaries, and channel
   behaviour on re-import can only be proven in Premiere itself.
2. **VAL is unwired** — production posture assumes a provider that cannot
   yet run a task; until wired, real runs require admin mode + the Claude
   fallback (server-side credential).
3. **Planning quality on real material is untested** — mock fixtures are
   span-locked to the synthetic transcript; a live-provider run on real
   material is required before trusting paper-edit quality.
4. **Admin/standard distinction is deployment-env only** — no
   authentication layer; acceptable on a trusted internal network, revisit
   before wider rollout.
5. **SQLite single-writer** — fine for a small internal team; the store
   interface allows a Postgres swap without redesign if concurrency grows.
