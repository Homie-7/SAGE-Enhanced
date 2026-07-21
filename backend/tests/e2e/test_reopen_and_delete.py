"""Reopening setup and deleting projects — including the safety mechanism
that stops a still-running background analysis from clobbering state that
moved on underneath it (via a reopen or a delete) instead of resurrecting or
overwriting it. See OrchestrationEngine._superseded / reopen_setup."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.orchestration.engine import OrchestrationEngine
from app.providers.registry import ProviderRegistry
from app.schemas.state import InputFile, Project, ProjectMeta, ProjectPhase
from app.storage.sqlite_store import DiskArtefactStore

BACKEND = Path(__file__).resolve().parents[2]
BENCH = BACKEND / "tests" / "fixtures" / "benchmarks" / "teacher_success_story"


# --- HTTP-level: reopen / delete as a user would trigger them -----------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAGE_DB_PATH", str(tmp_path / "sage.db"))
    monkeypatch.setenv("SAGE_ARTEFACT_ROOT", str(tmp_path / "artefacts"))
    monkeypatch.setenv("SAGE_MOCK_FIXTURES", str(BENCH / "expected" / "mock_tasks"))
    monkeypatch.setenv("SAGE_PROVIDER", "mock")
    import app.config, app.api.deps, app.main
    importlib.reload(app.config)
    importlib.reload(app.api.deps)
    importlib.reload(app.main)
    return TestClient(app.main.app)


def _upload_and_setup(client, name="t"):
    r = client.post("/api/projects", json={"name": name})
    pid = r.json()["meta"]["id"]
    with open(BENCH / "inputs" / "source.xml", "rb") as f:
        r = client.post(f"/api/projects/{pid}/uploads", params={"kind": "xml"},
                        files={"file": ("source.xml", f, "application/xml")})
    xml_stored_path = r.json()["inputs"][-1]["stored_path"]
    with open(BENCH / "inputs" / "transcript.txt", "rb") as f:
        client.post(f"/api/projects/{pid}/uploads", params={"kind": "transcript"},
                    files={"file": ("transcript.txt", f, "text/plain")})
    r = client.post(f"/api/projects/{pid}/setup", json={})
    assert r.status_code == 200
    return pid, xml_stored_path


def test_reopen_setup_preserves_inputs_and_answers_then_replans(client):
    # Note: with the mock provider, /analyse runs the whole background
    # pipeline synchronously before the HTTP call returns, so by the time we
    # could check, the project is already past "analysing" into
    # paper_edit_ready — beyond reopen's scope by design (Setup + Processing
    # only, not Review onward). This test therefore reopens from
    # setup_complete instead, which is itself a new, real capability: you
    # previously could not resubmit /setup once past inputs_uploaded at all.
    # The mid-analysis case (the harder one) is verified directly against
    # the engine below, where the exact save-by-save timing can be forced.
    pid, _ = _upload_and_setup(client)

    r = client.post(f"/api/projects/{pid}/reopen-setup")
    assert r.status_code == 200, r.text
    reopened = r.json()
    assert reopened["meta"]["phase"] == "inputs_uploaded"
    assert reopened["paper_edit"] is None
    assert reopened["roster"] == []
    assert reopened["ledger"]["entries"] == []
    # Setup answers and uploaded inputs survive reopening.
    assert len(reopened["inputs"]) == 2
    assert reopened["setup"]["cut_style"]["value"] == "natural"

    # A full round trip through planning still works — reopening isn't a
    # dead end.
    r = client.post(f"/api/projects/{pid}/setup", json={})
    assert r.status_code == 200 and r.json()["meta"]["phase"] == "setup_complete"
    r = client.post(f"/api/projects/{pid}/analyse")
    assert r.status_code == 200
    project = client.get(f"/api/projects/{pid}").json()
    assert project["meta"]["phase"] == "paper_edit_ready"
    assert len(project["paper_edit"]["beats"]) == 8


def test_reopen_setup_refused_after_approval(client):
    pid, _ = _upload_and_setup(client)
    client.post(f"/api/projects/{pid}/analyse")
    client.post(f"/api/projects/{pid}/beats/status", json={"bid": "B1", "status": "locked"})
    r = client.post(f"/api/projects/{pid}/approve",
                    json={"approved_by": "editor@rmit", "accepted_risks": []})
    assert r.json()["meta"]["phase"] == "approved"

    r = client.post(f"/api/projects/{pid}/reopen-setup")
    assert r.status_code == 409


def test_reopen_setup_unknown_project_404(client):
    r = client.post("/api/projects/doesnotexist/reopen-setup")
    assert r.status_code == 404


def test_delete_project_removes_record_and_artefacts(client):
    # Uses the server's own reported stored_path rather than reconstructing
    # it from tmp_path: dependency singletons (get_store/get_artefacts) are
    # bound once at first import across this test session's reload dance,
    # so tmp_path from *this* test's fixture isn't guaranteed to match
    # what's actually in effect if another e2e test ran first. That's a
    # test-fixture quirk, not a server bug — trusting the API's own answer
    # sidesteps it entirely.
    pid, xml_stored_path = _upload_and_setup(client)
    artefact_dir = Path(xml_stored_path).parent
    assert artefact_dir.is_dir()

    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204

    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert not artefact_dir.exists()


def test_delete_unknown_project_404(client):
    r = client.delete("/api/projects/doesnotexist")
    assert r.status_code == 404


# --- the supersession mechanism itself, at the engine level -------------------
#
# The background run_planning loop saves after every one of the 6 planning
# tasks. If setup is reopened (generation bumped) or the project deleted
# (row gone) mid-loop, it must stop instead of continuing to save a stale
# in-memory object over the top of the fresher state. Testing this through
# real concurrent HTTP requests would be timing-dependent and flaky; instead
# this drives the engine directly against a store stub that deterministically
# reports "superseded" after a chosen number of saves, so the exact stopping
# point is asserted rather than hoped for.

class _SupersedeAfterNSaves:
    """Records every save; once `threshold` saves have happened, .get()
    reports the project as superseded — either reopened (bumped
    run_generation) or deleted (None), depending on `mode`."""

    def __init__(self, threshold: int, mode: str):
        assert mode in ("reopen", "delete")
        self._threshold = threshold
        self._mode = mode
        self.saves: list[Project] = []

    async def save(self, project: Project) -> Project:
        self.saves.append(project.model_copy(deep=True))
        return project

    async def get(self, project_id: str):
        if not self.saves:
            return None
        if len(self.saves) >= self._threshold:
            if self._mode == "delete":
                return None
            fresh = self.saves[-1].model_copy(deep=True)
            fresh.meta.run_generation += 1
            return fresh
        return self.saves[-1].model_copy(deep=True)


async def _project_with_real_inputs(tmp_path) -> tuple[Project, DiskArtefactStore]:
    artefacts = DiskArtefactStore(tmp_path / "artefacts")
    project = Project(meta=ProjectMeta(name="supersede-test", provider="mock"))
    project.meta.phase = ProjectPhase.SETUP_COMPLETE
    for kind, filename in (("xml", "source.xml"), ("transcript", "transcript.txt")):
        data = (BENCH / "inputs" / filename).read_bytes()
        stored_path = await artefacts.write(project.meta.id, f"{kind}_{filename}", data)
        project.inputs.append(InputFile(
            kind=kind, filename=filename, stored_path=stored_path,
            checksum_sha256="test",
        ))
    return project, artefacts


def _registry() -> ProviderRegistry:
    return ProviderRegistry(
        configs_dir=config.PROVIDER_CONFIGS,
        mock_fixture_dir=str(BENCH / "expected" / "mock_tasks"),
    )


async def test_run_planning_stops_immediately_when_reopened_before_any_task(tmp_path):
    project, artefacts = await _project_with_real_inputs(tmp_path)
    store = _SupersedeAfterNSaves(threshold=1, mode="reopen")
    engine = OrchestrationEngine(store, _registry(), artefacts=artefacts,
                                 prompts_root=config.PROMPTS_ROOT)

    await engine.run_planning(project)

    # Save #1 is the transition to ANALYSING itself; save #2 is the
    # source-audit save, where the first supersession check happens and
    # (threshold=1) immediately detects it. None of the 6 planning tasks
    # ran (a full run saves 1 + 1 + 6 + 1-on-final-transition = 9).
    assert len(store.saves) == 2


async def test_run_planning_stops_partway_when_reopened_mid_loop(tmp_path):
    project, artefacts = await _project_with_real_inputs(tmp_path)
    # threshold=3: superseded is first reported once 3 saves exist — i.e.
    # right after the first planning task's save (transition + source-audit
    # + 1 task = 3).
    store = _SupersedeAfterNSaves(threshold=3, mode="reopen")
    engine = OrchestrationEngine(store, _registry(), artefacts=artefacts,
                                 prompts_root=config.PROMPTS_ROOT)

    await engine.run_planning(project)

    assert len(store.saves) == 3
    # It never reached the final transition save (would make this 4+).
    assert store.saves[-1].meta.phase == ProjectPhase.ANALYSING


async def test_run_planning_stops_when_deleted_mid_loop(tmp_path):
    project, artefacts = await _project_with_real_inputs(tmp_path)
    store = _SupersedeAfterNSaves(threshold=2, mode="delete")
    engine = OrchestrationEngine(store, _registry(), artefacts=artefacts,
                                 prompts_root=config.PROMPTS_ROOT)

    await engine.run_planning(project)

    assert len(store.saves) == 2


async def test_run_planning_completes_normally_when_never_superseded(tmp_path):
    project, artefacts = await _project_with_real_inputs(tmp_path)
    # threshold higher than any real save count this run will reach.
    store = _SupersedeAfterNSaves(threshold=999, mode="reopen")
    engine = OrchestrationEngine(store, _registry(), artefacts=artefacts,
                                 prompts_root=config.PROMPTS_ROOT)

    result = await engine.run_planning(project)

    assert result.meta.phase == ProjectPhase.PAPER_EDIT_READY
    assert len(result.paper_edit.beats) == 8
    # 1 transition-to-analysing + 1 source-audit + 6 tasks + 1 final transition.
    assert len(store.saves) == 9
