"""Structured project state for SAGE Internal V1.

These schemas are the single source of truth for project state. They mirror
the canonical SAGE V3.2 schemas (see prompts/canonical/) — field names and
enumerations must not drift from the canonical definitions.

Canonical references:
  - Contributor roster: 03_Structuring_and_Approval  §Contributor Roster schema
  - Classification labels: 01_Project_Instructions   §5 Material classification
  - Content functions:   01_Project_Instructions     §6 Content-function grouping
  - Paper edit fields:   01/03                       §9 / §Paper Edit Table
  - Beat statuses:       01/03                       §Beat status meanings
  - Uncertainty labels:  01/03                       §Uncertainty labels
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enumerations — canonical, do not extend without updating canonical files
# ---------------------------------------------------------------------------

class ProjectPhase(str, Enum):
    """Server-enforced phase state machine."""

    CREATED = "created"
    INPUTS_UPLOADED = "inputs_uploaded"
    SETUP_COMPLETE = "setup_complete"
    ANALYSING = "analysing"
    PAPER_EDIT_READY = "paper_edit_ready"
    IN_REVIEW = "in_review"
    REVISING = "revising"
    APPROVED = "approved"
    REBUILDING = "rebuilding"
    VALIDATING = "validating"
    COMPLETE = "complete"
    FAILED = "failed"


# Legal transitions. The engine refuses anything else.
PHASE_TRANSITIONS: dict[ProjectPhase, set[ProjectPhase]] = {
    ProjectPhase.CREATED: {ProjectPhase.INPUTS_UPLOADED},
    ProjectPhase.INPUTS_UPLOADED: {ProjectPhase.SETUP_COMPLETE},
    ProjectPhase.SETUP_COMPLETE: {ProjectPhase.ANALYSING},
    ProjectPhase.ANALYSING: {ProjectPhase.PAPER_EDIT_READY, ProjectPhase.FAILED},
    ProjectPhase.PAPER_EDIT_READY: {ProjectPhase.IN_REVIEW},
    ProjectPhase.IN_REVIEW: {ProjectPhase.REVISING, ProjectPhase.APPROVED},
    ProjectPhase.REVISING: {ProjectPhase.IN_REVIEW, ProjectPhase.FAILED},
    ProjectPhase.APPROVED: {ProjectPhase.REBUILDING},
    ProjectPhase.REBUILDING: {ProjectPhase.VALIDATING, ProjectPhase.FAILED},
    ProjectPhase.VALIDATING: {ProjectPhase.COMPLETE, ProjectPhase.FAILED},
    ProjectPhase.COMPLETE: set(),
    ProjectPhase.FAILED: set(),
}


class FieldOrigin(str, Enum):
    USER = "user"
    INFERRED = "inferred"
    DEFAULT = "default"


class ContributorStatus(str, Enum):
    KEEP = "keep"
    OPTIONAL = "optional"
    MINIMISE = "minimise"
    EXCLUDE = "exclude"


class MaterialLabel(str, Enum):
    """Canonical §5 material classification labels."""

    KEEPER = "keeper"
    USABLE_TRIM = "usable_trim"
    SETUP = "setup"
    DEFINITION = "definition"
    PROCESS = "process"
    EXAMPLE = "example"
    EVIDENCE = "evidence"
    REFLECTION = "reflection"
    OUTCOME = "outcome"
    BRIDGE = "bridge"
    CLOSE = "close"
    REPEAT = "repeat"
    FILLER = "filler"
    FALSE_START = "false_start"
    POOR_TAKE = "poor_take"
    FRAGMENT = "fragment"
    CONTAMINATION = "contamination"
    TECH_RISK = "tech_risk"


class ContentFunction(str, Enum):
    """Canonical §6 content-function groups."""

    HOOK = "hook"
    CONTEXT = "context"
    DEFINITION = "definition"
    PROBLEM = "problem"
    PROCESS = "process"
    EXAMPLE = "example"
    EVIDENCE = "evidence"
    REFLECTION = "reflection"
    OUTCOME = "outcome"
    TRANSITION = "transition"
    CLOSING = "closing"
    EXCLUDE = "exclude"


class CleanupStrategy(str, Enum):
    CONSERVATIVE = "conservative"
    NATURAL = "natural"  # canonical default
    MODERATE = "moderate"
    PUNCHY = "punchy"
    AGGRESSIVE = "aggressive"


class EditMode(str, Enum):
    NARRATIVE = "narrative"
    SELECTS = "selects"
    CLEANUP = "cleanup"


class BeatStatus(str, Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    LOCKED = "locked"
    REJECTED = "rejected"


class UncertaintyLabel(str, Enum):
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    IDENTITY_UNCERTAIN = "IDENTITY_UNCERTAIN"
    MATCH_APPROXIMATE = "MATCH_APPROXIMATE"
    SENTENCE_SEAM_RISK = "SENTENCE_SEAM_RISK"
    BALANCE_RISK = "BALANCE_RISK"
    CONTINUITY_RISK = "CONTINUITY_RISK"


class RebuildStyle(str, Enum):
    """Canonical file 04 rebuild styles."""

    A_MAX_STRUCTURAL_PRESERVATION = "A"
    B_EDITORIAL_USABILITY_FIRST = "B"  # V1 default
    C_SIMPLIFIED_HANDOFF = "C"


class CheckOutcome(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


# ---------------------------------------------------------------------------
# Setup / intent — the file-02 capture set
# ---------------------------------------------------------------------------

class SetupField(BaseModel):
    """A captured-or-inferred setup value with provenance."""

    value: Optional[str] = None
    origin: FieldOrigin = FieldOrigin.DEFAULT


class ProjectSetup(BaseModel):
    """Canonical file 02 capture set. 'infer' is expressed as value=None
    with origin=default until inference fills it during analysis."""

    runtime_target: SetupField = SetupField()
    hard_cap: SetupField = SetupField()
    graphics_in_cap: SetupField = SetupField()
    tone: SetupField = SetupField()
    cut_style: SetupField = SetupField(value=CleanupStrategy.NATURAL.value)
    representation: SetupField = SetupField()
    contributor_rule: SetupField = SetupField()
    opening: SetupField = SetupField()
    ending: SetupField = SetupField()
    clarity: SetupField = SetupField()
    source_handling: SetupField = SetupField(value="single")  # V1: single only
    audio_baseline: SetupField = SetupField()
    camera_audio: SetupField = SetupField()
    audio_rebuild: SetupField = SetupField()
    multicam: SetupField = SetupField()
    must_keep: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    known_contributors: list[str] = Field(default_factory=list)
    preset: SetupField = SetupField()


# ---------------------------------------------------------------------------
# Inputs and audit
# ---------------------------------------------------------------------------

class InputFile(BaseModel):
    file_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    kind: str  # "xml" | "transcript" | "notes"
    filename: str
    stored_path: str
    checksum_sha256: str
    uploaded_at: datetime = Field(default_factory=_now)
    # Set when ingest transformed the file (e.g. word-timed JSON transcript
    # normalized to SAGE text) so the person can see what happened.
    ingest_note: str | None = None


class SourceAudit(BaseModel):
    """Deterministic facts extracted from source XML by the xmlengine,
    plus LLM-assessed risks. Populated during ANALYSING."""

    frame_rate: Optional[float] = None
    ntsc: Optional[bool] = None
    track_structure: dict = Field(default_factory=dict)
    sync_baseline: Optional[str] = None
    linked_audio: list[dict] = Field(default_factory=list)
    tech_risks: list[str] = Field(default_factory=list)
    source_count: int = 0
    material_type_guess: Optional[str] = None


# ---------------------------------------------------------------------------
# Roster, classification, grouping, structure
# ---------------------------------------------------------------------------

class Contributor(BaseModel):
    cid: str
    label: str
    role: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[str] = None
    status: ContributorStatus = ContributorStatus.KEEP
    value_note: Optional[str] = None
    ambiguity_note: Optional[str] = None


class ClassifiedSegment(BaseModel):
    seg_id: str
    source: str
    transcript_span: tuple[int, int]  # character offsets into transcript
    time_span: Optional[tuple[float, float]] = None  # seconds, if resolvable
    label: MaterialLabel
    cid: Optional[str] = None
    confidence: Optional[str] = None


class FunctionGroup(BaseModel):
    func: ContentFunction
    seg_ids: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class StructurePlan(BaseModel):
    mode: Optional[EditMode] = None
    cleanup_strategy: CleanupStrategy = CleanupStrategy.NATURAL
    beat_order: list[str] = Field(default_factory=list)  # BIDs
    rationale: Optional[str] = None


# ---------------------------------------------------------------------------
# Paper edit
# ---------------------------------------------------------------------------

class Beat(BaseModel):
    """One row of the canonical Paper Edit Table."""

    bid: str
    src: str
    cid: Optional[str] = None
    role: Optional[str] = None
    func: ContentFunction
    quote_stub: Optional[str] = None
    exact_quote: Optional[str] = None  # resolved deterministically when shortlisted
    est_duration: Optional[float] = None  # seconds
    boundary_status: Optional[str] = None
    confidence: Optional[str] = None
    include_reason: Optional[str] = None
    representation_note: Optional[str] = None
    graphics_note: Optional[str] = None
    uncertainty_labels: list[UncertaintyLabel] = Field(default_factory=list)
    status: BeatStatus = BeatStatus.DRAFT
    seg_ids: list[str] = Field(default_factory=list)  # provenance to segments


class PaperEdit(BaseModel):
    version: int = 1
    beats: list[Beat] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)

    def beat(self, bid: str) -> Optional[Beat]:
        return next((b for b in self.beats if b.bid == bid), None)

    @property
    def locked_bids(self) -> set[str]:
        return {b.bid for b in self.beats if b.status == BeatStatus.LOCKED}

    @property
    def rejected_bids(self) -> set[str]:
        return {b.bid for b in self.beats if b.status == BeatStatus.REJECTED}


# ---------------------------------------------------------------------------
# Ledger, revisions, approval
# ---------------------------------------------------------------------------

class LedgerEntry(BaseModel):
    key: str  # e.g. "job_mode", "runtime_target", "audio_strategy"
    value: str
    origin: FieldOrigin
    settled_at: datetime = Field(default_factory=_now)


class DecisionLedger(BaseModel):
    """Canonical decision ledger. Settled items are not reopened unless the
    user asks, a conflict arises, or a technical blocker forces review."""

    entries: list[LedgerEntry] = Field(default_factory=list)

    def settle(self, key: str, value: str, origin: FieldOrigin) -> None:
        self.entries = [e for e in self.entries if e.key != key]
        self.entries.append(LedgerEntry(key=key, value=value, origin=origin))

    def get(self, key: str) -> Optional[str]:
        return next((e.value for e in self.entries if e.key == key), None)


class RevisionDelta(BaseModel):
    """Canonical delta report — Targeted Revision Mode output."""

    paper_edit_version: int
    changed_bids: list[str]
    reason: str
    runtime_effect: Optional[str] = None
    contributor_effect: Optional[str] = None
    risk_effect: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class Approval(BaseModel):
    approved_by: str
    approved_at: datetime = Field(default_factory=_now)
    approved_items: list[str] = Field(default_factory=list)
    accepted_risks: list[str] = Field(default_factory=list)
    paper_edit_version: int


# ---------------------------------------------------------------------------
# Rebuild and validation
# ---------------------------------------------------------------------------

class BeatMapping(BaseModel):
    """LLM plans; code builds. One mapping per approved/locked beat."""

    bid: str
    source_file_id: str
    clipitem_refs: list[str] = Field(default_factory=list)
    in_seconds: float
    out_seconds: float
    track_handling: Optional[str] = None
    audio_handling: Optional[str] = None
    boundary_note: Optional[str] = None
    uncertainty_labels: list[UncertaintyLabel] = Field(default_factory=list)


class RebuildPlan(BaseModel):
    style: RebuildStyle = RebuildStyle.B_EDITORIAL_USABILITY_FIRST
    mappings: list[BeatMapping] = Field(default_factory=list)
    provenance_notes: list[str] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    name: str
    outcome: CheckOutcome
    detail: Optional[str] = None


class Blocker(BaseModel):
    """Canonical failure rule: exact blocker, why it blocks, what is needed."""

    check: str
    why_it_blocks: str
    what_is_needed: str


class ValidationReport(BaseModel):
    checks: list[ValidationCheck] = Field(default_factory=list)
    blockers: list[Blocker] = Field(default_factory=list)
    overall: CheckOutcome = CheckOutcome.FAIL
    produced_at: datetime = Field(default_factory=_now)


class OutputArtefact(BaseModel):
    xml_path: str
    checksum_sha256: str
    produced_at: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Project aggregate root
# ---------------------------------------------------------------------------

class ProjectMeta(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    phase: ProjectPhase = ProjectPhase.CREATED
    # Provider is chosen at project creation, recorded here, and never
    # switched silently. Changing it is an explicit user action that is
    # itself recorded in provider_history.
    provider: str = "mock"
    provider_history: list[dict] = Field(default_factory=list)
    schema_version: int = 1


class Project(BaseModel):
    meta: ProjectMeta
    inputs: list[InputFile] = Field(default_factory=list)
    setup: ProjectSetup = ProjectSetup()
    source_audit: SourceAudit = SourceAudit()
    roster: list[Contributor] = Field(default_factory=list)
    classification: list[ClassifiedSegment] = Field(default_factory=list)
    groups: list[FunctionGroup] = Field(default_factory=list)
    structure: StructurePlan = StructurePlan()
    paper_edit: Optional[PaperEdit] = None
    paper_edit_history: list[PaperEdit] = Field(default_factory=list)
    ledger: DecisionLedger = DecisionLedger()
    revisions: list[RevisionDelta] = Field(default_factory=list)
    approval: Optional[Approval] = None
    rebuild: Optional[RebuildPlan] = None
    validation: Optional[ValidationReport] = None
    output: Optional[OutputArtefact] = None
