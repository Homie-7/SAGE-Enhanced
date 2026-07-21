"""Project creation and retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import config
from app.api.serializers import project_out, projects_out
from app.api.deps import get_artefacts, get_registry, get_store
from app.schemas.state import Project, ProjectMeta

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    provider: str | None = None  # defaults to config.DEFAULT_PROVIDER


@router.post("", response_model=None)
async def create_project(req: CreateProjectRequest, store=Depends(get_store), registry=Depends(get_registry)):
    """Standard users always get the centrally configured provider (VAL in
    production). Choosing a provider per project is an admin/dev capability."""
    if req.provider and req.provider != config.DEFAULT_PROVIDER and not config.ADMIN_MODE:
        raise HTTPException(
            403, "Provider selection is managed centrally. "
                 "Set SAGE_ADMIN_MODE=1 for admin/dev deployments.")
    provider = req.provider or config.DEFAULT_PROVIDER
    if provider not in registry.available():
        raise HTTPException(422, f"Unknown provider '{provider}'. Available: {registry.available()}")
    project = Project(meta=ProjectMeta(name=req.name, provider=provider))
    project.meta.provider_history.append({"provider": provider, "reason": "project_created"})
    return project_out(await store.create(project))


@router.get("", response_model=None)
async def list_projects(store=Depends(get_store)):
    return projects_out(await store.list_projects())


@router.get("/{project_id}", response_model=None)
async def get_project(project_id: str, store=Depends(get_store)):
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    return project_out(project)


@router.delete("/{project_id}", status_code=204, response_model=None)
async def delete_project(project_id: str, store=Depends(get_store),
                         artefacts=Depends(get_artefacts)):
    """Delete a project's record and its uploaded/rebuilt files, at any
    phase — including mid-analysis. Safe against a still-running background
    planning task because that task checks (after every task it saves) that
    the project still exists at all; if not, it stops rather than
    resurrecting the row via its next save (see
    OrchestrationEngine._superseded)."""
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    await store.delete(project_id)
    await artefacts.delete_project(project_id)


class ChangeProviderRequest(BaseModel):
    provider: str
    reason: str  # explicit, recorded — no silent switching


@router.post("/{project_id}/provider", response_model=None)
async def change_provider(project_id: str, req: ChangeProviderRequest,
                          store=Depends(get_store), registry=Depends(get_registry)):
    """Explicit provider change (admin/dev only). Recorded in
    provider_history; never done automatically by the system."""
    if not config.ADMIN_MODE:
        raise HTTPException(
            403, "Provider changes are an admin/dev operation. "
                 "Set SAGE_ADMIN_MODE=1 for admin/dev deployments.")
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    if req.provider not in registry.available():
        raise HTTPException(422, f"Unknown provider '{req.provider}'.")
    project.meta.provider_history.append(
        {"provider": req.provider, "reason": req.reason, "previous": project.meta.provider}
    )
    project.meta.provider = req.provider
    return project_out(await store.save(project))
