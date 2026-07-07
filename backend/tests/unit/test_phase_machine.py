"""Phase machine + approval gate tests — these run now (Stage 2)."""

import pytest

from app.orchestration.engine import (
    ApprovalGateError,
    IllegalTransitionError,
    OrchestrationEngine,
)
from app.schemas.state import Project, ProjectMeta, ProjectPhase


class _NullStore:
    async def save(self, project):
        return project


def _project(phase: ProjectPhase) -> Project:
    p = Project(meta=ProjectMeta(name="t", provider="mock"))
    p.meta.phase = phase
    return p


def test_illegal_transition_refused():
    engine = OrchestrationEngine(_NullStore(), registry=None)
    with pytest.raises(IllegalTransitionError):
        engine.assert_transition(_project(ProjectPhase.CREATED), ProjectPhase.REBUILDING)


def test_legal_transition_allowed():
    engine = OrchestrationEngine(_NullStore(), registry=None)
    engine.assert_transition(_project(ProjectPhase.CREATED), ProjectPhase.INPUTS_UPLOADED)


def test_rebuild_refused_without_approval():
    engine = OrchestrationEngine(_NullStore(), registry=None)
    with pytest.raises(ApprovalGateError):
        engine.assert_rebuild_allowed(_project(ProjectPhase.IN_REVIEW))
