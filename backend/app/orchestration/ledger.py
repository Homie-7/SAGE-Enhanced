"""Decision ledger management.

Canonical rule: treat approved items as settled. Do not reopen or re-explain
them unless the user asks, a new request conflicts, or a technical blocker
forces review. The helpers here centralise that discipline so tasks cannot
casually overwrite settled decisions.
"""

from __future__ import annotations

from app.schemas.state import DecisionLedger, FieldOrigin, Project


class SettledDecisionConflict(Exception):
    def __init__(self, key: str, settled: str, incoming: str):
        super().__init__(
            f"Decision '{key}' is settled as '{settled}' but an update to "
            f"'{incoming}' was attempted. Settled decisions are only reopened "
            f"explicitly."
        )
        self.key, self.settled, self.incoming = key, settled, incoming


def settle_from_setup(project: Project) -> DecisionLedger:
    """Seed the ledger from the quick-setup capture set (user/inferred
    values only; unset fields remain open for inference)."""
    ledger = project.ledger
    for key, field in project.setup.__dict__.items():
        if hasattr(field, "value") and field.value:
            ledger.settle(key, field.value, field.origin)
    return ledger


def settle(
    ledger: DecisionLedger,
    key: str,
    value: str,
    origin: FieldOrigin,
    *,
    reopen: bool = False,
) -> None:
    existing = ledger.get(key)
    if existing is not None and existing != value and not reopen:
        raise SettledDecisionConflict(key, existing, value)
    ledger.settle(key, value, origin)
