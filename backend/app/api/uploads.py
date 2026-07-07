"""XML + transcript (+ notes) upload — deterministic ingest."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.serializers import project_out, projects_out
from app.api.deps import get_artefacts, get_engine, get_store
from app.schemas.state import InputFile, Project, ProjectPhase

router = APIRouter(prefix="/api/projects/{project_id}", tags=["uploads"])

_ALLOWED_KINDS = {"xml", "transcript", "notes"}


@router.post("/uploads", response_model=None)
async def upload_input(project_id: str, kind: str, file: UploadFile,
                       store=Depends(get_store), artefacts=Depends(get_artefacts),
                       engine=Depends(get_engine)):
    """kind: xml | transcript | notes. Checksums, stores, registers the
    InputFile; transitions to inputs_uploaded once XML + transcript present."""
    if kind not in _ALLOWED_KINDS:
        raise HTTPException(422, f"kind must be one of {sorted(_ALLOWED_KINDS)}.")
    project = await store.get(project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    if project.meta.phase not in (ProjectPhase.CREATED, ProjectPhase.INPUTS_UPLOADED):
        raise HTTPException(
            409, f"Uploads are only accepted before setup (phase is "
                 f"'{project.meta.phase.value}').")

    data = await file.read()
    if not data:
        raise HTTPException(422, "Uploaded file is empty.")
    checksum = hashlib.sha256(data).hexdigest()
    safe_name = f"{kind}_{(file.filename or kind).replace('/', '_')}"
    stored_path = await artefacts.write(project_id, safe_name, data)

    # One file per kind in V1 (single-source): replace, don't accumulate.
    project.inputs = [f for f in project.inputs if f.kind != kind]
    project.inputs.append(InputFile(
        kind=kind, filename=file.filename or safe_name,
        stored_path=stored_path, checksum_sha256=checksum,
    ))

    kinds = {f.kind for f in project.inputs}
    if project.meta.phase == ProjectPhase.CREATED and {"xml", "transcript"} <= kinds:
        return project_out(await engine.transition(project, ProjectPhase.INPUTS_UPLOADED))
    return project_out(await store.save(project))
