"""Context builder: assemble unified context package for AI reasoning."""
from __future__ import annotations

import logging
from typing import Any, Optional

from ADAM.aiops.retrieval import Retriever
from ADAM.automations.history import get_job_history
from ADAM.knowledge.context import get_context_engine
from ADAM.knowledge.graph import get_entity_store
from ADAM.memory.store import get_memory

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build rich context packages from multiple sources."""

    def __init__(self, retriever: Optional[Retriever] = None) -> None:
        self._retriever = retriever
        self._memory = get_memory()
        self._history = get_job_history()

    async def build(self, query: str, entity_id: Optional[str] = None, top_k: int = 5) -> dict[str, Any]:
        package: dict[str, Any] = {
            "query": query,
            "graph_context": {},
            "memory_context": [],
            "automation_context": [],
            "vector_context": [],
        }

        if entity_id:
            ctx = get_context_engine().build_context(entity_id)
            package["graph_context"] = ctx

        package["memory_context"] = [
            {"key": row["key"], "value": row["value"], "updated_at": row["updated_at"]}
            for row in self._memory.search(query, limit=10)
        ]

        package["automation_context"] = self._history.list_jobs(workflow_id=entity_id, success=None)[:10]

        if self._retriever:
            vector_results = await self._retriever.search(query, top_k=top_k)
            package["vector_context"] = vector_results

        return package
