"""Review flow: lock/reject beats, request targeted revision, approve."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.serializers import project_out, projects_out
from app.api.deps import get_engine, get_store
from app.orchestration.engine import (
    IllegalTransitionError,
    RevisionRejected,
    TaskFailure,
)
from app.schemas.state import BeatStatus, Project, ProjectPhase

router = APIRouter(prefix="/api/projects/{project_id}", tags=["review"])

_REVIEW_PHASES = {ProjectPhase.PAPER_EDIT_READY, ProjectPhase.IN_REVIEW}
# Human review actions. Reopening (-> candidate) is the explicit action that
# unlocks a locked beat or readmits a rejected one — never done by the LLM.
_ALLOWED_STATUS = {BeatStatus.LOCKED, BeatStatus.REJECTED, BeatStatus.CANDIDATE}


class BeatStatusUpdate(BaseModel):
    bid: str
    status: BeatStatus  # locked | rejected | candidate (reopen)


class RevisionRequest(BaseModel):
    instruction: str
    reopened_bids: list[str] = []


class ApprovalRequest(BaseModel):
    approved_by: str
    accepted_risks: list[str] = []


async def _get_reviewable(project_id: str, store) -> Project:
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    if project.meta.phase not in _REVIEW_PHASES:
        raise HTTPException(
            409, f"Review actions require phase paper_edit_ready/in_review "
                 f"(currently '{project.meta.phase.value}').")
    if project.paper_edit is None:
        raise HTTPException(409, "No paper edit exists yet; run planning first.")
    return project


@router.post("/beats/status", response_model=None)
async def update_beat_status(project_id: str, update: BeatStatusUpdate,
                             store=Depends(get_store), engine=Depends(get_engine)):
    project = await _get_reviewable(project_id, store)
    if update.status not in _ALLOWED_STATUS:
        raise HTTPException(422, "status must be locked, rejected, or candidate.")
    beat = project.paper_edit.beat(update.bid)
    if beat is None:
        raise HTTPException(404, f"Beat '{update.bid}' not found.")
    beat.status = update.status
    project = await engine.ensure_in_review(project)
    return project_out(await store.save(project))


@router.post("/revise", response_model=None)
async def request_revision(project_id: str, req: RevisionRequest,
                           store=Depends(get_store), engine=Depends(get_engine)):
    """Targeted Revision Mode: delta only, lock-enforced deterministically."""
    project = await _get_reviewable(project_id, store)
    if not req.instruction.strip():
        raise HTTPException(422, "Revision instruction is empty.")
    try:
        return project_out(await engine.run_revision(
            project, req.instruction, set(req.reopened_bids)))
    except RevisionRejected as exc:
        raise HTTPException(422, detail={
            "message": "Revision rejected: it violated lock/rejection rules. "
                       "State is unchanged.",
            "blockers": [b.model_dump() for b in exc.report.blockers],
        })
    except TaskFailure as exc:
        raise HTTPException(502, detail={
            "message": "Revision task failed.",
            "blocker": exc.blocker.model_dump(),
        })
    except IllegalTransitionError as exc:
        raise HTTPException(409, str(exc))


@router.post("/approve", response_model=None)
async def approve(project_id: str, req: ApprovalRequest,
                  store=Depends(get_store), engine=Depends(get_engine)):
    """Record approval of the current paper edit version; approved beats
    become locked (canonical rule)."""
    project = await _get_reviewable(project_id, store)
    try:
        return project_out(await engine.approve(project, req.approved_by, req.accepted_risks))
    except TaskFailure as exc:
        raise HTTPException(422, detail=exc.blocker.model_dump())
    except IllegalTransitionError as exc:
        raise HTTPException(409, str(exc))
