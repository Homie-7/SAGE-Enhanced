"""End-to-end core loop: create → upload → setup → analyse → review →
approve → rebuild → validate → download, driven by the Teacher Success Story
benchmark fixture and the deterministic mock provider.

This is the Stage 3 contract test: if this passes, the core loop works.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from lxml import etree

from app.orchestration.engine import ApprovalGateError, OrchestrationEngine, RevisionRejected
from app.providers.registry import ProviderRegistry
from app.schemas.state import (
    BeatStatus, CheckOutcome, Project, ProjectMeta, ProjectPhase, ProjectSetup,
)
from app.storage.sqlite_store import DiskArtefactStore, SQLiteProjectStore

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
BENCH = BACKEND / "tests" / "fixtures" / "benchmarks" / "teacher_success_story"
MOCK_TASKS = BENCH / "expected" / "mock_tasks"


@pytest.fixture
def env(tmp_path):
    store = SQLiteProjectStore(tmp_path / "sage.db")
    artefacts = DiskArtefactStore(tmp_path / "artefacts")
    registry = ProviderRegistry(
        configs_dir=REPO / "prompts" / "configs",
        mock_fixture_dir=MOCK_TASKS,
    )
    engine = OrchestrationEngine(
        store, registry, artefacts=artefacts, prompts_root=REPO / "prompts",
    )
    return store, artefacts, engine


async def _project_through_upload(store, artefacts, engine) -> Project:
    import hashlib
    project = Project(meta=ProjectMeta(name="Teacher Success Story", provider="mock"))
    await store.create(project)
    for kind, src in (("xml", BENCH / "inputs" / "source.xml"),
                      ("transcript", BENCH / "inputs" / "transcript.txt")):
        data = src.read_bytes()
        path = await artefacts.write(project.meta.id, f"{kind}_{src.name}", data)
        from app.schemas.state import InputFile
        project.inputs.append(InputFile(
            kind=kind, filename=src.name, stored_path=path,
            checksum_sha256=hashlib.sha256(data).hexdigest(),
        ))
    return await engine.transition(project, ProjectPhase.INPUTS_UPLOADED)


async def _project_through_planning(store, artefacts, engine) -> Project:
    project = await _project_through_upload(store, artefacts, engine)
    project.setup = ProjectSetup()
    project = await engine.transition(project, ProjectPhase.SETUP_COMPLETE)
    project = await engine.run_planning(project)
    return project


async def test_full_core_loop(env):
    store, artefacts, engine = env
    project = await _project_through_planning(store, artefacts, engine)

    # Planning landed the paper edit with structured state populated.
    assert project.meta.phase == ProjectPhase.PAPER_EDIT_READY
    assert project.source_audit.frame_rate == 25.0
    assert len(project.roster) == 2
    assert len(project.classification) == 14
    assert project.structure.mode is not None
    assert project.paper_edit is not None and len(project.paper_edit.beats) == 8
    assert all(b.status == BeatStatus.CANDIDATE for b in project.paper_edit.beats)
    assert all(b.exact_quote is None for b in project.paper_edit.beats)  # stub-first

    # Approval gate is hard: rebuild refused before approval.
    with pytest.raises(ApprovalGateError):
        engine.assert_rebuild_allowed(project)

    # Approve → all non-rejected beats lock; exact quotes resolved.
    project = await engine.approve(project, "editor@rmit", accepted_risks=["B4 seam"])
    assert project.meta.phase == ProjectPhase.APPROVED
    assert all(b.status == BeatStatus.LOCKED for b in project.paper_edit.beats)
    assert all(b.exact_quote for b in project.paper_edit.beats)
    transcript = (BENCH / "inputs" / "transcript.txt").read_text()
    for b in project.paper_edit.beats:
        assert b.exact_quote in " ".join(transcript.split())  # verbatim

    # Rebuild + validation + output.
    project = await engine.run_rebuild(project)
    assert project.meta.phase == ProjectPhase.COMPLETE, (
        project.validation and [b.model_dump() for b in project.validation.blockers])
    assert project.validation.overall in (CheckOutcome.PASS, CheckOutcome.WARN)
    assert not project.validation.blockers
    assert project.output is not None

    # Output XML matches the benchmark's structural expectations.
    checks = json.loads((BENCH / "expected" / "output_checks.json").read_text())
    tree = etree.parse(project.output.xml_path)
    seq = tree.getroot().find(".//sequence")
    vclips = seq.findall("media/video/track/clipitem")
    assert len(vclips) == checks["expected_clip_count_video"]
    assert int(seq.findtext("rate/timebase")) == checks["frame_rate"]
    total = int(seq.findtext("duration"))
    assert total / 25 <= checks["max_total_duration_seconds"]
    # Clips are sequential and gap-free on the rebuilt timeline.
    cursor = 0
    for c in vclips:
        assert int(c.findtext("start")) == cursor
        cursor = int(c.findtext("end"))
    # Every video clip has linked audio present in the output.
    aclips = seq.findall("media/audio/track/clipitem")
    assert len(aclips) == len(vclips)


async def test_approval_gate_blocks_rebuild(env):
    store, artefacts, engine = env
    project = await _project_through_planning(store, artefacts, engine)
    with pytest.raises(ApprovalGateError):
        await engine.run_rebuild(project)
    assert project.meta.phase == ProjectPhase.PAPER_EDIT_READY  # untouched


async def test_targeted_revision_legal_delta(env):
    store, artefacts, engine = env
    project = await _project_through_planning(store, artefacts, engine)
    # Lock B1 first; the fixture revision only touches B7 — must pass.
    project.paper_edit.beat("B1").status = BeatStatus.LOCKED
    project = await engine.ensure_in_review(project)
    v_before = project.paper_edit.version
    project = await engine.run_revision(project, "Tighten the reflection beat.")
    assert project.meta.phase == ProjectPhase.IN_REVIEW
    assert project.paper_edit.version == v_before + 1
    assert project.revisions[-1].changed_bids == ["B7"]
    assert project.paper_edit.beat("B1").status == BeatStatus.LOCKED
    assert len(project.paper_edit_history) == 1


async def test_revision_violating_lock_is_rejected(env):
    store, artefacts, engine = env
    project = await _project_through_planning(store, artefacts, engine)
    # Lock B7 — the fixture revision modifies B7, so it must now be rejected.
    project.paper_edit.beat("B7").status = BeatStatus.LOCKED
    project = await engine.ensure_in_review(project)
    v_before = project.paper_edit.version
    with pytest.raises(RevisionRejected) as exc:
        await engine.run_revision(project, "Tighten the reflection beat.")
    assert any("locked" in b.check for b in exc.value.report.blockers)
    fresh = await store.get(project.meta.id)
    assert fresh.paper_edit.version == v_before  # state untouched
    assert fresh.meta.phase == ProjectPhase.IN_REVIEW


async def test_rejected_beat_stays_out_of_rebuild(env):
    store, artefacts, engine = env
    project = await _project_through_planning(store, artefacts, engine)
    # Reject B7; the static rebuild-plan fixture still maps all 8 beats,
    # so plan fidelity must fail the build honestly.
    project.paper_edit.beat("B7").status = BeatStatus.REJECTED
    project = await engine.ensure_in_review(project)
    project = await engine.approve(project, "editor@rmit", [])
    project = await engine.run_rebuild(project)
    assert project.meta.phase == ProjectPhase.FAILED
    assert any("rejected" in b.check for b in project.validation.blockers)
