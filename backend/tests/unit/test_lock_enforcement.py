"""Deterministic lock-diff tests — these run now (Stage 2)."""

from app.orchestration.revision import diff_paper_edits
from app.schemas.state import Beat, BeatStatus, ContentFunction, PaperEdit


def _beat(bid: str, status: BeatStatus, stub: str = "s") -> Beat:
    return Beat(bid=bid, src="src1", func=ContentFunction.CONTEXT,
                quote_stub=stub, status=status)


def test_locked_beat_modification_is_violation():
    prev = PaperEdit(version=1, beats=[_beat("B1", BeatStatus.LOCKED, "original")])
    prop = PaperEdit(version=2, beats=[_beat("B1", BeatStatus.LOCKED, "altered")])
    diff = diff_paper_edits(prev, prop)
    assert not diff.ok
    assert diff.violations[0].kind == "locked_modified"


def test_locked_beat_removal_is_violation():
    prev = PaperEdit(version=1, beats=[_beat("B1", BeatStatus.LOCKED)])
    prop = PaperEdit(version=2, beats=[])
    diff = diff_paper_edits(prev, prop)
    assert any(v.kind == "locked_removed" for v in diff.violations)


def test_rejected_beat_reintroduction_is_violation():
    prev = PaperEdit(version=1, beats=[_beat("B9", BeatStatus.REJECTED)])
    prop = PaperEdit(version=2, beats=[_beat("B9", BeatStatus.CANDIDATE)])
    diff = diff_paper_edits(prev, prop)
    assert any(v.kind == "rejected_reintroduced" for v in diff.violations)


def test_reopened_lock_change_is_legal():
    prev = PaperEdit(version=1, beats=[_beat("B1", BeatStatus.LOCKED, "original")])
    prop = PaperEdit(version=2, beats=[_beat("B1", BeatStatus.CANDIDATE, "altered")])
    diff = diff_paper_edits(prev, prop, reopened_bids={"B1"})
    assert diff.ok
    assert diff.changed_bids == ["B1"]


def test_untouched_plan_is_clean():
    beats = [_beat("B1", BeatStatus.LOCKED), _beat("B2", BeatStatus.CANDIDATE)]
    prev = PaperEdit(version=1, beats=beats)
    prop = PaperEdit(version=2, beats=[b.model_copy(deep=True) for b in beats])
    assert diff_paper_edits(prev, prop).ok
