"""SAGE Internal V1 — FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allow_origins=["http://localhost:5173"],  # Vite dev server
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
