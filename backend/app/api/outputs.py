"""Validation report + output download."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_store
from app.schemas.state import ProjectPhase, ValidationReport

router = APIRouter(prefix="/api/projects/{project_id}", tags=["outputs"])


@router.get("/validation", response_model=ValidationReport)
async def get_validation(project_id: str, store=Depends(get_store)):
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    if project.validation is None:
        raise HTTPException(404, "No validation report yet.")
    return project.validation


@router.get("/download")
async def download_output(project_id: str, store=Depends(get_store)):
    """Streams the validated output XML. Refuses if validation failed —
    failures are explicit, not hidden behind a download."""
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    if project.meta.phase != ProjectPhase.COMPLETE or project.output is None:
        blockers = (
            [b.model_dump() for b in project.validation.blockers]
            if project.validation else []
        )
        raise HTTPException(409, detail={
            "message": "No validated output to download. Validation must pass "
                       "before handoff (canonical rule).",
            "phase": project.meta.phase.value,
            "blockers": blockers,
        })
    path = Path(project.output.xml_path)
    if not path.exists():
        raise HTTPException(500, "Output artefact missing on disk.")
    return FileResponse(
        path, media_type="application/xml",
        filename=f"{project.meta.name.replace(' ', '_')}_sage_rebuild.xml",
    )
