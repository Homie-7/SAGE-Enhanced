"""Provider-agnostic task runner.

Responsibilities:
  - execute a TaskSpec against the project's recorded provider
  - validate the JSON output against the task's Pydantic model
  - on invalid output: one bounded repair round (if the provider's
    capabilities allow), then explicit failure — never a silent retry loop
  - never switch providers on failure (canonical: failures are explicit)
"""

from __future__ import annotations

from typing import Type

from pydantic import BaseModel, ValidationError

from app.providers.base import ProviderAdapter
from app.schemas.tasks import TaskSpec, TaskResult


def _validate(result: TaskResult, output_model: Type[BaseModel]) -> BaseModel | None:
    if not result.valid or result.parsed is None:
        return None
    try:
        return output_model.model_validate(result.parsed)
    except ValidationError as exc:
        result.valid = False
        result.error = (
            f"Task '{result.task_name}' returned JSON that does not satisfy "
            f"{output_model.__name__}: {exc.errors()[:3]}"
        )
        return None


def _repair_spec(task: TaskSpec, failed: TaskResult) -> TaskSpec:
    return TaskSpec(
        task_name=task.task_name,
        system_prompt=task.system_prompt,
        user_prompt=(
            task.user_prompt
            + "\n\n## Repair round\nYour previous response was invalid.\n"
            + f"Problem: {failed.error}\n"
            + "Previous response (do not repeat the mistake):\n"
            + (failed.raw_text[:4000] or "(empty)")
            + "\n\nRespond again with ONLY a single JSON object valid against "
            "the schema above. No prose, no code fences."
        ),
        output_schema=task.output_schema,
        max_output_tokens=task.max_output_tokens,
    )


async def run_validated(
    adapter: ProviderAdapter,
    task: TaskSpec,
    output_model: Type[BaseModel],
) -> tuple[TaskResult, BaseModel | None]:
    """Run a task and validate its output. One bounded repair round if the
    provider's capabilities allow. Returns the raw result plus the validated
    model (or None, with result.error set honestly)."""
    result = await adapter.run_task(task)
    model = _validate(result, output_model)
    if model is not None:
        return result, model

    retry = adapter.capabilities.retry
    if retry.repair_prompt and retry.max_attempts >= 2:
        repair_result = await adapter.run_task(_repair_spec(task, result))
        repair_result.repair_attempted = True
        model = _validate(repair_result, output_model)
        if model is None and repair_result.error is None:
            repair_result.error = result.error
        return repair_result, model

    return result, None
