"""Knowledge graph memory integration."""
from __future__ import annotations

import json
from typing import Any, Optional

from ADAM.knowledge.graph import Entity, get_entity_store
from ADAM.knowledge.relationships import VALID_RELATIONSHIP_TYPES
from ADAM.memory.store import get_memory


class KnowledgeMemory:
    """Persist graph snapshots to Memory Store."""

    def __init__(self) -> None:
        self._memory = get_memory()
        self._store = get_entity_store()

    def record_entity(self, entity: Entity) -> None:
        self._memory.set(
            f"knowledge.entities.{entity.entity_id}",
            json.dumps(entity.to_dict()),
            tags=["knowledge", "entity", entity.type],
        )

    def record_relationship(self, relationship: dict[str, Any]) -> None:
        key = f"knowledge.relationships.{relationship['relationship_id']}"
        self._memory.set(
            key,
            json.dumps(relationship),
            tags=["knowledge", "relationship", relationship["type"]],
        )

    def get_entity_memory(self, entity_id: str) -> Optional[dict[str, Any]]:
        raw = self._memory.get(f"knowledge.entities.{entity_id}")
        if not raw:
            return None
        return json.loads(raw["value"])


# Singleton
_memory: Optional[KnowledgeMemory] = None


def get_knowledge_memory() -> KnowledgeMemory:
    global _memory
    if _memory is None:
        _memory = KnowledgeMemory()
    return _memory


def reset_knowledge_memory() -> None:
    global _memory
    _memory = None
