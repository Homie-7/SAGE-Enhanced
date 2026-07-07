"""Targeted Revision Mode support + lock enforcement.

Canonical rules enforced deterministically here:
  - locked beats stay locked: not replaced, materially shortened, reordered
    relative to other locked beats, or reframed — silently
  - rejected beats do not reappear unless explicitly reopened
  - revisions are deltas over affected beats, never full replans

`diff_paper_edits` is THE gatekeeper: every new paper-edit version produced
by an LLM revision task must pass through it before being accepted into
project state.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.state import Beat, BeatStatus, PaperEdit


class LockViolation(BaseModel):
    bid: str
    kind: str  # locked_removed | locked_modified | locked_reordered | rejected_reintroduced
    detail: str


class PaperEditDiff(BaseModel):
    changed_bids: list[str] = Field(default_factory=list)
    added_bids: list[str] = Field(default_factory=list)
    removed_bids: list[str] = Field(default_factory=list)
    violations: list[LockViolation] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


_LOCK_SENSITIVE_FIELDS = (
    "src", "cid", "func", "exact_quote", "quote_stub",
    "est_duration", "seg_ids",
)


def _beat_fingerprint(beat: Beat) -> dict:
    return {f: getattr(beat, f) for f in _LOCK_SENSITIVE_FIELDS}


def diff_paper_edits(
    previous: PaperEdit,
    proposed: PaperEdit,
    *,
    reopened_bids: set[str] | None = None,
) -> PaperEditDiff:
    """Deterministic diff. `reopened_bids` are locks the user explicitly
    reopened; changes to those are legal and reported as changed, not
    violations."""
    reopened = reopened_bids or set()
    diff = PaperEditDiff()

    prev_by_bid = {b.bid: b for b in previous.beats}
    prop_by_bid = {b.bid: b for b in proposed.beats}

    diff.added_bids = [b for b in prop_by_bid if b not in prev_by_bid]
    diff.removed_bids = [b for b in prev_by_bid if b not in prop_by_bid]
    diff.changed_bids = [
        bid for bid, b in prop_by_bid.items()
        if bid in prev_by_bid
        and _beat_fingerprint(b) != _beat_fingerprint(prev_by_bid[bid])
    ]

    # Locked beats must survive intact unless explicitly reopened.
    prev_locked_order = [b.bid for b in previous.beats
                         if b.status == BeatStatus.LOCKED and b.bid not in reopened]
    for bid in prev_locked_order:
        if bid not in prop_by_bid:
            diff.violations.append(LockViolation(
                bid=bid, kind="locked_removed",
                detail="Locked beat missing from proposed paper edit.",
            ))
        elif bid in diff.changed_bids:
            diff.violations.append(LockViolation(
                bid=bid, kind="locked_modified",
                detail="Locked beat content changed without being reopened.",
            ))
    prop_locked_order = [b.bid for b in proposed.beats if b.bid in prev_locked_order]
    if prop_locked_order != [b for b in prev_locked_order if b in prop_by_bid]:
        diff.violations.append(LockViolation(
            bid=",".join(prev_locked_order), kind="locked_reordered",
            detail="Relative order of locked beats changed without reopening.",
        ))

    # Rejected beats must not reappear as active.
    for bid in previous.rejected_bids - reopened:
        prop = prop_by_bid.get(bid)
        if prop is not None and prop.status != BeatStatus.REJECTED:
            diff.violations.append(LockViolation(
                bid=bid, kind="rejected_reintroduced",
                detail="Rejected beat reintroduced without an explicit request.",
            ))

    return diff
