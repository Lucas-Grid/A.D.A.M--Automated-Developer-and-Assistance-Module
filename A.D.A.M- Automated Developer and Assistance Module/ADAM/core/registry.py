"""Project Registry: CRUD for AI projects managed by ADAM."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ProjectRegistryError


class ProjectRegistry:
    """Manage AI project records in SQLite."""

    def __init__(self) -> None:
        self._db_path = get_settings().db_path
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    path TEXT NOT NULL,
                    description TEXT,
                    model_tag TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, name: str, path: str, description: str = "", model_tag: str = "") -> dict[str, Any]:
        """Register a new AI project."""
        now = datetime.utcnow().isoformat()
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO projects (name, path, description, model_tag, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, path, description, model_tag, "{}", now, now),
                )
                project_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ProjectRegistryError(f"Project '{name}' already exists") from exc

        return {"id": project_id, "name": name, "path": path, "description": description, "model_tag": model_tag}

    def get(self, name: str) -> Optional[dict[str, Any]]:
        """Fetch a project by name."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        """List all registered projects."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    def update(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Update project fields by name."""
        allowed = {"description", "model_tag", "path", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            raise ProjectRegistryError("No valid fields to update")

        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [name]

        with self._connect() as conn:
            conn.execute(f"UPDATE projects SET {set_clause} WHERE name = ?", values)

        project = self.get(name)
        if project is None:
            raise ProjectRegistryError("Project vanished after update")
        return project

    def delete(self, name: str) -> None:
        """Remove a project registration."""
        with self._connect() as conn:
            conn.execute("DELETE FROM projects WHERE name = ?", (name,))


# Singleton
_project_registry: Optional[ProjectRegistry] = None


def get_project_registry() -> ProjectRegistry:
    global _project_registry
    if _project_registry is None:
        _project_registry = ProjectRegistry()
    return _project_registry


def reset_project_registry() -> None:
    """Reset cached project registry (for tests)."""
    global _project_registry
    _project_registry = None
