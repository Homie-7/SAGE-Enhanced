"""Core loop through the HTTP API surface (the exact calls the frontend makes)."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[2]
BENCH = BACKEND / "tests" / "fixtures" / "benchmarks" / "teacher_success_story"


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


def test_api_core_loop(client):
    # 1. create project
    r = client.post("/api/projects", json={"name": "Teacher Success Story"})
    assert r.status_code == 200, r.text
    project = r.json()
    pid = project["meta"]["id"]
    # Managed service: provider identity is redacted from standard responses.
    assert "provider" not in project["meta"]
    assert "provider_history" not in project["meta"]

    # 2. upload XML + transcript
    with open(BENCH / "inputs" / "source.xml", "rb") as f:
        r = client.post(f"/api/projects/{pid}/uploads", params={"kind": "xml"},
                        files={"file": ("source.xml", f, "application/xml")})
    assert r.status_code == 200, r.text
    with open(BENCH / "inputs" / "transcript.txt", "rb") as f:
        r = client.post(f"/api/projects/{pid}/uploads", params={"kind": "transcript"},
                        files={"file": ("transcript.txt", f, "text/plain")})
    assert r.status_code == 200 and r.json()["meta"]["phase"] == "inputs_uploaded"

    # Rebuild before approval must be refused at the API layer too.
    r = client.post(f"/api/projects/{pid}/rebuild")
    assert r.status_code in (403, 409)

    # 3. quick setup (all defaults / infer)
    r = client.post(f"/api/projects/{pid}/setup", json={})
    assert r.status_code == 200 and r.json()["meta"]["phase"] == "setup_complete"

    # 4. run planning — starts in the background; the UI (and this test)
    # polls until the project leaves setup_complete/analysing.
    r = client.post(f"/api/projects/{pid}/analyse")
    assert r.status_code == 200, r.text
    for _ in range(20):
        project = client.get(f"/api/projects/{pid}").json()
        if project["meta"]["phase"] not in ("setup_complete", "analysing"):
            break
    assert project["meta"]["phase"] == "paper_edit_ready", project.get("validation")
    assert len(project["paper_edit"]["beats"]) == 8
    # All 6 planning tasks completed — the real progress signal, not
    # inferred from output fields (which can legitimately be empty).
    assert project["meta"]["planning_progress"] == 6

    # 5/6. review: reject nothing, lock one explicitly, then approve
    r = client.post(f"/api/projects/{pid}/beats/status",
                    json={"bid": "B1", "status": "locked"})
    assert r.status_code == 200 and r.json()["meta"]["phase"] == "in_review"
    r = client.post(f"/api/projects/{pid}/approve",
                    json={"approved_by": "editor@rmit", "accepted_risks": []})
    assert r.status_code == 200 and r.json()["meta"]["phase"] == "approved"

    # 7/8. rebuild + validation
    r = client.post(f"/api/projects/{pid}/rebuild")
    assert r.status_code == 200, r.text
    project = r.json()
    assert project["meta"]["phase"] == "complete"
    r = client.get(f"/api/projects/{pid}/validation")
    assert r.status_code == 200
    assert r.json()["overall"] in ("pass", "warn") and not r.json()["blockers"]

    # 9. download
    r = client.get(f"/api/projects/{pid}/download")
    assert r.status_code == 200
    assert r.content.startswith(b"<?xml")
    assert b"<xmeml" in r.content


def test_download_refused_without_output(client):
    r = client.post("/api/projects", json={"name": "Empty"})
    pid = r.json()["meta"]["id"]
    r = client.get(f"/api/projects/{pid}/download")
    assert r.status_code == 409
