# SAGE Internal V1 — Stage 8 checkpoint (productisation)

Date: 2026-07-08 · Scope: UI/UX only. No backend, workflow, or API changes;
41 backend tests unchanged and green. All page logic and handlers preserved.

## What changed

- **Design system** (`frontend/src/styles.css`): near-black AMOLED base
  (#0a0a0b), neutral dark surfaces, one red (#e60028) spent only on
  committed moments — primary actions, the approval gate, locked beats.
  Muted green/amber for pass/warn. Helvetica/Arial UI stack; mono face for
  timecodes, beat IDs, phases, and checksums. Focus rings, reduced-motion
  support, mobile breakpoints.
- **Signature element**: the gated workflow rail (`components/Shell.tsx`) —
  the canonical sequence Upload → Setup → Plan → Review ‖GATE‖ Rebuild →
  Deliver drawn as a thin line through numbered nodes; the line fills red as
  phases complete and the gate tick turns red only after approval. It
  encodes the product's core rule rather than decorating.
- **All seven screens rebuilt on the system** with unchanged behaviour:
  projects home (status pills, empty state, admin provider control demoted
  to a small secondary line), upload (three labelled rows with hints and ✓
  confirmations), setup (label/field/hint grid, "leave blank to infer"),
  processing (calm red sweep line + the six pipeline steps in plain
  language), review (cutting-log paper edit: red left rule on locked rows,
  strike on rejected; roster; revision panel; approval summary grid),
  rebuild and download (validation checks as a pass/warn/fail ledger;
  blockers in a red-ruled alert; download only when complete).
- **Copy pass**: user-side language throughout ("Rebuild edited sequence",
  "Approve paper edit", precise error headings), hints explain the canonical
  behaviour without exposing machinery.
- Motion: opacity/transform only — 180ms page enter, 400ms rail fill,
  1.6s processing sweep; nothing loops on settled screens.

## Deliberately unchanged
Managed-service behaviour, provider redaction, workflow order, approval
gate enforcement, all API contracts, benchmark layer.

## Known UI/UX weaknesses for later
1. No screenshot/visual regression harness (no browser in the build env).
2. Paper edit table scrolls horizontally on narrow screens rather than
   reflowing to cards.
3. Revision history (paper_edit_history) has no viewer.
4. No inline confirmation dialog for Reject/Reopen (single-click, though
   reversible via Reopen).
5. Failed-phase recovery guidance is textual only; no retry affordance.
6. Museo (RMIT display face) not embedded — licensed font; system stack
   stands in.

## Stage 8.1 refinement (2026-07-08)

- **Upload correctness**: per-kind content validation server-side — the XML
  field requires a parseable `<xmeml>` with a `<sequence>`; the transcript
  field rejects sequence XML with a redirect message, accepts timecoded text,
  and converts word-timed JSON transcripts to SAGE text at ingest (recorded
  on the file as an ingest note the UI shows). Binary/unknown formats fail
  with precise messages. Client-side extension pre-checks catch mistakes
  before upload. 8 new tests (49 total).
- **Setup hybrid**: tone / cut style / opening / ending / contributors are
  now structured presets using the canonical file 02 vocabulary, each with
  Infer as the default and a "Custom…" free-text override. The stray
  known-contributors field was replaced by the canonical contributor rule.
- **Identity**: wordmark is plain "SAGE" — the red full stop removed.
- **Provider testing (admin/dev only)**: a dashed, visually secondary panel
  on the projects page — readiness per provider from /api/admin/status with
  exact missing-fact details, plus the per-project provider selector for
  test runs. Absent in standard mode; server still enforces.
- **Multi-source**: no upload change. Single-source V1 stated plainly in
  the sequence field hint ("one project per sequence for now"). Proper
  multi-source remains a future engine-level workflow, not an upload tweak.
