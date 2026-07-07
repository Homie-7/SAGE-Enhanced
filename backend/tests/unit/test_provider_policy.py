"""Managed-service provider rules: standard users never choose providers;
admin/dev mode may; provider is always recorded for audit."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


def make_client(tmp_path, monkeypatch, *, admin: bool, default: str = "mock"):
    monkeypatch.setenv("SAGE_DB_PATH", str(tmp_path / "sage.db"))
    monkeypatch.setenv("SAGE_ARTEFACT_ROOT", str(tmp_path / "artefacts"))
    monkeypatch.setenv("SAGE_PROVIDER", default)
    monkeypatch.setenv("SAGE_ADMIN_MODE", "1" if admin else "0")
    import app.config, app.api.deps, app.main
    importlib.reload(app.config)
    importlib.reload(app.api.deps)
    importlib.reload(app.main)
    return TestClient(app.main.app)


def test_standard_user_gets_default_provider_and_cannot_choose(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch, admin=False)

    r = client.post("/api/projects", json={"name": "Normal"})
    assert r.status_code == 200
    body = r.json()
    # Provider facts are recorded in state but redacted from standard responses.
    assert "provider" not in body["meta"]
    assert "provider_history" not in body["meta"]

    r = client.post("/api/projects", json={"name": "Sneaky", "provider": "claude"})
    assert r.status_code == 403

    pid = body["meta"]["id"]
    r = client.post(f"/api/projects/{pid}/provider",
                    json={"provider": "claude", "reason": "trying it"})
    assert r.status_code == 403

    meta = client.get("/api/meta").json()
    assert meta == {"admin_mode": False}  # reveals nothing about providers


def test_admin_mode_can_choose_and_change_with_recorded_reason(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch, admin=True)

    r = client.post("/api/projects", json={"name": "Dev", "provider": "claude"})
    assert r.status_code == 200
    pid = r.json()["meta"]["id"]
    assert r.json()["meta"]["provider"] == "claude"

    r = client.post(f"/api/projects/{pid}/provider",
                    json={"provider": "mock", "reason": "claude endpoint down"})
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["provider"] == "mock"
    last = body["meta"]["provider_history"][-1]
    assert last["reason"] == "claude endpoint down" and last["previous"] == "claude"

    meta = client.get("/api/meta").json()
    assert meta["admin_mode"] is True
    assert set(meta["available_providers"]) == {"claude", "mock", "val"}


def test_provider_change_requires_reason(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch, admin=True)
    pid = client.post("/api/projects", json={"name": "P"}).json()["meta"]["id"]
    r = client.post(f"/api/projects/{pid}/provider", json={"provider": "claude"})
    assert r.status_code == 422  # reason is mandatory — no silent switching
