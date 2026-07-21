"""VAL adapter — RMIT internal provider (managed-service default).

Design: every transport fact lives in prompts/configs/val.json
(`endpoint` block) and the credential lives server-side in the environment
variable named there (default VAL_API_KEY). Nothing about VAL is hard-coded;
wiring VAL up = fill the config + set the env var. Until both exist, every
call fails precisely and readiness() reports exactly what is missing.

Two API styles are supported, covering the common internal-gateway shapes:
  - "openai_chat"          POST {base_url}/chat/completions
  - "anthropic_messages"   POST {base_url}/messages

Adapters must not contain workflow logic (see base.py).
"""

from __future__ import annotations

import asyncio
import os

import httpx

from app.providers.base import ProviderCapabilities
from app.providers.claude import extract_json
from app.schemas.tasks import TaskSpec, TaskResult, TaskUsage

_STYLES = ("openai_chat", "anthropic_messages")
_ADMIN_HINT = "Contact the SAGE administrator; users never supply API keys."


class VALProvider:
    name = "val"

    def __init__(self, capabilities: ProviderCapabilities):
        self.capabilities = capabilities

    # -- readiness -----------------------------------------------------------

    def _missing(self) -> list[str]:
        ep = self.capabilities.endpoint
        missing: list[str] = []
        if not ep.base_url:
            missing.append("endpoint.base_url in prompts/configs/val.json")
        if ep.api_style not in _STYLES:
            missing.append(
                f"endpoint.api_style in prompts/configs/val.json (one of {_STYLES})")
        if not self._model():
            missing.append("model in prompts/configs/val.json")
        env = ep.auth_env or "VAL_API_KEY"
        if not os.environ.get(env):
            missing.append(f"server-side credential (env {env})")
        return missing

    def readiness(self) -> tuple[bool, str]:
        missing = self._missing()
        if missing:
            return False, "VAL not configured — missing: " + "; ".join(missing)
        ep = self.capabilities.endpoint
        return True, (f"VAL configured: {ep.api_style} at {ep.base_url}, "
                      f"model {self._model()}")

    def _model(self) -> str | None:
        return os.environ.get("VAL_MODEL") or self.capabilities.model

    # -- request shaping -----------------------------------------------------

    def _request(self, task: TaskSpec, max_tokens: int) -> tuple[str, dict, dict]:
        ep = self.capabilities.endpoint
        env = ep.auth_env or "VAL_API_KEY"
        credential = os.environ[env]
        value = f"{ep.auth_scheme} {credential}" if ep.auth_scheme else credential
        headers = {ep.auth_header: value, "Content-Type": "application/json"}

        base = (ep.base_url or "").rstrip("/")
        if ep.api_style == "openai_chat":
            url = f"{base}/chat/completions"
            body = {
                "model": self._model(),
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": task.system_prompt},
                    {"role": "user", "content": task.user_prompt},
                ],
            }
        else:  # anthropic_messages
            url = f"{base}/messages"
            body = {
                "model": self._model(),
                "max_tokens": max_tokens,
                "system": task.system_prompt,
                "messages": [{"role": "user", "content": task.user_prompt}],
            }
        return url, headers, body

    @staticmethod
    def _extract_text(style: str, data: dict) -> str:
        if style == "openai_chat":
            return data["choices"][0]["message"]["content"]
        parts = data.get("content", [])
        return "\n".join(p.get("text", "") for p in parts
                         if isinstance(p, dict) and p.get("type") == "text")

    # -- execution -----------------------------------------------------------

    async def run_task(self, task: TaskSpec) -> TaskResult:
        missing = self._missing()
        if missing:
            return TaskResult(
                task_name=task.task_name, provider=self.name, raw_text="",
                valid=False,
                error=("The VAL provider is not available on this SAGE server "
                       f"({'; '.join(missing)}). {_ADMIN_HINT}"),
            )

        ep = self.capabilities.endpoint
        max_tokens = task.max_output_tokens or self.capabilities.max_output_tokens
        url, headers, body = self._request(task, max_tokens)

        last_exc: Exception | None = None
        for attempt in range(1 + max(0, ep.transport_retries)):
            try:
                async with httpx.AsyncClient(timeout=ep.timeout_seconds) as client:
                    resp = await client.post(url, headers=headers, json=body)
                break
            except httpx.HTTPError as exc:  # transport only — content never retried here
                last_exc = exc
                if attempt < ep.transport_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
        else:
            return TaskResult(
                task_name=task.task_name, provider=self.name, raw_text="",
                valid=False,
                error=(f"VAL transport failure after "
                       f"{1 + ep.transport_retries} attempt(s): {last_exc}. "
                       f"{_ADMIN_HINT}"),
            )

        if resp.status_code == 401 or resp.status_code == 403:
            return TaskResult(
                task_name=task.task_name, provider=self.name, raw_text="",
                valid=False,
                error=(f"VAL rejected the server credential (HTTP {resp.status_code}). "
                       f"{_ADMIN_HINT}"),
            )
        if resp.status_code >= 400:
            return TaskResult(
                task_name=task.task_name, provider=self.name, raw_text="",
                valid=False,
                error=(f"VAL returned HTTP {resp.status_code}: "
                       f"{resp.text[:300]}"),
            )

        try:
            data = resp.json()
            text = self._extract_text(ep.api_style or "", data)
        except Exception as exc:
            return TaskResult(
                task_name=task.task_name, provider=self.name,
                raw_text=resp.text[:2000], valid=False,
                error=f"VAL response could not be read as {ep.api_style}: {exc}",
            )
        parsed = extract_json(text)
        if parsed is None:
            return TaskResult(
                task_name=task.task_name, provider=self.name,
                raw_text=text, valid=False,
                error=(f"Task '{task.task_name}': VAL returned text that is not "
                       "a single JSON object (the repair round will restate the "
                       "schema requirement)."),
            )
        usage_raw = data.get("usage") if isinstance(data, dict) else None
        usage = TaskUsage()
        if isinstance(usage_raw, dict):
            usage = TaskUsage(
                input_tokens=int(usage_raw.get("input_tokens")
                                 or usage_raw.get("prompt_tokens") or 0),
                output_tokens=int(usage_raw.get("output_tokens")
                                  or usage_raw.get("completion_tokens") or 0),
            )
        return TaskResult(
            task_name=task.task_name, provider=self.name,
            raw_text=text, parsed=parsed, valid=True, usage=usage,
        )
