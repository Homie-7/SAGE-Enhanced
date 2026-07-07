"""Fixture-driven mock provider.

Enables full end-to-end testing of orchestration, locks, and validation with
zero LLM cost and total determinism. Responses are looked up from a fixture
directory by task name, falling back to a registered in-memory response.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.providers.base import ProviderCapabilities
from app.schemas.tasks import TaskSpec, TaskResult


class MockProvider:
    name = "mock"

    def __init__(self, fixture_dir: Optional[str | Path] = None):
        self.capabilities = ProviderCapabilities(provider="mock")
        self._fixture_dir = Path(fixture_dir) if fixture_dir else None
        self._responses: dict[str, dict] = {}

    def register(self, task_name: str, response: dict) -> None:
        self._responses[task_name] = response

    async def run_task(self, task: TaskSpec) -> TaskResult:
        payload: Optional[dict] = None
        if self._fixture_dir is not None:
            candidate = self._fixture_dir / f"{task.task_name}.json"
            if candidate.exists():
                payload = json.loads(candidate.read_text())
        if payload is None:
            payload = self._responses.get(task.task_name)
        if payload is None:
            return TaskResult(
                task_name=task.task_name,
                provider=self.name,
                raw_text="",
                valid=False,
                error=(
                    f"No mock fixture registered for task '{task.task_name}'. "
                    f"Add one to the fixture directory or register() it."
                ),
            )
        return TaskResult(
            task_name=task.task_name,
            provider=self.name,
            raw_text=json.dumps(payload),
            parsed=payload,
            valid=True,
        )

    def readiness(self) -> tuple[bool, str]:
        ok = self._fixture_dir is not None
        return ok, (f"Mock fixtures at {self._fixture_dir}" if ok
                    else "Mock provider has no fixture directory configured.")
