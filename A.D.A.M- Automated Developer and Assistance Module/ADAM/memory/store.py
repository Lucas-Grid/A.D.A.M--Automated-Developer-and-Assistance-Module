"""Memory store for ADAM OS."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import MemoryError


class MemoryStore:
    """Key-value memory with optional metadata and tags."""

    def __init__(self) -> None:
        self._db_path = get_settings().db_path
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    kind TEXT DEFAULT 'text',
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id INTEGER NOT NULL,
                    embedding BLOB,
                    FOREIGN KEY(memory_id) REFERENCES memory(id) ON DELETE CASCADE
                )
                """
            )

    def set(self, key: str, value: str, *, kind: str = "text", tags: Optional[list[str]] = None) -> None:
        """Store a memory entry."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory (key, value, kind, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, kind=excluded.kind,
                tags=excluded.tags, updated_at=excluded.updated_at
                """,
                (key, value, kind, ",".join(tags or []), now, now),
            )

    def get(self, key: str) -> Optional[dict]:
        """Retrieve a memory entry by key."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memory WHERE key = ?", (key,)).fetchone()
            if row is None:
                return None
            return dict(row)

    def delete(self, key: str) -> None:
        """Delete a memory entry."""
        with self._connect() as conn:
            conn.execute("DELETE FROM memory WHERE key = ?", (key,))

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Simple keyword search across memory values."""
        sql = "SELECT * FROM memory WHERE value LIKE ? OR tags LIKE ? ORDER BY updated_at DESC LIMIT ?"
        pattern = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(sql, (pattern, pattern, limit)).fetchall()
            return [dict(r) for r in rows]


# Singleton
_memory_store: Optional[MemoryStore] = None


def get_memory() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store


def reset_memory() -> None:
    """Reset cached memory store (for tests)."""
    global _memory_store
    _memory_store = None
