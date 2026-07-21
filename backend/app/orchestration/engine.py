"""Orchestration engine — the canonical SAGE phase machine.

Owns:
  - legal phase transitions (schemas.state.PHASE_TRANSITIONS)
  - the planning pipeline order (canonical workflow order, file 01)
  - the hard approval gate before rebuild
  - decision-ledger updates as phases settle decisions

The engine is provider-agnostic: it resolves the adapter recorded in
Project.meta.provider via the registry, per task, and never substitutes
another provider on failure.
"""

from __future__ import annotations

from pathlib import Path

from app import config
from app.orchestration.ledger import settle_from_setup
from app.orchestration.revision import diff_paper_edits
from app.orchestration.tasks.assembly import PromptRepository, assemble_task
from app.orchestration.tasks.pipeline import (
    PLANNING_TASKS,
    TaskApplyError,
    resolve_exact_quotes,
)
from app.orchestration.tasks.runner import run_validated
from app.providers.registry import ProviderRegistry
from app.schemas.state import (
    PHASE_TRANSITIONS,
    Approval,
    BeatMapping,
    BeatStatus,
    Blocker,
    CheckOutcome,
    DecisionLedger,
    OutputArtefact,
    PaperEdit,
    Project,
    ProjectPhase,
    RevisionDelta,
    SourceAudit,
    StructurePlan,
    ValidationReport,
)
from app.schemas.tasks import RebuildPlanOutput, RevisionOutput
from app.storage.base import ArtefactStore, ProjectStore
from app.validation.lock_enforcement import check_locks
from app.validation.plan_fidelity import check_plan_fidelity, check_quote_fidelity
from app.validation.report import ReportBuilder
from app.validation.schema_checks import check_state_integrity
from app.validation.xml_integrity import check_output_xml
from app.xmlengine.parser import XMLParseError, parse_source_xml
from app.xmlengine.rebuilder import RebuildError, rebuild_sequence


class IllegalTransitionError(Exception):
    pass


class ApprovalGateError(Exception):
    """Raised when rebuild is attempted without an approved paper edit."""


class TaskFailure(Exception):
    """A task failed honestly. Carries the exact blocker."""

    def __init__(self, task_name: str, why: str, what_is_needed: str):
        super().__init__(f"{task_name}: {why}")
        self.blocker = Blocker(check=task_name, why_it_blocks=why, what_is_needed=what_is_needed)


class RevisionRejected(Exception):
    """Raised when a proposed revision violates lock/rejection rules."""

    def __init__(self, report: ValidationReport):
        super().__init__("Revision rejected by lock enforcement.")
        self.report = report


# Canonical planning pipeline (workflow order, file 01, phases 3–9).
# Kickoff (1) and intent capture (2) are the upload + quick-setup flows.
PLANNING_TASK_ORDER: list[str] = [
    "source_audit",
    "contributor_roster",
    "material_classification",
    "function_grouping",
    "mode_and_structure",
    "paper_edit",
]


