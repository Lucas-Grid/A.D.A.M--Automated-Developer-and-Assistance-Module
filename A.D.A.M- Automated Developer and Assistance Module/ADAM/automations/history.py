"""Job history: persist execution outcomes."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import AutomationError


class JobHistory:
    """SQLite-backed job history."""

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
                CREATE TABLE IF NOT EXISTS job_history (
                    job_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration REAL,
                    success INTEGER DEFAULT 0,
                    error_message TEXT,
                    output_summary TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def record(self, record: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO job_history (
                    job_id, workflow_id, start_time, end_time, duration,
                    success, error_message, output_summary, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["job_id"],
                    record["workflow_id"],
                    record["start_time"],
                    record.get("end_time"),
                    record.get("duration"),
                    1 if record.get("success") else 0,
                    record.get("error_message"),
                    json.dumps(record.get("output_summary", {})),
                    now,
                ),
            )
        return self.get(record["job_id"])

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM job_history WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def list_jobs(self, workflow_id: Optional[str] = None, success: Optional[bool] = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM job_history"
        params = []
        where = []
        if workflow_id:
            where.append("workflow_id = ?")
            params.append(workflow_id)
        if success is not None:
            where.append("success = ?")
            params.append(1 if success else 0)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]


# Singleton
_history: Optional[JobHistory] = None


def get_job_history() -> JobHistory:
    global _history
    if _history is None:
        _history = JobHistory()
    return _history


def reset_job_history() -> None:
    global _history
    _history = None
