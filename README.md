# SAGE Internal V1

Story Assembly and Guidance Engine — a human-led, AI-assisted editorial
workflow for educational video production. Internal RMIT deployment.

SAGE takes a synced timeline XML and transcript, performs editorial analysis
and structuring, presents a paper edit for human review and approval, and only
then produces a rebuild output. It does not replace the editor.

## Non-negotiables (enforced in code, not just prompts)
- human approval before rebuild (server-side gate)
- locked beats stay locked; rejected beats stay rejected (deterministic diff)
- revisions are targeted deltas, not full replans
- uncertainty is visible; failures are explicit and honest
- deterministic validation sits alongside LLM reasoning
- the LLM plans the rebuild; deterministic code builds the XML

## Layout
- `prompts/canonical/` — the SAGE V3.2 editorial source of truth (verbatim)
- `prompts/{tasks,overlays,configs}/` — task templates, provider overlays,
  provider capability configs (see prompts/README.md)
- `backend/` — FastAPI app: API, orchestration engine, provider adapters,
  schemas, XML engine, deterministic validation, storage
- `frontend/` — React shell for the core loop:
  upload → setup → review → approve → rebuild → download
- `backend/tests/fixtures/benchmarks/` — benchmark fixture structure
- `docs/architecture.md` — Stage 1 architecture document

## Providers (managed service model)
SAGE runs as an internal managed service. Standard users never choose or see
a provider — every project runs on the centrally configured one
(`SAGE_PROVIDER`, VAL in production). The architecture stays fully
provider-agnostic underneath: the provider is recorded in project state at
creation for audit/debugging, and is never switched silently.

Per-project provider selection and explicit provider changes (with a
recorded reason) exist only in admin/dev deployments (`SAGE_ADMIN_MODE=1`);
the backend enforces this server-side and the UI only reveals provider
controls when `/api/meta` reports admin mode.

- `val` — clean stub until programmatic access is confirmed
- `claude` — dev/fallback (requires `ANTHROPIC_API_KEY`)
- `mock` — fixture-driven, fully deterministic, used by tests/benchmarks

## Running (development)
Backend:
```
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```
Frontend:
```
cd frontend
npm install
npm run dev
```
Tests:
```
cd backend && pytest
```
