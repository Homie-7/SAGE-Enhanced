# SAGE Internal V1 — Handover Brief

Written 2026-07-21 for a colleague joining the project, and for that
colleague's AI assistant to read as onboarding context. If you're an AI
assistant reading this: treat the "Non-negotiables" section as hard
constraints, not suggestions — they've been repeated and enforced across
this project's entire history for specific reasons explained below.

---

## 1. What SAGE is

**Story Assembly and Guidance Engine** — a human-led, AI-assisted editorial
workflow for educational video production, built for internal use at RMIT
University. It takes a synced timeline (Premiere FCP7 XML export) and a
transcript, runs an LLM-driven editorial planning pipeline, presents the
result as a "paper edit" for human review and approval, and only then
produces a rebuilt XML the editor re-imports into Premiere.

**It does not replace the editor.** The core design principle, enforced in
code (not just prompts):
- human approval is a server-side gate before any rebuild happens
- locked beats stay locked; rejected beats stay rejected (deterministic diff, not re-planned)
- revisions are targeted deltas, never full replans
- uncertainty is surfaced explicitly; failures are honest, never silently swallowed
- deterministic validation runs alongside LLM reasoning — the LLM plans the cut, deterministic code builds the actual XML

## 2. Architecture at a glance

- `prompts/canonical/` — SAGE V3.2 editorial logic, **verbatim source of
  truth**. Never paraphrased, never edited per-provider.
- `prompts/{tasks,overlays,configs}/` — task templates reference canonical
  sections (don't restate them); overlays are tiny per-provider formatting
  deltas; configs are provider capability JSON (limits, chunking strategy).
- `backend/` — FastAPI app: orchestration engine, provider adapters, XML
  parser/rebuilder, deterministic validation suite, SQLite-backed project
  store.
- `frontend/` — React (Vite, `BrowserRouter`) shell for the core loop:
  upload → setup → review → approve → rebuild → download.
- `backend/tests/` — 49 tests, all passing as of the last commit on the
  deployment branch (unit + HTTP-level via FastAPI TestClient).

### Providers (important design point)
Three provider adapters exist behind one interface (`backend/app/providers/`):
- **`val`** — the real target: RMIT's internal multi-model gateway (can
  route to Opus, GPT, and other models depending on config). **Not yet
  live** — transport is fully implemented and tested against a fake
  gateway, but no real `VAL_API_KEY`/gateway URL has been supplied yet, so
  no live SAGE run has happened against real VAL infrastructure.
- **`claude`** — fallback/dev-only, never the production default.
- **`mock`** — fixture-driven, zero-cost, fully deterministic; used by the
  test suite and benchmark fixtures, not shipped in the deployment image.

## 3. Non-negotiables (repeat these back before changing anything nearby)

These were stated explicitly and repeatedly by the project owner across
every session touching this codebase. Do not soften or reinterpret them:

- SAGE is a **managed-service internal app** — standard users never see or
  choose a provider.
- **VAL is the only production default.** Claude exists purely as a
  fallback/test path.
- Provider selection (which model runs a project, or switching mid-project)
  is **admin/dev-only**, gated server-side by `SAGE_ADMIN_MODE`, never
  exposed to standard users regardless of deployment.
- The canonical prompt files remain the sole source of editorial logic —
  no duplicating or paraphrasing SAGE's brain elsewhere.
- **No new product features, no workflow redesign, no faked multi-source
  support** — several rounds of deployment work explicitly excluded scope
  creep even when it would have been easy to bundle in.
- **No BYOK** — this is not a product where end users supply their own API
  keys. Ever.
- **Secrets never touch the frontend, the repo, logs, or any client-visible
  config.** `VAL_API_KEY` is a server-side env var / secret-manager entry
  only, full stop.

## 4. Current state: deployment work (the most recent focus)

