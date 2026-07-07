"""ValidationReport builder — the canonical failure rule in code.

Every failure is a structured blocker: {check, why_it_blocks, what_is_needed}.
No vague language. The overall outcome is FAIL if any check fails, WARN if
any check warns, PASS otherwise.
"""

from __future__ import annotations

from app.schemas.state import Blocker, CheckOutcome, ValidationCheck, ValidationReport


class ReportBuilder:
    def __init__(self) -> None:
        self._checks: list[ValidationCheck] = []
        self._blockers: list[Blocker] = []

    def passed(self, name: str, detail: str | None = None) -> None:
        self._checks.append(ValidationCheck(name=name, outcome=CheckOutcome.PASS, detail=detail))

    def warned(self, name: str, detail: str) -> None:
        self._checks.append(ValidationCheck(name=name, outcome=CheckOutcome.WARN, detail=detail))

    def failed(self, name: str, why_it_blocks: str, what_is_needed: str) -> None:
        self._checks.append(ValidationCheck(name=name, outcome=CheckOutcome.FAIL, detail=why_it_blocks))
        self._blockers.append(Blocker(check=name, why_it_blocks=why_it_blocks, what_is_needed=what_is_needed))

    def build(self) -> ValidationReport:
        outcomes = {c.outcome for c in self._checks}
        overall = (
            CheckOutcome.FAIL if CheckOutcome.FAIL in outcomes
            else CheckOutcome.WARN if CheckOutcome.WARN in outcomes
            else CheckOutcome.PASS
        )
        return ValidationReport(checks=self._checks, blockers=self._blockers, overall=overall)
