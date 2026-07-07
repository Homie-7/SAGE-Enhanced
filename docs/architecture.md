# SAGE Internal V1 — Stage 1: Planning and Architecture

Status: awaiting approval before Stage 2 scaffolding.

---

## 1. Architecture summary

SAGE Internal V1 is a thin, reliable application wrapped around the canonical SAGE editorial methodology. Four layers:

```
┌─────────────────────────────────────────────────────┐
│ FRONTEND (React SPA)                                │
│ core loop only: upload → setup → review → approve   │
│ → rebuild → download                                │
├─────────────────────────────────────────────────────┤
│ BACKEND API (FastAPI, Python)                       │
│ projects, uploads, phase triggers, approvals,       │
│ downloads                                           │
├─────────────────────────────────────────────────────┤
│ ORCHESTRATION ENGINE                                │
│ canonical SAGE phase machine · task runner ·        │
│ decision ledger · revision discipline · beat locks  │
├──────────────────────────┬──────────────────────────┤
│ PROVIDER LAYER           │ DETERMINISTIC LAYER      │
│ adapter interface        │ XML parse + rebuild      │
│ VAL adapter (stub)       │ engine · schema          │
│ Claude adapter           │ validation · lock        │
│ mock adapter             │ enforcement · output     │
│ capability configs       │ validation · failure     │
│ prompt overlays          │ reporting                │
└──────────────────────────┴──────────────────────────┘
```

Key principles:

- **One canonical pipeline.** The 12-phase SAGE workflow lives once, in the orchestration engine and canonical prompt files. Providers plug in underneath via adapters; they never fork the workflow.
- **LLMs reason, code enforces.** Every LLM task returns structured JSON validated against a schema. The LLM never writes output XML; deterministic code builds it from the approved rebuild plan.
- **State is structured, not conversational.** The project record is the source of truth. LLM calls are stateless tasks fed from structured state, not a long-running chat.
- **Approval is a hard gate in code**, not a prompt convention. The rebuild endpoint refuses to run unless project state is `approved`.

### Stack (proposed)

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Best ecosystem for XML processing, Pydantic schemas, fast internal deployment |
| Frontend | React + Vite + TypeScript | Simple SPA shell; shared types with backend schemas |
| State | SQLite + JSON columns (file-per-project artefacts on disk) | Zero infra for internal V1; trivially migratable to Postgres later |
| Schemas | Pydantic (backend) + generated TS types | One schema definition, two consumers |
| LLM tasks | Provider adapter interface (async) | VAL / Claude / mock behind one contract |

---

## 2. Preserve vs rebuild matrix

| SAGE element | Decision | Notes |
|---|---|---|
| 12-phase workflow order | **Preserve** | Becomes the orchestration state machine |
| Approval gate before rebuild | **Preserve + harden** | Enforced in code, not just prompts |
| Contributor roster schema (CID, role, confidence, keep status) | **Preserve** | Becomes a Pydantic schema |
| Material classification labels | **Preserve** | Enum in schema; canonical file remains the definition source |
| Content-function groups | **Preserve** | Enum in schema |
| Cleanup strategies (Conservative→Aggressive, default Natural) | **Preserve** | Config value in project setup |
| Modes (Narrative / Selects / Cleanup) | **Preserve** | |
| Paper edit table schema (BID, src, CID, func, stub/exact, dur, boundary, conf, why, status) | **Preserve** | Central schema of the whole app |
| Beat statuses (Draft/Candidate/Approved/Locked/Rejected) | **Preserve** | Enforced by a deterministic lock engine |
| Locked-beat rules | **Preserve + harden** | Code diffs every revised paper edit against locks; violations are hard failures |
| Rejected-beat non-reintroduction | **Preserve + harden** | Same diff engine |
| Targeted Revision Mode / delta-only reporting | **Preserve** | Revisions are scoped LLM tasks over affected beats only |
| Decision ledger | **Preserve** | First-class state object, not chat memory |
| Uncertainty labels (IDENTITY_UNCERTAIN, SENTENCE_SEAM_RISK, etc.) | **Preserve** | Enum; surfaced in UI |
| Failure rule (exact blocker, no vague language) | **Preserve** | Structured `ValidationReport` with explicit blockers |
| Inference defaults + presets (kickoff file 02) | **Preserve** | Drive the quick-setup flow defaults |
| Rebuild styles A/B/C + audio behaviour rules (file 04) | **Preserve** | Inform the deterministic rebuild engine's options |
| Validation checklist (files 04/05) | **Preserve** | Converted item-by-item into deterministic checks where possible; LLM review where judgement is required |
| Chat as delivery mechanism | **Rebuild** | Replaced by structured app flow |
| Chat history as state | **Rebuild** | Replaced by structured project state |
| "Compact Mode" token-efficiency conventions | **Rebuild** | Superseded: structured JSON tasks are inherently compact; stub-first quote handling is preserved as a data rule |
| Two-chat split (plan chat / rebuild chat) | **Rebuild** | Superseded by stateless tasks + structured state |
| LLM writes rebuild XML | **Rebuild (mechanism), preserve (intent)** | Canonical rule says "do not generate guessed XML". V1 enforces this maximally: LLM outputs a rebuild plan (beat → clip mappings); deterministic code clones/trims/reorders the real source XML |
| Claude-specific setup instructions (README project setup) | **Rebuild** | Replaced by prompt architecture below |

