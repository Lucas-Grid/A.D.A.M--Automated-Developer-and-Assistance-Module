"""Context engine: build context packages for AI reasoning."""
from __future__ import annotations

from typing import Any, Optional

from ADAM.automations.history import get_job_history
from ADAM.knowledge.graph import get_entity_store
from ADAM.knowledge.queries import get_query_engine
from ADAM.memory.store import get_memory


class ContextEngine:
    """Build rich context packages around a focal entity."""

    def __init__(self) -> None:
        self._store = get_entity_store()
        self._queries = get_query_engine()
        self._memory = get_memory()
        self._history = get_job_history()

    def build_context(self, entity_id: str, depth: int = 2) -> dict[str, Any]:
        entity = self._store.get_entity(entity_id)
        if not entity:
            return {"error": f"Entity '{entity_id}' not found"}

        context: dict[str, Any] = {
            "entity": entity.to_dict(),
            "related": [],
            "recent_history": [],
            "memory_entries": [],
        }

        for rel in self._store.get_relationships(entity_id):
            neighbor_id = rel["target_id"] if rel["source_id"] == entity_id else rel["source_id"]
            neighbor = self._store.get_entity(neighbor_id)
            if neighbor:
                context["related"].append(
                    {
                        "entity": neighbor.to_dict(),
                        "relationship": rel,
                        "direction": "outgoing" if rel["source_id"] == entity_id else "incoming",
                    }
                )

        context["recent_history"] = self._history.list_jobs(workflow_id=entity_id, success=None)[:10]

        prefix = f"knowledge.entities.{entity_id}."
        context["memory_entries"] = [
            {"key": k, "value": v["value"], "tags": v.get("tags", [])}
            for k, v in self._memory.search(prefix)
        ]

        return context


# Singleton
_engine: Optional[ContextEngine] = None


def get_context_engine() -> ContextEngine:
    global _engine
    if _engine is None:
        _engine = ContextEngine()
    return _engine


def reset_context_engine() -> None:
    global _engine
    _engine = None
