"""Lock and rejection enforcement as validation checks.

Thin wrapper over orchestration.revision.diff_paper_edits so the same
deterministic diff guards both the revision flow and final validation.
"""

from __future__ import annotations

from app.orchestration.revision import diff_paper_edits
from app.schemas.state import PaperEdit
from app.validation.report import ReportBuilder


def check_locks(
    previous: PaperEdit,
    proposed: PaperEdit,
    rb: ReportBuilder,
    *,
    reopened_bids: set[str] | None = None,
) -> None:
    diff = diff_paper_edits(previous, proposed, reopened_bids=reopened_bids)
    if diff.ok:
        rb.passed("lock_enforcement", "Locked and rejected beats preserved.")
        return
    for v in diff.violations:
        rb.failed(
            f"lock_enforcement:{v.kind}",
            why_it_blocks=f"Beat {v.bid}: {v.detail}",
            what_is_needed=(
                "Reopen the beat explicitly, or regenerate the revision "
                "without touching locked/rejected beats."
            ),
        )
