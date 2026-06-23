"""Model Registry: persist and query model metadata."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import ModelRegistryError


class ModelRegistry:
    """SQLite-backed model registry."""

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
                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id TEXT UNIQUE NOT NULL,
                    provider TEXT NOT NULL,
                    display_name TEXT,
                    local_or_remote TEXT,
                    supports_chat INTEGER DEFAULT 0,
                    supports_vision INTEGER DEFAULT 0,
                    supports_embeddings INTEGER DEFAULT 0,
                    supports_reasoning INTEGER DEFAULT 0,
                    context_window INTEGER DEFAULT 0,
                    availability_status TEXT DEFAULT 'unknown',
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def register(self, model: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO models (
                    model_id, provider, display_name, local_or_remote,
                    supports_chat, supports_vision, supports_embeddings,
                    supports_reasoning, context_window, availability_status,
                    metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    provider=excluded.provider,
                    display_name=excluded.display_name,
                    local_or_remote=excluded.local_or_remote,
                    supports_chat=excluded.supports_chat,
                    supports_vision=excluded.supports_vision,
                    supports_embeddings=excluded.supports_embeddings,
                    supports_reasoning=excluded.supports_reasoning,
                    context_window=excluded.context_window,
                    availability_status=excluded.availability_status,
                    metadata=excluded.metadata,
                    updated_at=excluded.updated_at
                """,
                (
                    model["model_id"],
                    model["provider"],
                    model.get("display_name"),
                    model.get("local_or_remote"),
                    int(model.get("supports_chat", False)),
                    int(model.get("supports_vision", False)),
                    int(model.get("supports_embeddings", False)),
                    int(model.get("supports_reasoning", False)),
                    model.get("context_window", 0),
                    model.get("availability_status", "unknown"),
                    json.dumps(model.get("metadata", {})),
                    now,
                    now,
                ),
            )
        return self.get(model["model_id"])

    def get(self, model_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM models WHERE model_id = ?", (model_id,)).fetchone()
            return dict(row) if row else None

    def list_models(self, provider: Optional[str] = None, status: Optional[str] = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM models"
        params = []
        where = []
        if provider:
            where.append("provider = ?")
            params.append(provider)
        if status:
            where.append("availability_status = ?")
            params.append(status)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def update_status(self, model_id: str, status: str) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                "UPDATE models SET availability_status = ?, updated_at = ? WHERE model_id = ?",
                (status, datetime.utcnow().isoformat(), model_id),
            )
        m = self.get(model_id)
        if not m:
            raise ModelRegistryError(f"Model '{model_id}' not found")
        return m

    def delete(self, model_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM models WHERE model_id = ?", (model_id,))


# Singleton
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def reset_model_registry() -> None:
    global _registry
    _registry = None
