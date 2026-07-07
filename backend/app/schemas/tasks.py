"""I/O contracts for LLM tasks.

Every LLM task has a typed input assembled from structured state and a typed
output validated with Pydantic before it touches project state. The LLM never
mutates state directly.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .state import (
    Beat,
    ClassifiedSegment,
    Contributor,
    ContentFunction,
    EditMode,
    FunctionGroup,
    RebuildPlan,
    UncertaintyLabel,
)


class TaskSpec(BaseModel):
    """Fully assembled request handed to a provider adapter."""

    task_name: str
    system_prompt: str
    user_prompt: str
    output_schema: dict  # JSON Schema for the expected output
    max_output_tokens: Optional[int] = None


class TaskUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class TaskResult(BaseModel):
    task_name: str
    provider: str
    raw_text: str
    parsed: Optional[dict] = None  # schema-valid JSON, or None on failure
    valid: bool = False
    repair_attempted: bool = False
    error: Optional[str] = None
    usage: TaskUsage = TaskUsage()


# --- Typed task outputs (what `parsed` must validate against) ---------------

class SourceAuditOutput(BaseModel):
    tech_risks: list[str] = Field(default_factory=list)
    material_type_guess: Optional[str] = None
    notes: Optional[str] = None


class RosterOutput(BaseModel):
    contributors: list[Contributor]


class ClassificationOutput(BaseModel):
    segments: list[ClassifiedSegment]


class GroupingOutput(BaseModel):
    groups: list[FunctionGroup]


class StructureOutput(BaseModel):
    mode: EditMode
    rationale: str
    proposed_order: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class PaperEditOutput(BaseModel):
    beats: list[Beat]
    representation_summary: Optional[str] = None
    clarity_summary: Optional[str] = None
    main_risks: list[str] = Field(default_factory=list)


class RevisionOutput(BaseModel):
    """Targeted Revision Mode: affected beats only, never the full plan."""

    changed_beats: list[Beat]
    reason: str
    runtime_effect: Optional[str] = None
    contributor_effect: Optional[str] = None
    risk_effect: Optional[str] = None


class RebuildPlanOutput(BaseModel):
    plan: RebuildPlan
    seam_risks: list[str] = Field(default_factory=list)
