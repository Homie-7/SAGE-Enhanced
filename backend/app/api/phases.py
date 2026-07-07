"""Phase triggers: quick setup, planning run, rebuild trigger."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.serializers import project_out, projects_out
from app.api.deps import get_engine, get_store
from app.orchestration.engine import ApprovalGateError, IllegalTransitionError
from app.orchestration.ledger import settle_from_setup
from app.schemas.state import Project, ProjectPhase, ProjectSetup

router = APIRouter(prefix="/api/projects/{project_id}", tags=["phases"])


async def _get(project_id: str, store) -> Project:
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    return project


@router.post("/setup", response_model=None)
async def submit_setup(project_id: str, setup: ProjectSetup,
                       store=Depends(get_store), engine=Depends(get_engine)):
    """Quick-setup answers (any subset; the rest is inferred)."""
    project = await _get(project_id, store)
    if project.meta.phase != ProjectPhase.INPUTS_UPLOADED:
        raise HTTPException(
            409, f"Setup requires phase 'inputs_uploaded' "
                 f"(currently '{project.meta.phase.value}').")
    project.setup = setup
    settle_from_setup(project)
    return project_out(await engine.transition(project, ProjectPhase.SETUP_COMPLETE))


@router.post("/analyse", response_model=None)
async def run_planning(project_id: str, store=Depends(get_store), engine=Depends(get_engine)):
    """Run the canonical planning pipeline (audit → roster → classification
    → grouping → mode/structure → paper edit)."""
    project = await _get(project_id, store)
    try:
        return project_out(await engine.run_planning(project))
    except IllegalTransitionError as exc:
        raise HTTPException(409, str(exc))


@router.post("/rebuild", response_model=None)
async def trigger_rebuild(project_id: str, store=Depends(get_store), engine=Depends(get_engine)):
    """Rebuild. The engine's approval gate hard-fails unless the project is
    approved (assert_rebuild_allowed)."""
    project = await _get(project_id, store)
    try:
        return project_out(await engine.run_rebuild(project))
    except ApprovalGateError as exc:
        raise HTTPException(403, str(exc))
    except IllegalTransitionError as exc:
        raise HTTPException(409, str(exc))
