"""Automation Registry: persist and query automation definitions."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import AutomationError


class AutomationRegistry:
    """SQLite-backed automation registry."""

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
                CREATE TABLE IF NOT EXISTS automations (
                    automation_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    enabled INTEGER DEFAULT 1,
                    trigger_type TEXT NOT NULL,
                    trigger_config TEXT,
                    workflow_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, automation: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO automations (
                    automation_id, name, description, enabled,
                    trigger_type, trigger_config, workflow_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    automation["automation_id"],
                    automation["name"],
                    automation.get("description"),
                    1 if automation.get("enabled", True) else 0,
                    automation["trigger_type"],
                    json.dumps(automation.get("trigger_config", {})),
                    automation["workflow_id"],
                    now,
                    now,
                ),
            )
        return self.get(automation["automation_id"])

    def get(self, automation_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM automations WHERE automation_id = ?", (automation_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_automations(self, trigger_type: Optional[str] = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM automations"
        params = []
        where = []
        if trigger_type:
            where.append("trigger_type = ?")
            params.append(trigger_type)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def update(self, automation_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(automation_id)
        if not current:
            raise AutomationError(f"Automation '{automation_id}' not found")

        allowed = {"name", "description", "enabled", "trigger_type", "trigger_config", "workflow_id"}
        filtered = {k: v for k, v in updates.items() if k in allowed}

        if not filtered:
            return current

        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        params = list(filtered.values())
        params.append(datetime.utcnow().isoformat())
        params.append(automation_id)

        with self._connect() as conn:
            conn.execute(
                f"UPDATE automations SET {set_clause}, updated_at = ? WHERE automation_id = ?",
                params,
            )
        return self.get(automation_id)

    def delete(self, automation_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM automations WHERE automation_id = ?", (automation_id,))


# Singleton
_registry: Optional[AutomationRegistry] = None


def get_automation_registry() -> AutomationRegistry:
    global _registry
    if _registry is None:
        _registry = AutomationRegistry()
    return _registry


def reset_automation_registry() -> None:
    global _registry
    _registry = None
