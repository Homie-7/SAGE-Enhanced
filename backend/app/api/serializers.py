"""API response shaping.

Managed-service rule: provider identity and provider history are recorded in
every project's state for audit/debugging, but they are backend/admin facts.
Standard-mode API responses redact them; admin/dev deployments
(SAGE_ADMIN_MODE=1) see them in full.
"""

from __future__ import annotations

from typing import Any

from app import config
from app.schemas.state import Project

_ADMIN_ONLY_META_FIELDS = ("provider", "provider_history")


def project_out(project: Project) -> dict[str, Any]:
    data = project.model_dump(mode="json")
    if not config.ADMIN_MODE:
        for field in _ADMIN_ONLY_META_FIELDS:
            data["meta"].pop(field, None)
    return data


def projects_out(projects: list[Project]) -> list[dict[str, Any]]:
    return [project_out(p) for p in projects]
