"""Prompt assembly.

Assembly per task =
    relevant canonical excerpts
  + task template (prompts/tasks/<task>.md)
  + structured state context (serialised from Project, task-scoped)
  + provider overlay (prompts/overlays/<provider>.md, may be empty)
  + output JSON schema (from schemas.tasks)

Canonical files are read verbatim from prompts/canonical and are never
edited per provider. Overlays are small deltas only; if an overlay restates
workflow logic, that is a design violation.

Lock discipline at the prompt level: locked beats are provided as read-only
context, never as editable candidates (see revision task template).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.tasks import TaskSpec


class PromptRepository:
    def __init__(self, prompts_root: str | Path):
        self.root = Path(prompts_root)

    def canonical(self, filename: str) -> str:
        return (self.root / "canonical" / filename).read_text()

    def task_template(self, task_name: str) -> str:
        return (self.root / "tasks" / f"{task_name}.md").read_text()

    def overlay(self, provider: str) -> str:
        p = self.root / "overlays" / f"{provider}.md"
        return p.read_text() if p.exists() else ""


def assemble_task(
    prompts: PromptRepository,
    *,
    task_name: str,
    provider: str,
    canonical_files: list[str],
    state_context: dict,
    output_schema: dict,
    max_output_tokens: int | None = None,
) -> TaskSpec:
    system_parts = [prompts.canonical(f) for f in canonical_files]
    overlay = prompts.overlay(provider)
    if overlay.strip():
        system_parts.append(overlay)
    system_prompt = "\n\n---\n\n".join(system_parts)

    user_prompt = "\n\n".join([
        prompts.task_template(task_name),
        "## Structured project context\n```json\n"
        + json.dumps(state_context, indent=2, default=str)
        + "\n```",
        "## Output requirement\nRespond with a single JSON object valid "
        "against this schema. No prose before or after.\n```json\n"
        + json.dumps(output_schema, indent=2)
        + "\n```",
    ])

    return TaskSpec(
        task_name=task_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_schema=output_schema,
        max_output_tokens=max_output_tokens,
    )
