"""Agent Registry: persist and query agent definitions."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from ADAM.agents.agent import Agent
from ADAM.core.config import get_settings
from ADAM.core.exceptions import AgentError


class AgentRegistry:
    """SQLite-backed agent registry."""

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
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    description TEXT,
                    model_id TEXT,
                    enabled INTEGER DEFAULT 1,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, agent: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow().isoformat()
        entity = Agent(
            id=agent["id"],
            name=agent["name"],
            role=agent["role"],
            description=agent.get("description", ""),
            model_id=agent.get("model_id"),
            enabled=bool(agent.get("enabled", True)),
            metadata=agent.get("metadata", {}),
            created_at=now,
            updated_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agents (
                    id, name, role, description, model_id, enabled, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.name,
                    entity.role,
                    entity.description,
                    entity.model_id,
                    1 if entity.enabled else 0,
                    json.dumps(entity.metadata),
                    entity.created_at,
                    entity.updated_at,
                ),
            )
        return self.get(entity.id)

    def get(self, agent_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
            return dict(row) if row else None

    def list_agents(self, enabled: bool | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM agents"
        params = []
        where = []
        if enabled is not None:
            where.append("enabled = ?")
            params.append(1 if enabled else 0)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def update(self, agent_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get(agent_id)
        if not current:
            raise AgentError(f"Agent '{agent_id}' not found")

        allowed = {"name", "role", "description", "model_id", "enabled", "metadata"}
        filtered = {k: v for k, v in updates.items() if k in allowed}
        if not filtered:
            return current

        if "metadata" in filtered:
            filtered["metadata"] = json.dumps(filtered["metadata"])
        if "enabled" in filtered:
            filtered["enabled"] = 1 if filtered["enabled"] else 0

        filtered["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        params = list(filtered.values())
        params.append(agent_id)

        with self._connect() as conn:
            conn.execute(
                f"UPDATE agents SET {set_clause} WHERE id = ?",
                params,
            )
        return self.get(agent_id)

    def delete(self, agent_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))


# Singleton
_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def reset_agent_registry() -> None:
    global _registry
    _registry = None
