"""Workflow system: data-driven step sequences."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import AutomationError
from ADAM.skills.engine import get_skill_engine


class Workflow:
    """Data-driven workflow definition."""

    def __init__(self, workflow_id: str, steps: list[str], metadata: Optional[dict[str, Any]] = None):
        self.workflow_id = workflow_id
        self.steps = steps
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "steps": self.steps,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Workflow:
        return cls(
            workflow_id=data["workflow_id"],
            steps=data["steps"],
            metadata=data.get("metadata"),
        )


class WorkflowStore:
    """Persist workflows in SQLite."""

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
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    steps TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, workflow: Workflow) -> Workflow:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflows (workflow_id, steps, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    steps=excluded.steps,
                    metadata=excluded.metadata,
                    updated_at=excluded.updated_at
                """,
                (
                    workflow.workflow_id,
                    json.dumps(workflow.steps),
                    json.dumps(workflow.metadata),
                    now,
                    now,
                ),
            )
        return self.get(workflow.workflow_id)

    def get(self, workflow_id: str) -> Optional[Workflow]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
            if not row:
                return None
            return Workflow.from_dict(
                {
                    "workflow_id": row["workflow_id"],
                    "steps": json.loads(row["steps"]),
                    "metadata": json.loads(row["metadata"] or "{}"),
                }
            )

    def list_workflows(self) -> list[Workflow]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM workflows ORDER BY updated_at DESC").fetchall()
            return [
                Workflow.from_dict(
                    {
                        "workflow_id": r["workflow_id"],
                        "steps": json.loads(r["steps"]),
                        "metadata": json.loads(r["metadata"] or "{}"),
                    }
                )
                for r in rows
            ]

    def delete(self, workflow_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM workflows WHERE workflow_id = ?", (workflow_id,))


# Singleton
_store: Optional[WorkflowStore] = None


def get_workflow_store() -> WorkflowStore:
    global _store
    if _store is None:
        _store = WorkflowStore()
    return _store


def reset_workflow_store() -> None:
    global _store
    _store = None
