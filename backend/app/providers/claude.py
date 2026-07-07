"""Claude adapter — development and explicit fallback provider.

Transport only. Model and limits come from prompts/configs/claude.json.
JSON handling: prompt-for-JSON with one bounded repair round (see
orchestration.tasks.runner for the repair loop, which is provider-agnostic).

Credentials are held server-side (ANTHROPIC_API_KEY on the SAGE host); end users never supply keys.
"""

from __future__ import annotations

import json
import os
import re

from app.providers.base import ProviderCapabilities
from app.schemas.tasks import TaskSpec, TaskResult, TaskUsage

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(text: str) -> dict | None:
    """Extract a single JSON object from model text. Tolerates code fences
    and leading/trailing prose; never repairs the JSON itself."""
    candidate = _FENCE.sub("", text).strip()
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = candidate.find("{"), candidate.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(candidate[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


class ClaudeProvider:
    name = "claude"

    def __init__(self, capabilities: ProviderCapabilities):
        self.capabilities = capabilities
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic()
        return self._client

    async def _complete(self, system: str, user: str, max_tokens: int):
        """Single completion round-trip via the Anthropic messages API."""
        client = self._get_client()
        return await client.messages.create(
            model=self.capabilities.model or "claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

    async def run_task(self, task: TaskSpec) -> TaskResult:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return TaskResult(
                task_name=task.task_name,
                provider=self.name,
                raw_text="",
                valid=False,
                error=(
                    "The Claude fallback provider is not configured on this "
                    "SAGE server (missing server-side credential). Contact "
                    "the SAGE administrator; users never supply API keys."
                ),
            )
        max_tokens = task.max_output_tokens or self.capabilities.max_output_tokens
        try:
            response = await self._complete(task.system_prompt, task.user_prompt, max_tokens)
        except Exception as exc:  # transport errors are explicit failures
            return TaskResult(
                task_name=task.task_name, provider=self.name, raw_text="",
                valid=False,
                error=f"Anthropic API call failed: {type(exc).__name__}: {exc}",
            )
        raw = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        parsed = extract_json(raw)
        usage = TaskUsage(
            input_tokens=getattr(response.usage, "input_tokens", 0),
            output_tokens=getattr(response.usage, "output_tokens", 0),
        )
        if parsed is None:
            return TaskResult(
                task_name=task.task_name, provider=self.name, raw_text=raw,
                valid=False, usage=usage,
                error="Response did not contain a parseable JSON object.",
            )
        return TaskResult(
            task_name=task.task_name, provider=self.name, raw_text=raw,
            parsed=parsed, valid=True, usage=usage,
        )
