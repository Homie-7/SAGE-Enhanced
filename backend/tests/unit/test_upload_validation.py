"""Upload content validation: the right file in the wrong field is caught
immediately, with a message that says where it belongs; word-timed JSON
transcripts are normalized to SAGE text at ingest."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[2]
BENCH = BACKEND / "tests" / "fixtures" / "benchmarks" / "teacher_success_story"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAGE_DB_PATH", str(tmp_path / "sage.db"))
    monkeypatch.setenv("SAGE_ARTEFACT_ROOT", str(tmp_path / "artefacts"))
    monkeypatch.setenv("SAGE_PROVIDER", "mock")
    import app.config, app.api.deps, app.main
    importlib.reload(app.config)
    importlib.reload(app.api.deps)
    importlib.reload(app.main)
    c = TestClient(app.main.app)
    r = c.post("/api/projects", json={"name": "Upload validation"})
    c.pid = r.json()["meta"]["id"]
    return c


def post(client, kind, name, content, ctype="application/octet-stream"):
    return client.post(f"/api/projects/{client.pid}/uploads?kind={kind}",
                       files={"file": (name, content, ctype)})


def test_xml_field_rejects_plain_text(client):
    r = post(client, "xml", "transcript.txt", b"[00:00:01] SARAH: Hello.")
    assert r.status_code == 422
    assert "not readable as XML" in r.json()["detail"]


def test_xml_field_rejects_non_xmeml_xml(client):
    r = post(client, "xml", "data.xml", b"<project><name>x</name></project>")
    assert r.status_code == 422
    assert "expected <xmeml>" in r.json()["detail"]


def test_xml_field_accepts_real_sequence(client):
    r = post(client, "xml", "source.xml",
             (BENCH / "inputs" / "source.xml").read_bytes())
    assert r.status_code == 200


def test_transcript_field_rejects_sequence_xml_and_redirects(client):
    r = post(client, "transcript", "source.xml",
             (BENCH / "inputs" / "source.xml").read_bytes())
    assert r.status_code == 422
    assert "Sequence XML field" in r.json()["detail"]


def test_transcript_accepts_plain_timecoded_text(client):
    r = post(client, "transcript", "t.txt",
             (BENCH / "inputs" / "transcript.txt").read_bytes())
    assert r.status_code == 200
    entry = next(f for f in r.json()["inputs"] if f["kind"] == "transcript")
    assert entry["ingest_note"] is None


def test_transcript_normalizes_word_timed_json(client):
    payload = {
        "language": "en",
        "speakers": [{"id": "s1", "name": "Ada"}],
        "segments": [{"start": 1.0, "duration": 1.5, "speaker": "s1", "words": [
            {"type": "word", "text": "Hello", "start": 1.0, "duration": 0.4},
            {"type": "word", "text": "there", "start": 1.5, "duration": 0.4},
        ]}],
    }
    r = post(client, "transcript", "t.json", json.dumps(payload).encode())
    assert r.status_code == 200
    entry = next(f for f in r.json()["inputs"] if f["kind"] == "transcript")
    assert "Converted from word-timed JSON" in entry["ingest_note"]


def test_transcript_rejects_unknown_json_dialect(client):
    r = post(client, "transcript", "t.json", b'{"utterances": []}')
    assert r.status_code == 422
    assert "not a recognised transcript format" in r.json()["detail"]


def test_transcript_rejects_binary(client):
    r = post(client, "transcript", "t.bin", b"\xff\xfe\x00\x01binary")
    assert r.status_code == 422
    assert "UTF-8" in r.json()["detail"]
