"""Application configuration (environment-driven, internal deployment)."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = os.environ.get("SAGE_DB_PATH", str(REPO_ROOT / "backend" / "sage.db"))
ARTEFACT_ROOT = os.environ.get("SAGE_ARTEFACT_ROOT", str(REPO_ROOT / "backend" / "artefacts"))
PROMPTS_ROOT = os.environ.get("SAGE_PROMPTS_ROOT", str(REPO_ROOT / "prompts"))
PROVIDER_CONFIGS = str(Path(PROMPTS_ROOT) / "configs")

# Default provider for NEW projects only. Existing projects always use the
# provider recorded in their own state.
DEFAULT_PROVIDER = os.environ.get("SAGE_PROVIDER", "val")

# Provider selection is a backend/admin/config concern. Standard users always
# get DEFAULT_PROVIDER (centrally hosted VAL in production). Only when the
# deployment runs in admin/dev mode may a provider be chosen per project or
# changed (explicitly, with a recorded reason) mid-project.
ADMIN_MODE = os.environ.get("SAGE_ADMIN_MODE", "0") == "1"

# Fixture directory for the mock provider (task_name.json files). Points at
# the primary benchmark by default so a dev environment runs end-to-end with
# zero LLM cost.
MOCK_FIXTURES = os.environ.get(
    "SAGE_MOCK_FIXTURES",
    str(REPO_ROOT / "backend" / "tests" / "fixtures" / "benchmarks"
        / "teacher_success_story" / "expected" / "mock_tasks"),
)

# Browser origins allowed to call this API (comma-separated). Defaults to the
# Vite dev server only. Only relevant if the frontend is hosted separately
# from this API (cross-origin) — irrelevant, but harmless, in the default
# single-service deployment (see STATIC_ROOT below), since same-origin
# requests never go through CORS at all.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("SAGE_CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# If set and populated, this app serves the built frontend itself from the
# same origin as the API — the simplest staging deployment (one host, one
# domain, no CORS, no separate frontend platform). The Dockerfile builds the
# frontend and sets this env var; unset in local dev, where the Vite dev
# server is used instead.
STATIC_ROOT = Path(os.environ["SAGE_STATIC_ROOT"]) if os.environ.get("SAGE_STATIC_ROOT") else None
