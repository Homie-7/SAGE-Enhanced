"""Planning pipeline task definitions.

For each LLM task in the canonical planning order this module provides:
  - which canonical files the prompt needs,
  - a context builder (task-scoped slice of structured state), and
  - an applier that writes the validated output back into project state.

The LLM never mutates state directly; appliers are the only write path and
they validate referential integrity before accepting anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Type

from pydantic import BaseModel

from app.orchestration.ledger import settle
from app.schemas.state import (
    BeatStatus,
    FieldOrigin,
    PaperEdit,
    Project,
)
from app.schemas.tasks import (
    ClassificationOutput,
    GroupingOutput,
    PaperEditOutput,
    RosterOutput,
    SourceAuditOutput,
    StructureOutput,
)


class TaskApplyError(Exception):
    """Raised with an exact blocker when a task output cannot be accepted
    into project state (canonical failure rule)."""


# ---------------------------------------------------------------------------
# Shared context slices
# ---------------------------------------------------------------------------

def _setup_context(project: Project) -> dict:
    return project.setup.model_dump(mode="json")


def _ledger_context(project: Project) -> dict:
    return {e.key: e.value for e in project.ledger.entries}


def _audit_context(project: Project) -> dict:
    return project.source_audit.model_dump(mode="json")


def _segments_context(project: Project) -> list[dict]:
    return [s.model_dump(mode="json") for s in project.classification]


# ---------------------------------------------------------------------------
# Context builders (transcript_text is passed in; it is an artefact, not state)
# ---------------------------------------------------------------------------

def ctx_source_audit(project: Project, transcript_text: str) -> dict:
    return {
        "deterministic_source_facts": _audit_context(project),
        "setup": _setup_context(project),
        "transcript": transcript_text,
    }


def ctx_contributor_roster(project: Project, transcript_text: str) -> dict:
    return {
        "known_contributors": project.setup.known_contributors,
        "material_type_guess": project.source_audit.material_type_guess,
        "crew_interviewer_handling": project.setup.crew_interviewer.value or "exclude",
        "transcript": transcript_text,
    }


def ctx_material_classification(project: Project, transcript_text: str) -> dict:
    return {
        "roster": [c.model_dump(mode="json") for c in project.roster],
        "transcript_length_chars": len(transcript_text),
        "transcript": transcript_text,
        "span_rule": (
            "transcript_span values are [start, end) character offsets into "
            "the transcript exactly as provided. time_span values are seconds "
            "on the source timeline taken from transcript timecodes."
        ),
    }


def ctx_function_grouping(project: Project, transcript_text: str) -> dict:
    return {
        "segments": _segments_context(project),
        "setup": _setup_context(project),
    }


def ctx_mode_and_structure(project: Project, transcript_text: str) -> dict:
    return {
        "groups": [g.model_dump(mode="json") for g in project.groups],
        "segments": _segments_context(project),
        "setup": _setup_context(project),
        "settled_decisions": _ledger_context(project),
    }


def ctx_paper_edit(project: Project, transcript_text: str) -> dict:
    return {
        "roster": [c.model_dump(mode="json") for c in project.roster],
        "segments": _segments_context(project),
        "groups": [g.model_dump(mode="json") for g in project.groups],
        "structure": project.structure.model_dump(mode="json"),
        "setup": _setup_context(project),
        "settled_decisions": _ledger_context(project),
        "transcript": transcript_text,
        "data_rules": (
            "Emit quote_stub only (first words … last words); exact quotes are "
            "resolved deterministically later. Every beat must reference real "
            "seg_ids. Beat status starts as 'candidate'."
        ),
    }


# ---------------------------------------------------------------------------
# Appliers
# ---------------------------------------------------------------------------

def apply_source_audit(project: Project, out: SourceAuditOutput, transcript_text: str) -> None:
    project.source_audit.tech_risks = out.tech_risks
    project.source_audit.material_type_guess = out.material_type_guess


def apply_contributor_roster(project: Project, out: RosterOutput, transcript_text: str) -> None:
    if not out.contributors:
        raise TaskApplyError(
            "Roster task returned zero contributors; a SAGE job requires at "
            "least one. Check the transcript upload."
        )
    cids = [c.cid for c in out.contributors]
    if len(cids) != len(set(cids)):
        raise TaskApplyError("Roster contains duplicate CIDs; CIDs must be unique.")
    project.roster = out.contributors


def apply_material_classification(
    project: Project, out: ClassificationOutput, transcript_text: str
) -> None:
    if not out.segments:
        raise TaskApplyError("Classification returned zero segments.")
    cids = {c.cid for c in project.roster}
    n = len(transcript_text)
    seg_ids = set()
    for seg in out.segments:
        if seg.seg_id in seg_ids:
            raise TaskApplyError(f"Duplicate seg_id '{seg.seg_id}' in classification.")
        seg_ids.add(seg.seg_id)
        lo, hi = seg.transcript_span
        if not (0 <= lo < hi <= n):
            raise TaskApplyError(
                f"Segment {seg.seg_id} span [{lo}, {hi}) is outside the "
                f"transcript (length {n}). Spans must index real transcript text."
            )
        if seg.cid is not None and seg.cid not in cids:
            raise TaskApplyError(
                f"Segment {seg.seg_id} references unknown contributor '{seg.cid}'."
            )
    project.classification = out.segments


def apply_function_grouping(project: Project, out: GroupingOutput, transcript_text: str) -> None:
    known = {s.seg_id for s in project.classification}
    for group in out.groups:
        unknown = [s for s in group.seg_ids if s not in known]
        if unknown:
            raise TaskApplyError(
                f"Group '{group.func.value}' references unknown segments: {unknown}."
            )
    project.groups = out.groups


def apply_mode_and_structure(project: Project, out: StructureOutput, transcript_text: str) -> None:
    project.structure.mode = out.mode
    project.structure.rationale = out.rationale
    settle(project.ledger, "job_mode", out.mode.value, FieldOrigin.INFERRED)
    settle(
        project.ledger,
        "cleanup_strategy",
        project.structure.cleanup_strategy.value,
        FieldOrigin.INFERRED,
    )


def apply_paper_edit(project: Project, out: PaperEditOutput, transcript_text: str) -> None:
    if not out.beats:
        raise TaskApplyError("Paper edit task returned zero beats.")
    known_segs = {s.seg_id for s in project.classification}
    cids = {c.cid for c in project.roster}
    bids = set()
    for beat in out.beats:
        if beat.bid in bids:
            raise TaskApplyError(f"Duplicate BID '{beat.bid}' in paper edit.")
        bids.add(beat.bid)
        if not beat.seg_ids:
            raise TaskApplyError(
                f"Beat {beat.bid} has no seg_ids; every beat must map to real "
                "source segments (canonical structural source rule)."
            )
        unknown = [s for s in beat.seg_ids if s not in known_segs]
        if unknown:
            raise TaskApplyError(f"Beat {beat.bid} references unknown segments: {unknown}.")
        if beat.cid is not None and beat.cid not in cids:
            raise TaskApplyError(f"Beat {beat.bid} references unknown contributor '{beat.cid}'.")
        if beat.status not in (BeatStatus.DRAFT, BeatStatus.CANDIDATE):
            # The LLM proposes; humans lock/reject.
            beat.status = BeatStatus.CANDIDATE
    project.paper_edit = PaperEdit(version=1, beats=out.beats)
    project.structure.beat_order = [b.bid for b in out.beats]


# ---------------------------------------------------------------------------
# Exact-quote resolution (deterministic; canonical quote-stub-first rule)
# ---------------------------------------------------------------------------

_TIMECODE = re.compile(r"\[\d{2}:\d{2}:\d{2}\]\s*")
_SPEAKER = re.compile(r"^[A-Z][A-Za-z .'-]{0,40}:\s*", re.MULTILINE)


def _clean_span_text(text: str) -> str:
    text = _TIMECODE.sub("", text)
    text = _SPEAKER.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def resolve_exact_quotes(project: Project, transcript_text: str) -> None:
    """Resolve exact quotes for locked beats deterministically from the
    transcript spans of their segments. Stubs stay stubs until locking."""
    if project.paper_edit is None:
        return
    spans = {s.seg_id: s.transcript_span for s in project.classification}
    for beat in project.paper_edit.beats:
        if beat.status != BeatStatus.LOCKED:
            continue
        pieces = []
        for seg_id in beat.seg_ids:
            span = spans.get(seg_id)
            if span is None:
                continue
            pieces.append(_clean_span_text(transcript_text[span[0]:span[1]]))
        if pieces:
            beat.exact_quote = " ".join(pieces)


# ---------------------------------------------------------------------------
# Registry consumed by the orchestration engine
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlanningTask:
    name: str
    canonical_files: list[str]
    output_model: Type[BaseModel]
    build_context: Callable[[Project, str], dict]
    apply: Callable[[Project, BaseModel, str], None]


_CORE = "01_Project_Instructions_V3_2_Efficient.md"
_KICKOFF = "02_Kickoff_Intent_and_Presets_V3_2_Efficient.md"
_STRUCTURE = "03_Structuring_and_Approval_V3_2_Efficient.md"

PLANNING_TASKS: dict[str, PlanningTask] = {
    t.name: t
    for t in [
        PlanningTask("source_audit", [_CORE], SourceAuditOutput,
                     ctx_source_audit, apply_source_audit),
        PlanningTask("contributor_roster", [_CORE], RosterOutput,
                     ctx_contributor_roster, apply_contributor_roster),
        PlanningTask("material_classification", [_CORE], ClassificationOutput,
                     ctx_material_classification, apply_material_classification),
        PlanningTask("function_grouping", [_CORE], GroupingOutput,
                     ctx_function_grouping, apply_function_grouping),
        PlanningTask("mode_and_structure", [_CORE, _KICKOFF], StructureOutput,
                     ctx_mode_and_structure, apply_mode_and_structure),
        PlanningTask("paper_edit", [_CORE, _STRUCTURE], PaperEditOutput,
                     ctx_paper_edit, apply_paper_edit),
    ]
}
