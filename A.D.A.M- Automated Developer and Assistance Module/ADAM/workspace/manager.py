"""Workspace Manager: register, activate, and persist workspace metadata."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import WorkspaceError


class WorkspaceManager:
    """Manage AI workspaces in SQLite."""

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
                CREATE TABLE IF NOT EXISTS workspaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    path TEXT NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def register(self, name: str, path: str, description: str = "", metadata: dict | None = None) -> dict[str, Any]:
        """Register a new workspace."""
        now = datetime.utcnow().isoformat()
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO workspaces (name, path, description, is_active, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, 0, ?, ?, ?)
                    """,
                    (name, path, description, self._serialize(metadata), now, now),
                )
                ws_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise WorkspaceError(f"Workspace '{name}' already exists") from exc
        return self.get(name)

    def set_active(self, name: str) -> dict[str, Any]:
        """Set a workspace as the active one."""
        with self._connect() as conn:
            conn.execute("UPDATE workspaces SET is_active = 0")
            conn.execute("UPDATE workspaces SET is_active = 1, updated_at = ? WHERE name = ?", (datetime.utcnow().isoformat(), name))
        ws = self.get(name)
        if not ws:
            raise WorkspaceError(f"Workspace '{name}' not found")
        return ws

    def get(self, name: str) -> Optional[dict[str, Any]]:
        """Get workspace by name."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM workspaces WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def get_active(self) -> Optional[dict[str, Any]]:
        """Get the currently active workspace."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM workspaces WHERE is_active = 1 LIMIT 1").fetchone()
            return dict(row) if row else None

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all registered workspaces."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM workspaces ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    def update(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Update workspace fields."""
        allowed = {"description", "metadata", "path"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            raise WorkspaceError("No valid fields to update")
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [name]
        with self._connect() as conn:
            conn.execute(f"UPDATE workspaces SET {set_clause} WHERE name = ?", values)
        ws = self.get(name)
        if not ws:
            raise WorkspaceError("Workspace vanished after update")
        return ws

    def delete(self, name: str) -> None:
        """Unregister a workspace."""
        with self._connect() as conn:
            conn.execute("DELETE FROM workspaces WHERE name = ?", (name,))

    @staticmethod
    def _serialize(metadata: dict | None) -> str:
        import json
        return json.dumps(metadata or {})


# Singleton
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager() -> WorkspaceManager:
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
    return _workspace_manager


def reset_workspace_manager() -> None:
    """Reset cached workspace manager (for tests)."""
    global _workspace_manager
    _workspace_manager = None