class OrchestrationEngine:
    def __init__(
        self,
        store: ProjectStore,
        registry: ProviderRegistry,
        artefacts: ArtefactStore | None = None,
        prompts_root: str | Path | None = None,
    ):
        self._store = store
        self._registry = registry
        self._artefacts = artefacts
        self._prompts = PromptRepository(prompts_root or config.PROMPTS_ROOT)

    # -- phase machine ------------------------------------------------------

    def assert_transition(self, project: Project, target: ProjectPhase) -> None:
        current = project.meta.phase
        if target not in PHASE_TRANSITIONS[current]:
            raise IllegalTransitionError(
                f"Cannot move project from '{current.value}' to "
                f"'{target.value}'. Legal targets: "
                f"{sorted(p.value for p in PHASE_TRANSITIONS[current])}."
            )

    async def transition(self, project: Project, target: ProjectPhase) -> Project:
        self.assert_transition(project, target)
        project.meta.phase = target
        return await self._store.save(project)

    # -- approval gate (hard, in code) --------------------------------------

    def assert_rebuild_allowed(self, project: Project) -> None:
        if project.meta.phase != ProjectPhase.APPROVED or project.approval is None:
            raise ApprovalGateError(
                "Rebuild refused: the paper edit has not been approved. "
                "Human approval before rebuild is a non-negotiable SAGE rule."
            )
        if (
            project.paper_edit is None
            or project.approval.paper_edit_version != project.paper_edit.version
        ):
            raise ApprovalGateError(
                "Rebuild refused: the approved paper edit version does not "
                "match the current paper edit. Re-approve the current version."
            )

    # -- helpers -------------------------------------------------------------

    def _input(self, project: Project, kind: str):
        return next((f for f in project.inputs if f.kind == kind), None)

    async def _read_transcript(self, project: Project) -> str:
        t = self._input(project, "transcript")
        if t is None:
            raise TaskFailure(
                "inputs", "No transcript has been uploaded.",
                "Upload a transcript before running planning.",
            )
        data = await self._artefacts.read(project.meta.id, Path(t.stored_path).name)
        return data.decode("utf-8", errors="replace")

    def _adapter(self, project: Project):
        return self._registry.get(project.meta.provider)

    async def _run_task(self, project: Project, task_name: str, canonical_files: list[str],
                        context: dict, output_model):
        adapter = self._adapter(project)
        schema = output_model.model_json_schema()
        spec = assemble_task(
            self._prompts,
            task_name=task_name,
            provider=project.meta.provider,
            canonical_files=canonical_files,
            state_context=context,
            output_schema=schema,
            max_output_tokens=adapter.capabilities.max_output_tokens,
        )
        result, model = await run_validated(adapter, spec, output_model)
        if model is None:
            raise TaskFailure(
                task_name,
                result.error or "Task produced no valid output.",
                "Inspect the provider response; re-run the phase or adjust inputs.",
            )
        return model

    async def _fail(self, project: Project, blocker: Blocker) -> Project:
        report = project.validation or ValidationReport()
        report.blockers.append(blocker)
        report.overall = CheckOutcome.FAIL
        project.validation = report
        project.meta.phase = ProjectPhase.FAILED
        return await self._store.save(project)

    async def _superseded(self, project_id: str, started_generation: int) -> bool:
        """True if this project was reopened to Setup (generation moved on)
        or deleted (no longer exists) since this run_planning call started.
        Checked after every save in the loop below so a stale background
        task stops instead of overwriting fresher state — see
        reopen_setup's docstring for the write side of this contract."""
        fresh = await self._store.get(project_id)
        return fresh is None or fresh.meta.run_generation != started_generation

    # -- planning ------------------------------------------------------------

    async def run_planning(self, project: Project) -> Project:
        """Run PLANNING_TASK_ORDER end to end, updating structured state
        after each task."""
        started_generation = project.meta.run_generation
        project = await self.transition(project, ProjectPhase.ANALYSING)
        settle_from_setup(project)

        # Deterministic facts first — the LLM never guesses XML structure.
        xml_input = self._input(project, "xml")
        if xml_input is None:
            return await self._fail(project, Blocker(
                check="inputs", why_it_blocks="No source XML uploaded.",
                what_is_needed="Upload the synced source XML.",
            ))
        try:
            facts = parse_source_xml(xml_input.stored_path)
        except XMLParseError as exc:
            return await self._fail(project, Blocker(
                check="source_xml_parse", why_it_blocks=str(exc),
                what_is_needed="Provide a valid FCP7/Premiere XML export.",
            ))
        project.source_audit.frame_rate = facts.frame_rate
        project.source_audit.ntsc = facts.ntsc
        project.source_audit.track_structure = {
            "video_tracks": facts.video_tracks,
            "audio_tracks": facts.audio_tracks,
            "clipitems": [c.model_dump(mode="json") for c in facts.clipitems],
            "multicam_detected": facts.multicam_detected,
            "external_audio_detected": facts.external_audio_detected,
            "warnings": facts.warnings,
        }
        project.source_audit.source_count = 1  # V1: single source
        await self._store.save(project)
        if await self._superseded(project.meta.id, started_generation):
            return project

        try:
            transcript = await self._read_transcript(project)
            for task_name in PLANNING_TASK_ORDER:
                task = PLANNING_TASKS[task_name]
                context = task.build_context(project, transcript)
                model = await self._run_task(
                    project, task_name, task.canonical_files, context, task.output_model
                )
                task.apply(project, model, transcript)
                await self._store.save(project)
                if await self._superseded(project.meta.id, started_generation):
                    return project
        except TaskFailure as exc:
            return await self._fail(project, exc.blocker)
        except TaskApplyError as exc:
            return await self._fail(project, Blocker(
                check="task_output_integrity", why_it_blocks=str(exc),
                what_is_needed="Re-run planning; the provider output failed "
                               "referential integrity checks.",
            ))

        return await self.transition(project, ProjectPhase.PAPER_EDIT_READY)

    # -- reopening setup ------------------------------------------------------

    async def reopen_setup(self, project: Project) -> Project:
        """Explicit, human-initiated reset back to Setup — from Setup itself,
        from Processing (analysing), or from a pre-approval failure. Discards
        the planning-derived state wholesale (never partially) but keeps
        setup answers and uploaded inputs, so the Setup page reopens
        pre-filled rather than blank. Bumps run_generation so an in-flight
        run_planning background task (if any) detects it has been
        superseded and stops instead of overwriting this reset — see
        _superseded above."""
        if project.approval is not None:
            raise ApprovalGateError(
                "Cannot reopen setup: this project has already been "
                "approved. Approval is a one-way gate."
            )
        project.meta.run_generation += 1
        project.source_audit = SourceAudit()
        project.roster = []
        project.classification = []
        project.groups = []
        project.structure = StructurePlan()
        project.paper_edit = None
        project.paper_edit_history = []
        project.ledger = DecisionLedger()
        project.validation = None
        return await self.transition(project, ProjectPhase.INPUTS_UPLOADED)

    # -- review helpers ------------------------------------------------------

    async def ensure_in_review(self, project: Project) -> Project:
        if project.meta.phase == ProjectPhase.PAPER_EDIT_READY:
            project = await self.transition(project, ProjectPhase.IN_REVIEW)
        return project

    # -- targeted revision ----------------------------------------------------

    async def run_revision(
        self, project: Project, instruction: str, reopened_bids: set[str] | None = None
    ) -> Project:
        """Targeted Revision Mode: delta only, lock-enforced deterministically."""
        reopened = reopened_bids or set()
        project = await self.ensure_in_review(project)
        project = await self.transition(project, ProjectPhase.REVISING)
        current = project.paper_edit
        assert current is not None

        locked = [b for b in current.beats if b.status == BeatStatus.LOCKED]
        rejected = sorted(current.rejected_bids)
        editable = [
            b for b in current.beats
            if b.status not in (BeatStatus.LOCKED, BeatStatus.REJECTED) or b.bid in reopened
        ]
        context = {
            "instruction": instruction,
            "explicitly_reopened_bids": sorted(reopened),
            "locked_beats_read_only": [b.model_dump(mode="json") for b in locked
                                       if b.bid not in reopened],
            "rejected_bids": rejected,
            "editable_beats": [b.model_dump(mode="json") for b in editable],
            "settled_decisions": {e.key: e.value for e in project.ledger.entries},
            "paper_edit_version": current.version,
        }
        try:
            out: RevisionOutput = await self._run_task(
                project, "targeted_revision",
                ["01_Project_Instructions_V3_2_Efficient.md",
                 "03_Structuring_and_Approval_V3_2_Efficient.md"],
                context, RevisionOutput,
            )
        except TaskFailure as exc:
            # Honest failure; the review continues on the existing version.
            project = await self.transition(project, ProjectPhase.IN_REVIEW)
            raise exc

        # Build the proposed version: apply the delta onto a copy.
        proposed = PaperEdit(
            version=current.version + 1,
            beats=[b.model_copy(deep=True) for b in current.beats],
        )
        by_bid = {b.bid: i for i, b in enumerate(proposed.beats)}
        for changed in out.changed_beats:
            if changed.bid in by_bid:
                proposed.beats[by_bid[changed.bid]] = changed
            else:
                proposed.beats.append(changed)

        rb = ReportBuilder()
        check_locks(current, proposed, rb, reopened_bids=reopened)
        report = rb.build()
        if report.overall == CheckOutcome.FAIL:
            # Reject the revision entirely; state is untouched.
            project = await self.transition(project, ProjectPhase.IN_REVIEW)
            raise RevisionRejected(report)

        project.paper_edit_history.append(current)
        project.paper_edit = proposed
        project.structure.beat_order = [b.bid for b in proposed.beats]
        project.revisions.append(RevisionDelta(
            paper_edit_version=proposed.version,
            changed_bids=[b.bid for b in out.changed_beats],
            reason=out.reason,
            runtime_effect=out.runtime_effect,
            contributor_effect=out.contributor_effect,
            risk_effect=out.risk_effect,
        ))
        return await self.transition(project, ProjectPhase.IN_REVIEW)

    # -- approval --------------------------------------------------------------

    async def approve(
        self, project: Project, approved_by: str, accepted_risks: list[str]
    ) -> Project:
        project = await self.ensure_in_review(project)
        pe = project.paper_edit
        if pe is None or not any(b.status != BeatStatus.REJECTED for b in pe.beats):
            raise TaskFailure(
                "approval", "There are no non-rejected beats to approve.",
                "Revise the paper edit before approving.",
            )
        # Canonical rule: approved beats become locked.
        for beat in pe.beats:
            if beat.status != BeatStatus.REJECTED:
                beat.status = BeatStatus.LOCKED
        transcript = await self._read_transcript(project)
        resolve_exact_quotes(project, transcript)
        project.approval = Approval(
            approved_by=approved_by,
            approved_items=["paper_edit", "roster", "structure"],
            accepted_risks=accepted_risks,
            paper_edit_version=pe.version,
        )
        return await self.transition(project, ProjectPhase.APPROVED)

    # -- rebuild + validation ---------------------------------------------------

    async def run_rebuild(self, project: Project) -> Project:
        """Rebuild plan task + deterministic XML rebuild + validation."""
        self.assert_rebuild_allowed(project)
        project = await self.transition(project, ProjectPhase.REBUILDING)
        pe = project.paper_edit
        assert pe is not None

        seg_times = {s.seg_id: s.time_span for s in project.classification}
        locked = [b for b in pe.beats if b.status == BeatStatus.LOCKED]
        context = {
            "locked_beats": [
                {**b.model_dump(mode="json"),
                 "segment_time_spans": {s: seg_times.get(s) for s in b.seg_ids}}
                for b in locked
            ],
            "beat_order": [b.bid for b in locked],
            "source_facts": project.source_audit.model_dump(mode="json"),
            "rebuild_style": "B",
            "rules": (
                "Map every locked beat, in order, to real source clipitems. "
                "in_seconds/out_seconds are source-timeline seconds matching "
                "transcript timecodes. Never invent clipitem ids."
            ),
        }
        try:
            out: RebuildPlanOutput = await self._run_task(
                project, "rebuild_plan",
                ["04_XML_Builder_Spec_and_Audio_Behaviour_V3_2_Efficient.md"],
                context, RebuildPlanOutput,
            )
        except TaskFailure as exc:
            return await self._fail(project, exc.blocker)

        plan = out.plan
        # V1 is single-source: normalise mappings to the uploaded XML.
        xml_input = self._input(project, "xml")
        for m in plan.mappings:
            m.source_file_id = xml_input.file_id
        project.rebuild = plan
        await self._store.save(project)

        output_filename = "sage_rebuild.xml"
        output_path = Path(self._artefacts.path_for(project.meta.id, output_filename))
        try:
            rebuild_sequence(xml_input.stored_path, plan, output_path)
        except RebuildError as exc:
            return await self._fail(project, Blocker(
                check="deterministic_rebuild", why_it_blocks=str(exc),
                what_is_needed="Correct the rebuild plan or source mapping and retry.",
            ))

        project = await self.transition(project, ProjectPhase.VALIDATING)

        rb = ReportBuilder()
        transcript = await self._read_transcript(project)
        check_state_integrity(project, rb)
        if project.paper_edit_history:
            check_locks(project.paper_edit_history[-1], pe, rb,
                        reopened_bids={b.bid for b in pe.beats})
        check_plan_fidelity(pe, plan, rb)
        check_quote_fidelity(pe, transcript, rb)
        check_output_xml(output_path, plan.style, rb)
        report = rb.build()
        project.validation = report

        if report.overall == CheckOutcome.FAIL:
            project.meta.phase = ProjectPhase.FAILED
            return await self._store.save(project)

        import hashlib
        checksum = hashlib.sha256(output_path.read_bytes()).hexdigest()
        project.output = OutputArtefact(xml_path=str(output_path), checksum_sha256=checksum)
        return await self.transition(project, ProjectPhase.COMPLETE)
