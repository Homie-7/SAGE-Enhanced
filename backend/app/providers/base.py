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


class ProviderCapabilities(BaseModel):
    provider: str
    model: str | None = None
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
