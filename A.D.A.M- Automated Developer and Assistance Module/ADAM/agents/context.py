"""Agent context assembly from existing ADAM systems."""
from __future__ import annotations

from typing import Any, Optional

from ADAM.aiops.context_builder import ContextBuilder
from ADAM.aiops.retrieval import Retriever
from ADAM.aiops.vector_store import VectorStore
from ADAM.automations.history import get_job_history
from ADAM.knowledge.context import get_context_engine
from ADAM.knowledge.graph import get_entity_store
from ADAM.memory.store import get_memory
from ADAM.workspace.manager import get_workspace_manager


class AgentContext:
    """Assemble context packages for agents."""

    def __init__(self, retriever: Optional[Retriever] = None) -> None:
        self._retriever = retriever
        self._memory = get_memory()
        self._history = get_job_history()
        self._context_builder = ContextBuilder(retriever=retriever)

    async def build_for_agent(self, agent_id: str, objective: str, top_k: int = 5) -> dict[str, Any]:
        package: dict[str, Any] = {
            "agent_id": agent_id,
            "objective": objective,
            "graph_context": {},
            "memory_context": [],
            "automation_context": [],
            "vector_context": [],
            "workspace_context": {},
        }

        ws = get_workspace_manager().get_active()
        if ws:
            package["workspace_context"] = ws

        package["memory_context"] = [
            {"key": row["key"], "value": row["value"], "updated_at": row["updated_at"]}
            for row in self._memory.search(objective, limit=10)
        ]

        package["automation_context"] = self._history.list_jobs(workflow_id=None, success=None)[:10]

        if self._retriever:
            package["vector_context"] = await self._retriever.search(objective, top_k=top_k)

        return package
