"""Phase triggers: quick setup, planning run, rebuild trigger."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.serializers import project_out, projects_out
from app.api.deps import get_engine, get_store
from app.orchestration.engine import ApprovalGateError, IllegalTransitionError
from app.orchestration.ledger import settle_from_setup
from app.schemas.state import (Blocker, CheckOutcome, Project, ProjectPhase,
                               ProjectSetup, ValidationReport)

logger = logging.getLogger("sage.phases")

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
async def run_planning(project_id: str, background: BackgroundTasks,
                       store=Depends(get_store), engine=Depends(get_engine)):
    """Start the canonical planning pipeline (audit → roster → classification
    → grouping → mode/structure → paper edit).

    Runs in the background: live-provider planning can take minutes and must
    not hold the HTTP request open. The response returns immediately; the UI
    polls the project until it leaves setup_complete/analysing. Any failure
    is persisted as phase=failed with explicit blockers — never lost."""
    project = await _get(project_id, store)
    if project.meta.phase != ProjectPhase.SETUP_COMPLETE:
        raise HTTPException(
            409, f"Planning requires phase 'setup_complete' "
                 f"(currently '{project.meta.phase.value}').")

    async def _run() -> None:
        try:
            await engine.run_planning(project)
        except Exception as exc:  # noqa: BLE001 — background failures must be persisted
            logger.exception("Planning failed for project %s", project.meta.id)
            try:
                fresh = await store.get(project.meta.id)
                if fresh is not None and fresh.meta.phase != ProjectPhase.FAILED:
                    fresh.meta.phase = ProjectPhase.FAILED
                    fresh.validation = ValidationReport(
                        checks=[], overall=CheckOutcome.FAIL,
                        blockers=[Blocker(
                            check="planning_crash",
                            why_it_blocks=f"Unexpected error during planning: {exc}",
                            what_is_needed="Check server logs; retry after the "
                                           "cause is fixed (admin).",
                        )])
                    await store.save(fresh)
            except Exception:  # noqa: BLE001
                logger.exception("Could not persist planning failure for %s",
                                 project.meta.id)

    background.add_task(_run)
    return project_out(project)


@router.post("/reopen-setup", response_model=None)
async def reopen_setup(project_id: str, store=Depends(get_store), engine=Depends(get_engine)):
    """Explicit user action: stop treating the current plan (or in-progress
    analysis) as final and go back to Setup. Refused once approved — see
    OrchestrationEngine.reopen_setup for the exact rule and what it clears."""
    project = await _get(project_id, store)
    try:
        return project_out(await engine.reopen_setup(project))
    except ApprovalGateError as exc:
        raise HTTPException(409, str(exc))
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
