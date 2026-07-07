"""Dependency wiring for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from app import config
from app.orchestration.engine import OrchestrationEngine
from app.providers.registry import ProviderRegistry
from app.storage.sqlite_store import DiskArtefactStore, SQLiteProjectStore


@lru_cache
def get_store() -> SQLiteProjectStore:
    return SQLiteProjectStore(config.DB_PATH)


@lru_cache
def get_artefacts() -> DiskArtefactStore:
    return DiskArtefactStore(config.ARTEFACT_ROOT)


@lru_cache
def get_registry() -> ProviderRegistry:
    return ProviderRegistry(
        configs_dir=config.PROVIDER_CONFIGS,
        mock_fixture_dir=config.MOCK_FIXTURES,
    )


@lru_cache
def get_engine() -> OrchestrationEngine:
    return OrchestrationEngine(
        get_store(), get_registry(), artefacts=get_artefacts(),
        prompts_root=config.PROMPTS_ROOT,
    )
