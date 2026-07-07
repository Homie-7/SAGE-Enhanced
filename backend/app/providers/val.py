"""VAL adapter — RMIT internal provider. CLEAN STUB.

No programmatic API facts are confirmed yet. This stub exists so that:
  - the adapter surface is fixed now,
  - prompts/configs/val.json captures assumptions in one editable place,
  - wiring VAL later is an isolated task that touches only this file and
    its config.

Do not add speculative endpoints or auth flows here until VAL access is
confirmed. The stub fails explicitly and honestly (canonical failure rule).
"""

from __future__ import annotations

from app.providers.base import ProviderCapabilities
from app.schemas.tasks import TaskSpec, TaskResult


class VALProvider:
    name = "val"

    def __init__(self, capabilities: ProviderCapabilities):
        self.capabilities = capabilities

    async def run_task(self, task: TaskSpec) -> TaskResult:
        return TaskResult(
            task_name=task.task_name,
            provider=self.name,
            raw_text="",
            valid=False,
            error=(
                "The VAL provider is not yet available on this SAGE server. "
                "Contact the SAGE administrator. (Admin note: wire "
                "providers/val.py + prompts/configs/val.json, or change this "
                "project's provider explicitly in admin mode.)"
            ),
        )
