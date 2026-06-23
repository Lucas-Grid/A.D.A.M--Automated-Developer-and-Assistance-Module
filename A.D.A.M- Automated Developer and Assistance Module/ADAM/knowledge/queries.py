"""Knowledge graph query engine."""
from __future__ import annotations

from typing import Any, Optional

from ADAM.knowledge.graph import Entity, get_entity_store
from ADAM.knowledge.relationships import VALID_RELATIONSHIP_TYPES


class KnowledgeQueryEngine:
    """High-level queries over the knowledge graph."""

    def __init__(self) -> None:
        self._store = get_entity_store()

    def get_entity(self, entity_id: str) -> Optional[dict[str, Any]]:
        entity = self._store.get_entity(entity_id)
        return entity.to_dict() if entity else None

    def neighbors(self, entity_id: str) -> list[dict[str, Any]]:
        relationships = self._store.get_relationships(entity_id)
        result = []
        for rel in relationships:
            neighbor_id = rel["target_id"] if rel["source_id"] == entity_id else rel["source_id"]
            entity = self._store.get_entity(neighbor_id)
            if entity:
                result.append(
                    {
                        "entity": entity.to_dict(),
                        "relationship": rel,
                        "direction": "outgoing" if rel["source_id"] == entity_id else "incoming",
                    }
                )
        return result

    def related_entities(self, entity_id: str, rel_type: Optional[str] = None) -> list[dict[str, Any]]:
        relationships = self._store.get_relationships(entity_id)
        result = []
        for rel in relationships:
            if rel_type and rel["type"] != rel_type:
                continue
            neighbor_id = rel["target_id"] if rel["source_id"] == entity_id else rel["source_id"]
            entity = self._store.get_entity(neighbor_id)
            if entity:
                result.append(
                    {
                        "entity": entity.to_dict(),
                        "relationship": rel,
                        "direction": "outgoing" if rel["source_id"] == entity_id else "incoming",
                    }
                )
        return result

    def search(self, query: str, entity_type: Optional[str] = None) -> list[dict[str, Any]]:
        entities = self._store.search(query, entity_type=entity_type)
        return [e.to_dict() for e in entities]

    def relationship_path(self, source_id: str, target_id: str, max_depth: int = 3) -> list[dict[str, Any]]:
        visited = {source_id}
        queue: list[tuple[str, list[dict[str, Any]]]] = [(source_id, [])]
        while queue:
            current, path = queue.pop(0)
            if current == target_id:
                return path
            if len(path) >= max_depth:
                continue
            for rel in self._store.get_relationships(current):
                neighbor_id = rel["target_id"] if rel["source_id"] == current else rel["source_id"]
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                edge = {
                    "source_id": current,
                    "target_id": neighbor_id,
                    "relationship": rel,
                    "direction": "outgoing" if rel["source_id"] == current else "incoming",
                }
                queue.append((neighbor_id, path + [edge]))
        return []


# Singleton
_engine: Optional[KnowledgeQueryEngine] = None


def get_query_engine() -> KnowledgeQueryEngine:
    global _engine
    if _engine is None:
        _engine = KnowledgeQueryEngine()
    return _engine


def reset_query_engine() -> None:
    global _engine
    _engine = None