Nothing in the editorial methodology is rewritten. The canonical `.md` files ship inside the repo verbatim as the prompt core.

---

## 3. True MVP scope

**In:**

1. Create project
2. Upload XML(s) + transcript(s) (+ optional notes)
3. Quick setup — the compact kickoff question set from file 02, with "infer" as the default everywhere
4. Run planning phases (audit → roster → classification → grouping → mode → paper edit) as orchestrated LLM tasks
5. Paper edit review screen: beats, statuses, confidence, uncertainty labels, roster, approval summary
6. Revise (targeted, delta-only) or approve (per-beat lock/reject + whole-plan approval)
7. Rebuild: LLM produces rebuild plan → deterministic engine builds output XML
8. Validation: deterministic checks + structured report surfaced in UI
9. Download validated XML (or an explicit, honest failure report)

**Out (explicitly):** marketing pages, plugins, multi-user collaboration, analytics, advanced onboarding, multi-source merge polish (schema supports multi-source; UI optimises single-source first), auth beyond a simple internal gate, speculative features.

---

## 4. Repo / folder structure

```
sage-internal/
├── README.md
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                  # FastAPI entry
│   │   ├── api/                     # route modules
│   │   │   ├── projects.py
│   │   │   ├── uploads.py
│   │   │   ├── phases.py            # trigger analysis, revision, rebuild
│   │   │   ├── review.py            # approve / lock / reject / revise
│   │   │   └── outputs.py           # validation report, download
│   │   ├── orchestration/
│   │   │   ├── engine.py            # phase state machine
│   │   │   ├── tasks/               # one module per LLM task
│   │   │   ├── ledger.py            # decision ledger management
│   │   │   └── revision.py          # targeted revision + lock diffing
│   │   ├── providers/
│   │   │   ├── base.py              # ProviderAdapter interface
│   │   │   ├── claude.py
│   │   │   ├── val.py               # stub until API confirmed
│   │   │   ├── mock.py              # fixture-driven, for tests/dev
│   │   │   └── registry.py          # config-driven selection
│   │   ├── schemas/                 # Pydantic: state + task I/O
│   │   ├── xmlengine/
│   │   │   ├── parser.py            # FCP7 XML parse + audit facts
│   │   │   ├── rebuilder.py         # clone/trim/reorder from source
│   │   │   └── timing.py            # frames / samples / pproTicks
│   │   ├── validation/
│   │   │   ├── schema_checks.py
│   │   │   ├── lock_enforcement.py
│   │   │   ├── plan_fidelity.py     # beats ↔ segments mapping
│   │   │   ├── xml_integrity.py
│   │   │   └── report.py            # structured ValidationReport
│   │   └── storage/                 # SQLite + project artefact store
│   └── tests/
│       └── fixtures/                # sample XML, transcripts, golden outputs
├── frontend/
│   ├── package.json
│   └── src/
│       ├── pages/                   # Upload, Setup, Processing, Review,
│       │                            # Rebuild, Download
│       ├── components/              # PaperEditTable, RosterTable,
│       │                            # ApprovalSummary, ValidationReport
│       ├── api/                     # typed client
│       └── types/                   # generated from backend schemas
├── prompts/
│   ├── canonical/                   # SAGE V3.2 files, verbatim
│   ├── tasks/                       # task templates (see §6)
│   ├── overlays/                    # claude.md, val.md
│   └── configs/                     # provider capability JSON
└── docs/
    └── architecture.md              # this document, maintained
```

---

## 5. Provider strategy

**Adapter interface** (single contract):

```python
class ProviderAdapter(Protocol):
    name: str
    capabilities: ProviderCapabilities

    async def run_task(
        self,
        task: TaskSpec,          # assembled prompt + schema + context
    ) -> TaskResult:             # raw text + parsed/validated JSON + usage
```

**Capability config** per provider (JSON, not code):

