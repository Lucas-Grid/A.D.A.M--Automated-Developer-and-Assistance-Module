"""Memory layer: short-term session context + long-term SQLite store.

Design draws on patterns from the reference projects:
* jarvis-ai-assistant (skyfireitdiy) -- layered, tag-based memory
  (short / project / global) with NO vector computation, kept lightweight.
* OpenJarvis -- memory as one of five composable primitives; offline-first.

We keep the store dependency-free (plain SQLite) so the assistant runs anywhere.
The previous simple key/value API is preserved; we add scopes + tags on top.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Optional

SCOPES = ("short", "project", "global")


class Memory:
    def __init__(self, db_path: str = "jarvis_memory.db") -> None:
        self.db_path = db_path
        self._connect()
        self._ensure()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def _ensure(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'global',
                value TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT,
                updated_at TEXT,
                PRIMARY KEY (scope, key)
            )
            """
        )
        self._conn.commit()

    # --- store / recall ------------------------------------------------------
    def store(
        self, key: str, value: str, scope: str = "global", tags: Optional[list[str]] = None
    ) -> None:
        from datetime import datetime

        now = datetime.utcnow().isoformat()
        tag_str = ",".join(tags or [])
        self._conn.execute(
            "INSERT INTO memory(scope, key, value, tags, created_at, updated_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(scope, key) DO UPDATE SET value=excluded.value, tags=excluded.tags, "
            "updated_at=excluded.updated_at",
            (scope, key, value, tag_str, now, now),
        )
        self._conn.commit()

    def recall(self, key: str, scope: Optional[str] = None) -> Optional[str]:
        if scope:
            row = self._conn.execute(
                "SELECT value FROM memory WHERE scope=? AND key=?", (scope, key)
            ).fetchone()
        else:
            # most specific scope wins: short > project > global
            row = self._conn.execute(
                "SELECT value FROM memory WHERE key=? ORDER BY "
                "CASE scope WHEN 'short' THEN 0 WHEN 'project' THEN 1 ELSE 2 END LIMIT 1",
                (key,),
            ).fetchone()
        return row["value"] if row else None

    def search(self, term: str, limit: int = 10, scope: Optional[str] = None) -> list[tuple[str, str, str]]:
        like = f"%{term}%"
        if scope:
            rows = self._conn.execute(
                "SELECT scope, key, value FROM memory WHERE scope=? AND (key LIKE ? OR value LIKE ? OR tags LIKE ?) "
                "ORDER BY updated_at DESC LIMIT ?",
                (scope, like, like, like, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT scope, key, value FROM memory WHERE key LIKE ? OR value LIKE ? OR tags LIKE ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (like, like, like, limit),
            ).fetchall()
        return [(r["scope"], r["key"], r["value"]) for r in rows]

    def all(self, limit: int = 100, scope: Optional[str] = None) -> list[tuple[str, str, str]]:
        if scope:
            rows = self._conn.execute(
                "SELECT scope, key, value FROM memory WHERE scope=? ORDER BY updated_at DESC LIMIT ?",
                (scope, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT scope, key, value FROM memory ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [(r["scope"], r["key"], r["value"]) for r in rows]

    def delete(self, key: str, scope: Optional[str] = None) -> bool:
        if scope:
            cur = self._conn.execute("DELETE FROM memory WHERE scope=? AND key=?", (scope, key))
        else:
            cur = self._conn.execute("DELETE FROM memory WHERE key=?", (key,))
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()


class ShortTermMemory:
    """Rolling window of recent turns (the prompt context)."""

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self.turns: list[dict] = []

    def add(self, role: str, content: str, tool: Optional[str] = None) -> None:
        self.turns.append({"role": role, "content": content, "tool": tool})
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def snapshot(self) -> list[dict]:
        return list(self.turns)

    def clear(self) -> None:
        self.turns.clear()


class TaskList:
    """Side-channel task tracking (jarvis-ai-assistant pattern).

    Sub-tasks live here so they don't pollute the main agent's conversation
    context. The orchestrator optionally uses this to record planned steps.
    """

    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, title: str, status: str = "pending") -> int:
        self.items.append({"id": len(self.items) + 1, "title": title, "status": status})
        return self.items[-1]["id"]

    def complete(self, item_id: int) -> None:
        for it in self.items:
            if it["id"] == item_id:
                it["status"] = "done"

    def pending(self) -> list[dict]:
        return [it for it in self.items if it["status"] != "done"]

    def snapshot(self) -> list[dict]:
        return list(self.items)


class Telemetry:
    """Lightweight cost/latency tracker (OpenJarvis-style first-class telemetry).

    No external deps; records per-step latency and a rough token/$ estimate so
    the assistant can report what a turn cost. Swap in real GPU-watt/$ hooks later.
    """

    def __init__(self) -> None:
        self.steps: list[dict] = []
        self.total_tokens = 0
        self.total_ms = 0.0

    def record(self, tool: str, ms: float, tokens: int = 0) -> None:
        self.steps.append({"tool": tool, "ms": round(ms, 1), "tokens": tokens})
        self.total_ms += ms
        self.total_tokens += tokens

    def summary(self) -> dict:
        return {
            "steps": len(self.steps),
            "total_ms": round(self.total_ms, 1),
            "total_tokens": self.total_tokens,
        }
