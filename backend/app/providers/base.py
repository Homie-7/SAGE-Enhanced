"""Provider adapter contract.

A provider absorbs exactly three kinds of difference:
  1. transport/auth (this adapter)
  2. limits and strategies (ProviderCapabilities, loaded from prompts/configs)
  3. small prompt adjustments (overlay file in prompts/overlays)

Adapters must NOT contain workflow logic. If an adapter starts encoding SAGE
editorial behaviour, that is a design violation — the workflow lives once, in
the orchestration engine and canonical prompt files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from app.schemas.tasks import TaskSpec, TaskResult


class ChunkingConfig(BaseModel):
    transcript_chunk_tokens: int = 8000
    overlap_tokens: int = 400


class RetryConfig(BaseModel):
    max_attempts: int = 2
    repair_prompt: bool = True


class EndpointConfig(BaseModel):
    """Transport facts for HTTP providers. All optional so configs without
    endpoints (mock) stay valid; adapters fail precisely when required
    fields are missing."""
    base_url: str | None = None
    api_style: str | None = None  # "openai_chat" | "anthropic_messages"
    auth_env: str | None = None   # env var holding the server-side credential
    auth_header: str = "Authorization"
    auth_scheme: str | None = "Bearer"  # None = raw value in header
    timeout_seconds: float = 120.0
    transport_retries: int = 1  # retries on transport errors only, never on
                                # invalid content (that is the repair round's job)


class ProviderCapabilities(BaseModel):
    provider: str
    model: str | None = None
    endpoint: EndpointConfig = Field(default_factory=EndpointConfig)
    max_context_tokens: int = 32000
    max_output_tokens: int = 4000
    supports_system_prompt: bool = True
    supports_json_schema_mode: bool = False
    json_strategy: str = "prompt_and_repair"  # or "native_schema"
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)

    @classmethod
    def load(cls, config_path: str | Path) -> "ProviderCapabilities":
        return cls.model_validate(json.loads(Path(config_path).read_text()))


class ProviderAdapter(Protocol):
    name: str
    capabilities: ProviderCapabilities

    async def run_task(self, task: TaskSpec) -> TaskResult:
        """Execute one stateless task. Must return a TaskResult whose
        `parsed` is schema-valid JSON or whose `error` explains exactly
        why not (canonical failure rule: no vague language)."""
        ...

    def readiness(self) -> tuple[bool, str]:
        """Cheap, local, no-network answer to: could run_task possibly
        succeed right now? (config + credential presence). Used by the
        operator status endpoint and pre-flight checks."""
        ...
