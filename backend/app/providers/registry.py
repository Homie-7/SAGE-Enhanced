"""Provider registry.

Selection rules (non-negotiable):
  - the provider is chosen at project creation and recorded in
    Project.meta.provider,
  - every task run resolves the adapter from THAT recorded value,
  - the registry never falls back silently: if the recorded provider is
    unavailable, the task fails explicitly and the user must change the
    provider deliberately (recorded in meta.provider_history).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.providers.base import ProviderAdapter, ProviderCapabilities
from app.providers.claude import ClaudeProvider
from app.providers.mock import MockProvider
from app.providers.val import VALProvider


class UnknownProviderError(Exception):
    pass


class ProviderRegistry:
    def __init__(self, configs_dir: str | Path, mock_fixture_dir: str | Path | None = None):
        self._configs_dir = Path(configs_dir)
        self._mock_fixture_dir = mock_fixture_dir
        self._factories: dict[str, Callable[[], ProviderAdapter]] = {
            "mock": lambda: MockProvider(self._mock_fixture_dir),
            "claude": lambda: ClaudeProvider(self._load_caps("claude")),
            "val": lambda: VALProvider(self._load_caps("val")),
        }

    def _load_caps(self, name: str) -> ProviderCapabilities:
        return ProviderCapabilities.load(self._configs_dir / f"{name}.json")

    def available(self) -> list[str]:
        return sorted(self._factories)

    def get(self, name: str) -> ProviderAdapter:
        try:
            factory = self._factories[name]
        except KeyError:
            raise UnknownProviderError(
                f"Provider '{name}' is not registered. "
                f"Available: {', '.join(self.available())}."
            )
        return factory()
