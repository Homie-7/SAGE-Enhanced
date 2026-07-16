"""SAGE Internal V1 — FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import admin, outputs, phases, projects, review, uploads

app = FastAPI(
    title="SAGE Internal V1",
    description=(
        "Story Assembly and Guidance Engine — human-led, AI-assisted "
        "editorial workflow. Internal RMIT deployment."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router_module in (projects, uploads, phases, review, outputs, admin):
    app.include_router(router_module.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sage-internal", "version": "0.1.0"}


@app.get("/api/meta")
async def meta():
    """Deployment facts the UI is allowed to know. Standard mode deliberately
    reveals nothing about providers — that's a managed backend concern."""
    from app import config

    body: dict = {"admin_mode": config.ADMIN_MODE}
    if config.ADMIN_MODE:
        from app.api.deps import get_registry

        body["default_provider"] = config.DEFAULT_PROVIDER
        body["available_providers"] = get_registry().available()
    return body


# Optional single-service mode: if a built frontend is present (baked in by
# the Dockerfile at SAGE_STATIC_ROOT), serve it from this same app/origin —
# the simplest staging deployment, no separate frontend host, no CORS. Absent
# in local dev/tests, where the Vite dev server or test client is used
# instead; this block registers nothing in that case.
if config.STATIC_ROOT and config.STATIC_ROOT.is_dir():
    assets_dir = config.STATIC_ROOT / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """SPA fallback: serve the matching static file if one exists,
        otherwise index.html so client-side routing (BrowserRouter) can
        handle the path. /api/* never reaches here — routers above match
        first."""
        if full_path.startswith("api/"):
            raise HTTPException(404)
        candidate = config.STATIC_ROOT / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(config.STATIC_ROOT / "index.html")
