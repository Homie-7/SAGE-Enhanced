"""Storage abstraction.

The rest of the application depends only on ProjectStore. SQLite is the V1
implementation; a Postgres implementation can be added later by implementing
this same interface — no callers change.

Rules for implementations:
  - store the Project aggregate as a whole (JSON document semantics)
  - persist atomically per save
  - never mutate a Project the caller still holds
"""

from __future__ import annotations

from typing import Optional, Protocol

from app.schemas.state import Project


class ProjectStore(Protocol):
    async def create(self, project: Project) -> Project: ...

    async def get(self, project_id: str) -> Optional[Project]: ...

    async def save(self, project: Project) -> Project: ...

    async def list_projects(self) -> list[Project]: ...

    async def delete(self, project_id: str) -> None: ...


class ArtefactStore(Protocol):
    """Binary/file artefacts (uploaded XML, transcripts, rebuilt output)."""

    def path_for(self, project_id: str, filename: str) -> str: ...

    async def write(self, project_id: str, filename: str, data: bytes) -> str: ...

    async def read(self, project_id: str, filename: str) -> bytes: ...

    async def delete_project(self, project_id: str) -> None: ...
