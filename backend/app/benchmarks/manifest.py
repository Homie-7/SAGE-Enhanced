"""Benchmark case manifest.

A *case* is one real editorial project used as a benchmark: the material a
human editor started from (before), what they delivered (after), and the
transcript. Cases are general-purpose — `content_stream` is a free tag, not
an enum; nothing in the framework may branch on a specific stream name.

Cases live in backend/benchmarks/cases/<case_id>/ and are consumed by
scripts/benchmark_case.py for profiling, feasibility, preparation, and
comparison. They are deliberately separate from tests/fixtures/benchmarks/
(the mock-provider regression fixtures), and may link to one.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class CaseSource(BaseModel):
    """One 'before' timeline plus its transcript, if any."""
    source_id: str                       # case-local, e.g. "main", "electrotech"
    before_xml: str                      # path relative to the case directory
    transcript_json: str | None = None   # raw transcript as delivered
    label: str | None = None


class CaseManifest(BaseModel):
    case_id: str
    title: str
    content_stream: str | None = None    # free tag ("TSS", "LND", anything)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    sources: list[CaseSource]
    reference_after_xml: str | None = None   # the human final edit
    notes: str | None = None
    # Optional link to a mock-provider regression fixture directory
    # (tests/fixtures/benchmarks/...), if one mirrors this case.
    mock_fixture_dir: str | None = None
    # Facts recorded at ingest that affect interpretation, e.g. transcript
    # alignment problems. Free-form but persisted — honesty lives here.
    caveats: list[str] = Field(default_factory=list)

    def path(self, root: Path, rel: str) -> Path:
        return root / rel

    @classmethod
    def load(cls, case_dir: Path) -> "CaseManifest":
        return cls.model_validate(
            json.loads((case_dir / "case.json").read_text()))

    def save(self, case_dir: Path) -> None:
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "case.json").write_text(
            self.model_dump_json(indent=2) + "\n")


def cases_root(backend_dir: Path | None = None) -> Path:
    base = backend_dir or Path(__file__).resolve().parents[2]
    return base / "benchmarks" / "cases"


def list_cases(root: Path | None = None) -> list[CaseManifest]:
    r = root or cases_root()
    if not r.is_dir():
        return []
    out = []
    for d in sorted(r.iterdir()):
        if (d / "case.json").is_file():
            out.append(CaseManifest.load(d))
    return out