```json
{
  "provider": "val",
  "max_context_tokens": 32000,
  "max_output_tokens": 4000,
  "supports_system_prompt": true,
  "supports_json_schema_mode": false,
  "json_strategy": "prompt_and_repair",
  "chunking": { "transcript_chunk_tokens": 8000, "overlap_tokens": 400 },
  "retry": { "max_attempts": 2, "repair_prompt": true }
}
```

- **VAL-first**: registry resolves `SAGE_PROVIDER=val` by default in RMIT deployment. The VAL adapter ships as a stub with the interface and config in place; wiring it is a small, isolated task once programmatic access is confirmed.
- **Claude as dev/fallback provider**: fully implemented adapter against the Anthropic API. Fallback is explicit configuration, never silent switching mid-project (provider used is recorded in project state for auditability).
- **Mock provider**: returns fixture responses; enables full end-to-end testing of orchestration, locks, and validation with zero LLM cost and total determinism.
- **JSON reliability strategy**: schema validation on every task result; on failure, one bounded "repair" round-trip; on second failure, explicit task failure surfaced honestly (per SAGE failure rule). Providers with native JSON/schema modes use them via config; others use prompt-and-repair.
- **No per-provider pipelines.** Differences are absorbed by: adapter (transport/auth), capability config (limits, chunking, JSON strategy), overlay (small prompt adjustments). That's the whole surface.

---

## 6. Prompt system strategy

Four layers, assembled at task time:

```
prompts/
├── canonical/            # SAGE V3.2 md files — verbatim, never edited per provider
├── tasks/                # one template per LLM task
│   ├── source_audit.md
│   ├── contributor_roster.md
│   ├── material_classification.md
│   ├── function_grouping.md
│   ├── mode_and_structure.md
│   ├── paper_edit.md
│   ├── targeted_revision.md
│   ├── rebuild_plan.md
│   └── validation_review.md      # LLM-side judgement checks only
├── overlays/
│   ├── claude.md          # e.g. tool-use/formatting quirks
│   └── val.md
└── configs/               # capability JSON per provider
```

Assembly per task = **relevant canonical excerpts + task template + structured state context + provider overlay + output JSON schema**. Task templates reference canonical sections rather than paraphrasing them, so the SAGE brain stays in one place. Overlays are small deltas (formatting, instruction phrasing quirks) — if an overlay starts restating workflow logic, that's a design violation.

Each planning phase maps to one task with a strict JSON output schema mirroring the canonical schemas (roster fields, paper edit fields, beat statuses, uncertainty labels). Quote-stub-first discipline is a data rule: paper edit tasks emit stubs; exact quotes are resolved deterministically from the transcript for shortlisted/approved beats.

---

## 7. Structured state model

Project is the aggregate root. Sketch (Pydantic-defined; abbreviated):

```
Project
├── meta:            id, name, created_at, provider_used, phase, version
├── inputs:          xml_files[], transcripts[], notes[], checksums
├── setup:           the file-02 capture set (runtime_target, hard_cap, tone,
│                    cut_style, representation, contributor_rule, opening,
│                    ending, clarity, source_handling, audio_baseline,
│                    camera_audio, multicam, must_keep[], avoid[], preset)
│                    — each field: value + origin: user|inferred|default
├── source_audit:    frame_rate, tracks, sync_baseline, linked_audio,
│                    tech_risks[], source_count, material_type_guess
├── roster:          Contributor[] {cid, label, role, source, confidence,
│                    status: keep|optional|minimise|exclude, value_note,
│                    ambiguity_note?}
├── classification:  Segment[] {seg_id, source, span, label, cid?, conf}
├── groups:          FunctionGroup[] {func, seg_ids[], note}
├── structure:       {mode, cleanup_strategy, order[], rationale}
├── paper_edit:      version, Beat[] {bid, src, cid, role, func,
│                    quote_stub | exact_quote, est_duration, boundary_status,
│                    confidence, include_reason, representation_note?,
│                    graphics_note?, uncertainty_labels[],
│                    status: draft|candidate|approved|locked|rejected}
├── ledger:          DecisionLedger — settled decisions with origin + timestamp
├── revisions:       RevisionDelta[] {changed_bids[], reason, runtime_effect,
│                    contributor_effect, risk_effect, paper_edit_version}
├── approval:        {approved_by, at, approved_items[], accepted_risks[]}
├── rebuild:         {style: A|B|C, plan: BeatMapping[] {bid → source clip
│                    in/out, track handling, audio handling}, provenance[]}
├── validation:      ValidationReport {checks[] {name, pass|fail|warn,
│                    detail}, blockers[], overall}
└── output:          {xml_path, checksum, produced_at} | null
```

Phase state machine (enforced server-side):

