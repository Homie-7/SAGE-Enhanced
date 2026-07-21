"""Phase machine + approval gate tests — these run now (Stage 2)."""

import pytest

from app.orchestration.engine import (
    ApprovalGateError,
    IllegalTransitionError,
    OrchestrationEngine,
)
from app.schemas.state import Approval, PaperEdit, Project, ProjectMeta, ProjectPhase


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


# --- reopening setup ----------------------------------------------------------

@pytest.mark.parametrize("phase", [
    ProjectPhase.SETUP_COMPLETE, ProjectPhase.ANALYSING, ProjectPhase.FAILED,
])
async def test_reopen_setup_allowed_pre_approval(phase):
    engine = OrchestrationEngine(_NullStore(), registry=None)
    project = _project(phase)
    project.paper_edit = PaperEdit(version=1, beats=[])
    started_generation = project.meta.run_generation

    result = await engine.reopen_setup(project)

    assert result.meta.phase == ProjectPhase.INPUTS_UPLOADED
    assert result.meta.run_generation == started_generation + 1
    assert result.paper_edit is None


@pytest.mark.parametrize("phase", [
    ProjectPhase.PAPER_EDIT_READY, ProjectPhase.IN_REVIEW, ProjectPhase.REVISING,
])
async def test_reopen_setup_refused_once_paper_edit_exists_but_not_approved(phase):
    # Design decision: reopening is scoped to Setup + Processing only: once a
    # paper edit exists (Review onward), the phase graph itself has no
    # transition back to INPUTS_UPLOADED from these phases, independent of
    # approval — this is enforced by PHASE_TRANSITIONS, not the approval
    # check, so it raises IllegalTransitionError rather than ApprovalGateError.
    engine = OrchestrationEngine(_NullStore(), registry=None)
    project = _project(phase)
    with pytest.raises(IllegalTransitionError):
        await engine.reopen_setup(project)


async def test_reopen_setup_refused_after_approval():
    engine = OrchestrationEngine(_NullStore(), registry=None)
    project = _project(ProjectPhase.FAILED)
    project.approval = Approval(approved_by="editor@rmit", paper_edit_version=1)
    with pytest.raises(ApprovalGateError):
        await engine.reopen_setup(project)
