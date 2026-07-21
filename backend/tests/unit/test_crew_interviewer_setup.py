"""crew_interviewer setup field: defaults to today's standing behaviour
(exclude crew/interviewer voices), with an explicit opt-out ("consider"),
following the same infer-by-default pattern as every other setup field."""

from __future__ import annotations

from app.orchestration.tasks.pipeline import ctx_contributor_roster
from app.schemas.state import Project, ProjectMeta, SetupField


def _project() -> Project:
    return Project(meta=ProjectMeta(name="t", provider="mock"))


def test_default_is_exclude():
    p = _project()
    assert p.setup.crew_interviewer.value == "exclude"
    assert p.setup.crew_interviewer.origin == "default"


def test_context_carries_default_exclude():
    ctx = ctx_contributor_roster(_project(), "transcript text")
    assert ctx["crew_interviewer_handling"] == "exclude"


def test_context_carries_explicit_consider_override():
    p = _project()
    p.setup.crew_interviewer = SetupField(value="consider", origin="user")
    ctx = ctx_contributor_roster(p, "transcript text")
    assert ctx["crew_interviewer_handling"] == "consider"