```
created → inputs_uploaded → setup_complete → analysing → paper_edit_ready
→ in_review ⇄ revising → approved → rebuilding → validating
→ complete | failed (with explicit blockers)
```

Paper edit is versioned; every revision produces a delta record; the lock engine diffs versions to guarantee locked beats are byte-identical (or explicitly flagged) and rejected BIDs never reappear.

---

## 8. Validation strategy

**Deterministic (code):**

| Check | Mechanism |
|---|---|
| Task I/O schema validity | Pydantic on every LLM response |
| State transitions legal | Phase machine guards |
| Approval gate | Rebuild endpoint hard-fails unless phase = `approved` |
| Lock enforcement | Version diff: locked beats unchanged, rejected beats absent |
| Beat→segment mapping | Every approved/locked BID maps to a real source clip span |
| Quote fidelity | Exact quotes verified as substrings of transcript spans |
| XML well-formedness | Parser round-trip |
| XML integrity | File defs valid, refs resolvable, required tracks preserved, links valid for chosen style |
| Timing coherence | Frame/sample maths, pproTicks recalculation, sync offsets |
| Plan fidelity | Rebuilt sequence order/content matches approved paper edit |
| Output completeness | No locked beat dropped; forced substitutes disclosed |

**LLM (judgement only):** classification quality, grouping, structure rationale, revision suggestions, seam-risk assessment, clarity/representation summaries. LLM never grades its own technical output — that's the deterministic layer's job.

**Failure reporting:** every failure is a structured blocker `{check, why_it_blocks, what_is_needed}` — the canonical failure rule, in code. No vague language, no guessed output.

---

## 9. Technical risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | VAL has no (or limited) programmatic API | Medium–High | High | Adapter interface + stub now; Claude fallback fully working; capability config absorbs limitations (context size, no JSON mode) |
| 2 | FCP7 XML complexity (pproTicks, links, multicam) breaks rebuilds | Medium | High | Deterministic XML engine owns all structure; clone-from-source only; fixture-based tests against real Premiere exports; import-test checklist |
| 3 | Long transcripts exceed provider context | Medium | Medium | Chunking strategy in capability config; classification runs per-chunk with deterministic merge; audit facts extracted by code, not LLM |
| 4 | Inconsistent JSON output across providers | Medium | Medium | Schema validation + one repair round + honest failure; native schema modes where available |
| 5 | Diarisation/identity errors propagate | Medium | Medium | Canonical rule preserved: provisional labels, confidence, IDENTITY_UNCERTAIN surfaced in review UI; human confirms roster |
| 6 | Lock/revision drift (LLM quietly alters locked beats) | Medium | High | Locked beats never sent as editable context; deterministic diff hard-fails violations |
| 7 | RMIT data governance / where transcripts may be sent | Medium | High | VAL-first default; provider recorded per project; Claude use is explicit opt-in config |
| 8 | Scope creep beyond core loop | High | Medium | This document's MVP scope is the contract; Stage 3 implements only the listed flow |
| 9 | Premiere import edge cases only visible in Premiere | Medium | Medium | Validation reports "likely import-safe", never certainty; user post-import checklist (file 05) surfaced in UI |

---

## 10. Phased implementation plan

**Stage 2 — Scaffolding** (next, on approval): repo structure above; FastAPI shell with routes stubbed; React shell with the six core-loop pages stubbed; orchestration engine skeleton (phase machine, task runner interface); provider adapter interface + mock + Claude/VAL stubs + configs; prompts folder with canonical files copied in and task/overlay placeholders; full Pydantic schema set + generated TS types; validation module skeletons; fixture folder with one sample project.

**Stage 3 — Core loop** (on approval): project creation; upload flow with deterministic XML/transcript ingest; quick setup flow with inference defaults; planning orchestration end-to-end (mock + Claude); paper edit review UI with beat statuses, lock/reject, approval summary; targeted revision with delta + lock enforcement; approval gate; rebuild plan task + deterministic rebuild engine (Style B default) or explicit placeholder if XML engine needs more fixtures; validation report surface; download.

**Post-V1 (not now):** VAL adapter wiring once API confirmed; multi-source merge UI; rebuild styles A/C polish; benchmark harness expansion; auth hardening.

---

## Approval checkpoint

Stage 1 complete. Confirmations that would help before Stage 2 (defaults will be used if you simply approve):

1. Stack: FastAPI + React + SQLite — acceptable for internal V1?
2. The "LLM plans, code builds XML" rebuild mechanism — confirmed as the right reading of the canonical rule?
3. Any known facts about VAL's interface worth encoding in the stub now?

Reply **"Approved. Proceed to Stage 2 scaffolding only."** when ready.
