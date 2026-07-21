"""SQLite implementation of ProjectStore.

Deliberately simple: one table, the Project aggregate stored as a JSON
document. This mirrors how a Postgres JSONB implementation would work, so a
later swap is an implementation change, not a redesign.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.schemas.state import Project

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    phase      TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    document   TEXT NOT NULL
);
"""


class SQLiteProjectStore:
    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def create(self, project: Project) -> Project:
        return await self.save(project)

    async def get(self, project_id: str) -> Optional[Project]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT document FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            return None
        return Project.model_validate_json(row["document"])

    async def save(self, project: Project) -> Project:
        project.meta.updated_at = datetime.now(timezone.utc)
        doc = project.model_dump_json()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, phase, updated_at, document)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    phase = excluded.phase,
                    updated_at = excluded.updated_at,
                    document = excluded.document
                """,
                (
                    project.meta.id,
                    project.meta.name,
                    project.meta.phase.value,
                    project.meta.updated_at.isoformat(),
                    doc,
                ),
            )
        return project

    async def list_projects(self) -> list[Project]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT document FROM projects ORDER BY updated_at DESC"
            ).fetchall()
        return [Project.model_validate_json(r["document"]) for r in rows]

    async def delete(self, project_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))


class DiskArtefactStore:
    """File artefacts on local disk under a per-project directory."""

    def __init__(self, root: str | Path):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def path_for(self, project_id: str, filename: str) -> str:
        d = self._root / project_id
        d.mkdir(parents=True, exist_ok=True)
        return str(d / filename)

    async def write(self, project_id: str, filename: str, data: bytes) -> str:
        path = self.path_for(project_id, filename)
        Path(path).write_bytes(data)
        return path

    async def read(self, project_id: str, filename: str) -> bytes:
        return Path(self.path_for(project_id, filename)).read_bytes()

    async def delete_project(self, project_id: str) -> None:
        shutil.rmtree(self._root / project_id, ignore_errors=True)
