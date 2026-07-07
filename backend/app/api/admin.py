"""Operator endpoints — admin/dev deployments only.

Standard deployments return 403 and reveal nothing. These endpoints answer
the operator questions that matter before a live run: is the default
provider actually able to run a task, is state writable, are the canonical
prompt files present?
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app import config
from app.api.deps import get_registry

router = APIRouter(prefix="/api/admin", tags=["admin"])

_CANONICAL_FILES = 6  # SAGE V3.2 Efficient: files 00–05


def _require_admin() -> None:
    if not config.ADMIN_MODE:
        raise HTTPException(403, "Admin endpoints require an admin/dev deployment.")


@router.get("/status")
async def status():
    _require_admin()
    registry = get_registry()

    providers = {}
    for name in registry.available():
        try:
            adapter = registry.get(name)
            ready, detail = adapter.readiness()
        except Exception as exc:  # config load failures are operator facts too
            ready, detail = False, f"adapter failed to initialise: {exc}"
        providers[name] = {
            "ready": ready,
            "detail": detail,
            "is_default": name == config.DEFAULT_PROVIDER,
        }

    db_dir = Path(config.DB_PATH).parent
    try:
        db_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=db_dir):
            pass
        db_writable = True
        db_detail = str(config.DB_PATH)
    except OSError as exc:
        db_writable, db_detail = False, f"{config.DB_PATH}: {exc}"

    canonical_dir = Path(config.PROMPTS_ROOT) / "canonical"
    canonical_present = (canonical_dir.is_dir()
                         and len(list(canonical_dir.glob("*.md"))) >= _CANONICAL_FILES)

    artefact_root = Path(config.ARTEFACT_ROOT)
    try:
        artefact_root.mkdir(parents=True, exist_ok=True)
        artefacts_writable = os.access(artefact_root, os.W_OK)
    except OSError:
        artefacts_writable = False

    default_ready = providers.get(config.DEFAULT_PROVIDER, {}).get("ready", False)
    ok = default_ready and db_writable and canonical_present and artefacts_writable
    return {
        "ok": ok,
        "default_provider": config.DEFAULT_PROVIDER,
        "providers": providers,
        "database": {"writable": db_writable, "detail": db_detail},
        "artefacts": {"writable": artefacts_writable, "path": str(artefact_root)},
        "canonical_prompts": {"present": canonical_present, "path": str(canonical_dir)},
    }
