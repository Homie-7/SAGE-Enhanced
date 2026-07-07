"""XML + transcript (+ notes) upload — deterministic ingest."""

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from lxml import etree

from app.benchmarks.transcript import normalize_word_timed

from app.api.serializers import project_out, projects_out
from app.api.deps import get_artefacts, get_engine, get_store
from app.schemas.state import InputFile, Project, ProjectPhase

router = APIRouter(prefix="/api/projects/{project_id}", tags=["uploads"])

_ALLOWED_KINDS = {"xml", "transcript", "notes"}


def _looks_like_xmeml(data: bytes) -> bool:
    try:
        return etree.fromstring(data).tag == "xmeml"
    except etree.XMLSyntaxError:
        return False


def _validate_and_prepare(kind: str, filename: str, data: bytes
                          ) -> tuple[bytes, str | None]:
    """Per-kind content validation. Returns (bytes to store, ingest note) or
    raises 422 with a message that says exactly what went wrong and where the
    file belongs instead."""
    if kind == "xml":
        try:
            root = etree.fromstring(data)
        except etree.XMLSyntaxError as exc:
            raise HTTPException(422, f"'{filename}' is not readable as XML "
                                     f"({exc.msg if hasattr(exc, 'msg') else exc}). "
                                     "Export the sequence from Premiere via "
                                     "File → Export → Final Cut Pro XML.")
        if root.tag != "xmeml":
            raise HTTPException(422, f"'{filename}' is XML but not a Premiere "
                                     f"sequence export (root element is "
                                     f"<{root.tag}>, expected <xmeml>).")
        if root.find(".//sequence") is None:
            raise HTTPException(422, f"'{filename}' contains no <sequence>. "
                                     "Export the sequence itself, not the project bin.")
        return data, None

    if kind == "transcript":
        if _looks_like_xmeml(data):
            raise HTTPException(422, f"'{filename}' is a Premiere sequence "
                                     "XML — upload it in the Sequence XML "
                                     "field. The transcript field takes the "
                                     "text or JSON transcript of the recording.")
        stripped = data.lstrip()
        if stripped.startswith(b"{"):
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError as exc:
                raise HTTPException(422, f"'{filename}' looks like JSON but "
                                         f"does not parse (line {exc.lineno}).")
            if not isinstance(parsed, dict) or "segments" not in parsed:
                raise HTTPException(422, f"'{filename}' is JSON but not a "
                                         "recognised transcript format "
                                         "(expected word-timed segments). "
                                         "Upload the transcript as plain "
                                         "timecoded text instead.")
            try:
                norm = normalize_word_timed(parsed)
            except (KeyError, TypeError, ValueError) as exc:
                raise HTTPException(422, f"'{filename}' is a word-timed "
                                         f"transcript but a segment is "
                                         f"malformed ({exc}).")
            note = (f"Converted from word-timed JSON: {len(norm.words)} words, "
                    f"{norm.named_speaker_count}/{norm.speaker_count} named "
                    "speakers, timecoded text generated.")
            return norm.sage_text.encode("utf-8"), note
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(422, f"'{filename}' is not readable as UTF-8 "
                                     "text. Transcripts must be timecoded "
                                     "text or word-timed JSON.")
        return data, None

    # notes: any UTF-8 text
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(422, f"'{filename}' is not readable as text; "
                                 "notes must be a text file.")
    return data, None


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
    filename = file.filename or kind
    data, ingest_note = _validate_and_prepare(kind, filename, data)
    checksum = hashlib.sha256(data).hexdigest()
    safe_name = f"{kind}_{filename.replace('/', '_')}"
    stored_path = await artefacts.write(project_id, safe_name, data)

    # One file per kind in V1 (single-source): replace, don't accumulate.
    project.inputs = [f for f in project.inputs if f.kind != kind]
    project.inputs.append(InputFile(
        kind=kind, filename=filename,
        stored_path=stored_path, checksum_sha256=checksum,
        ingest_note=ingest_note,
    ))

    kinds = {f.kind for f in project.inputs}
    if project.meta.phase == ProjectPhase.CREATED and {"xml", "transcript"} <= kinds:
        return project_out(await engine.transition(project, ProjectPhase.INPUTS_UPLOADED))
    return project_out(await store.save(project))
