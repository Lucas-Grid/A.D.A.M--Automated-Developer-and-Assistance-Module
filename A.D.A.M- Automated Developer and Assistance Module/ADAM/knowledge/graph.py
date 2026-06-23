"""Knowledge Graph: entity storage and retrieval."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import KnowledgeGraphError

VALID_ENTITY_TYPES = {"project", "workspace", "model", "skill", "automation", "user_goal", "document"}


class Entity:
    """Graph entity."""

    def __init__(self, entity_id: str, type: str, name: str, metadata: Optional[dict[str, Any]] = None, created_at: Optional[str] = None):
        self.entity_id = entity_id
        self.type = type
        self.name = name
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "type": self.type,
            "name": self.name,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class EntityStore:
    """Persist entities in SQLite."""

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
                CREATE TABLE IF NOT EXISTS knowledge_entities (
                    entity_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_relationships (
                    relationship_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add_entity(self, entity: Entity) -> Entity:
        if entity.type not in VALID_ENTITY_TYPES:
            raise KnowledgeGraphError(f"Unsupported entity type: {entity.type}")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_entities (entity_id, type, name, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entity.entity_id,
                    entity.type,
                    entity.name,
                    json.dumps(entity.metadata),
                    entity.created_at,
                ),
            )
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM knowledge_entities WHERE entity_id = ?", (entity_id,)).fetchone()
            if not row:
                return None
            return Entity(
                entity_id=row["entity_id"],
                type=row["type"],
                name=row["name"],
                metadata=json.loads(row["metadata"] or "{}"),
                created_at=row["created_at"],
            )

    def add_relationship(self, source_id: str, target_id: str, rel_type: str, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        relationship_id = f"{source_id}:{rel_type}:{target_id}"
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_relationships (relationship_id, source_id, target_id, type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    relationship_id,
                    source_id,
                    target_id,
                    rel_type,
                    json.dumps(metadata or {}),
                    now,
                ),
            )
        return {
            "relationship_id": relationship_id,
            "source_id": source_id,
            "target_id": target_id,
            "type": rel_type,
            "metadata": metadata or {},
            "created_at": now,
        }

    def get_relationships(self, entity_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_relationships
                WHERE source_id = ? OR target_id = ?
                """,
                (entity_id, entity_id),
            ).fetchall()
            return [dict(r) for r in rows]

    def search(self, query: str, entity_type: Optional[str] = None) -> list[Entity]:
        q = f"%{query.lower()}%"
        sql = "SELECT * FROM knowledge_entities WHERE lower(name) LIKE ? OR lower(entity_id) LIKE ?"
        params = [q, q]
        if entity_type:
            sql += " AND type = ?"
            params.append(entity_type)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [
                Entity(
                    entity_id=r["entity_id"],
                    type=r["type"],
                    name=r["name"],
                    metadata=json.loads(r["metadata"] or "{}"),
                    created_at=r["created_at"],
                )
                for r in rows
            ]


# Singleton
_store: Optional[EntityStore] = None


def get_entity_store() -> EntityStore:
    global _store
    if _store is None:
        _store = EntityStore()
    return _store


def reset_entity_store() -> None:
    global _store
    _store = None