All deployment work lives on branch **`deploy/staging-vercel-railway`**
(name is now slightly stale — it started as a Railway+Vercel split, see
history below — but nobody's renamed it). **A PR against `main` is open
and deliberately not merged yet**, pending the project owner's review.

### What's actually been built and verified
- A single root `Dockerfile` (multi-stage: builds the Vite frontend, then
  bakes the built assets into the FastAPI backend image). One container
  serves both the API and the app itself from one origin — no CORS
  wiring needed, no second hosting platform required.
- `backend/app/main.py` serves the built frontend with an SPA fallback
  route, only when `SAGE_STATIC_ROOT` is set (inert in local dev/tests).
- **A path-traversal vulnerability in that SPA fallback route was found
  (by an automated security review) and fixed** — the handler now
  resolves and containment-checks candidate paths before serving them.
  Verified against both raw and percent-encoded traversal attempts.
- VAL's gateway facts (`base_url`/`api_style`/`model`) are overridable via
  env vars (`VAL_BASE_URL`, `VAL_API_STYLE`, `VAL_MODEL`) on top of the
  checked-in `prompts/configs/val.json`, so pointing a deployment at a
  specific VAL model needs no code change.
- Everything above was verified locally end-to-end, including a
  non-editable pip install (matching exactly how the Docker image installs
  the backend) with only the Dockerfile's baked-in env vars set: health
  check, static asset serving, SPA routing, and a real SQLite write via
  project creation all confirmed working.

### VAL is now live — confirmed working
A colleague's PR (`feature/val-provider-wiring`, merged to `main`) wired
`prompts/configs/val.json` to the real RMIT NPE gateway
(`https://val-npe.rmit.edu.au/api`, `openai_chat`, model `gpt-5.6-sol`) —
no secrets committed, just config, exactly as designed. That work has been
merged into the deployment branch. **A real live call against the actual
VAL gateway has since been run and confirmed working** (valid JSON
response, real token usage reported) — this is the first live VAL
round-trip on this project, and the Stage 7 blocker ("VAL not yet
programmatically confirmed") is resolved.

### Hosting decision history (useful context, not indecision)
The hosting approach went through three iterations before landing on the
current one: an initial two-platform split (separate backend/frontend
hosts), then one combined service to remove the cross-platform wiring
entirely, then a final pivot to **Google Cloud Run** once a
Google-native option was requested — the existing Dockerfile needed
*zero changes* to work there (it already listens on `$PORT`), which is
why Cloud Run was chosen over Firebase App Hosting (App Hosting is
framework/buildpack-oriented — Next.js/Angular — and has no clean "just
build my Dockerfile" path).

The Railway path (`docs/deployment-staging.md`) still works unchanged if
anyone ever prefers it — same Dockerfile either way.

### Outstanding manual steps (nobody has confirmed these are done yet)
Full instructions: **`docs/deployment-cloud-run.md`**. Summary:
1. Google Cloud Console → Cloud Run → Create Service → continuously deploy
   from the GitHub repo/branch above, build type Dockerfile.
2. Set env vars: `SAGE_PROVIDER=val`, `SAGE_ADMIN_MODE=0`.
3. Add `VAL_API_KEY` as a **Secret Manager secret**, not a plain variable.
   (`VAL_BASE_URL`/`VAL_API_STYLE`/`VAL_MODEL` no longer need setting —
   the checked-in config already points at the real gateway.)
4. Deploy, then verify by creating one real test project through Upload →
   Setup → Plan (exercises VAL for real, not just a readiness check).

**As of this writing, I have no confirmation that these console steps
have actually been carried out** — treat "is staging actually live" as an
open question to verify with the project owner, not an assumption. VAL
itself is confirmed working (see above); what's unconfirmed is only
whether it's been deployed to Cloud Run yet.

### Known limitations, stated plainly (not hidden)
- **Cloud Run's local disk is ephemeral.** SQLite DB + uploaded/rebuilt
  files live at `/tmp` inside the container by default — wiped on
  scale-to-zero, redeploys, or platform-initiated instance recycling. Fine
  for a short internal review session; not durable storage. Fixing this
  properly (Cloud Storage bucket, or moving off SQLite) is a real
  architecture change and was deliberately **not** done — out of scope
  unless asked for.
- VAL's exact gateway shape (OpenAI-style vs. Anthropic-style endpoint,
  real base URL, real model id) is still unknown to this codebase —
  they're placeholders. The adapter fails with a precise, specific message
  if any of these are wrong, rather than silently misbehaving.
- The `mock` provider (used by the test suite) isn't in the deployment
  image — its fixtures live under `backend/tests/`, deliberately not
  shipped, to keep the image small. Doesn't affect VAL/standard use.
- `SAGE_ADMIN_MODE` should default to `0` on staging, matching production.
  It is **not** required to test VAL — every project already runs on the
  configured default provider regardless of this flag. It only gates a
  diagnostic status endpoint and manual provider-switching.

## 5. Suggested next steps for whoever picks this up

- Confirm whether Cloud Run staging has actually been deployed, and if so,
  whether a real end-to-end project run (through rebuild/download) has
  succeeded against real VAL — this hasn't happened yet as far as this
  document's author knows.
- Get real VAL gateway facts (`base_url`, `api_style`, `model` id) from
  whoever administers RMIT's VAL access, since those are still placeholders.
- If staging needs to outlive casual review sessions, revisit the
  ephemeral-storage limitation deliberately (Cloud Storage bucket mount,
  or a real database) rather than assuming Cloud Run's default disk is fine.
- Everything else (core editorial loop, UI, validation suite) has been
  stable since Stage 8.1 — see `docs/checkpoints/` for the detailed history
  of what was built and verified at each stage, if deeper archaeology is
  needed.
