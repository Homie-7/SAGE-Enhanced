"""Plan-fidelity checks: rebuilt output vs approved paper edit.

Canonical (file 04 beat fidelity rule):
  - each approved/locked beat maps to a real source segment
  - no locked beat dropped
  - rejected beats absent
  - forced substitutes disclosed
Also: exact quotes must be verbatim substrings of the transcript span.
"""

from __future__ import annotations

import re

from app.schemas.state import BeatStatus, PaperEdit, RebuildPlan
from app.validation.report import ReportBuilder


def check_plan_fidelity(paper_edit: PaperEdit, plan: RebuildPlan, rb: ReportBuilder) -> None:
    mapped = [m.bid for m in plan.mappings]
    mapped_set = set(mapped)
    locked = [b.bid for b in paper_edit.beats if b.status == BeatStatus.LOCKED]
    rejected = paper_edit.rejected_bids

    missing = [bid for bid in locked if bid not in mapped_set]
    if missing:
        rb.failed(
            "plan_fidelity:locked_dropped",
            why_it_blocks=f"Locked beats missing from rebuild plan: {missing}.",
            what_is_needed="Regenerate the rebuild plan to include every locked beat.",
        )
    reintroduced = [bid for bid in mapped if bid in rejected]
    if reintroduced:
        rb.failed(
            "plan_fidelity:rejected_present",
            why_it_blocks=f"Rejected beats present in rebuild plan: {reintroduced}.",
            what_is_needed="Remove rejected beats from the plan.",
        )
    locked_in_plan_order = [bid for bid in mapped if bid in set(locked)]
    if locked_in_plan_order != locked:
        rb.failed(
            "plan_fidelity:order",
            why_it_blocks=(
                f"Plan order {locked_in_plan_order} does not match the approved "
                f"paper edit order {locked}."
            ),
            what_is_needed="Regenerate the plan preserving the approved beat order.",
        )
    bad_spans = [m.bid for m in plan.mappings if m.out_seconds <= m.in_seconds]
    if bad_spans:
        rb.failed(
            "plan_fidelity:spans",
            why_it_blocks=f"Mappings with non-positive duration: {bad_spans}.",
            what_is_needed="Each mapping needs out_seconds > in_seconds.",
        )
    if not missing and not reintroduced and locked_in_plan_order == locked and not bad_spans:
        rb.passed("plan_fidelity", "Every locked beat mapped, in order; no rejected beats present.")


_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def check_quote_fidelity(paper_edit: PaperEdit, transcript_text: str, rb: ReportBuilder) -> None:
    """Exact quotes of locked beats must be verbatim transcript content
    (whitespace-normalised; timecodes/speaker labels are stripped upstream)."""
    transcript_norm = _norm(transcript_text)
    problems = []
    unresolved = []
    for beat in paper_edit.beats:
        if beat.status != BeatStatus.LOCKED:
            continue
        if not beat.exact_quote:
            unresolved.append(beat.bid)
            continue
        if _norm(beat.exact_quote) not in transcript_norm:
            problems.append(beat.bid)
    if problems:
        rb.failed(
            "quote_fidelity",
            why_it_blocks=f"Exact quotes not found verbatim in transcript for beats: {problems}.",
            what_is_needed="Re-resolve quotes from segment spans; do not paraphrase source speech.",
        )
    elif unresolved:
        rb.warned("quote_fidelity", f"Locked beats without resolved exact quotes: {unresolved}.")
    else:
        rb.passed("quote_fidelity", "All locked-beat quotes are verbatim transcript content.")
