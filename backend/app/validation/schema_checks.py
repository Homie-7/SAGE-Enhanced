"""Schema and state validity checks (deterministic)."""

from __future__ import annotations

from app.schemas.state import Project
from app.validation.report import ReportBuilder


def check_state_integrity(project: Project, rb: ReportBuilder) -> None:
    """Referential integrity across the aggregate: beat CIDs exist in the
    roster, beat seg_ids exist in classification, inputs have checksums."""
    problems: list[str] = []

    for f in project.inputs:
        if not f.checksum_sha256:
            problems.append(f"Input '{f.filename}' has no checksum.")

    cids = {c.cid for c in project.roster}
    seg_ids = {s.seg_id for s in project.classification}
    if project.paper_edit is not None:
        for beat in project.paper_edit.beats:
            if beat.cid is not None and beat.cid not in cids:
                problems.append(f"Beat {beat.bid} references unknown contributor '{beat.cid}'.")
            for s in beat.seg_ids:
                if s not in seg_ids:
                    problems.append(f"Beat {beat.bid} references unknown segment '{s}'.")

    if project.rebuild is not None and project.paper_edit is not None:
        bids = {b.bid for b in project.paper_edit.beats}
        for m in project.rebuild.mappings:
            if m.bid not in bids:
                problems.append(f"Rebuild mapping references unknown beat '{m.bid}'.")

    if problems:
        rb.failed(
            "state_integrity",
            why_it_blocks="; ".join(problems),
            what_is_needed="Repair the referenced state (re-run the affected phase).",
        )
    else:
        rb.passed("state_integrity", "Roster, segments, beats, and mappings are referentially consistent.")
