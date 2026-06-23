"""Agent lifecycle management."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.agents.memory import AgentMemory
from ADAM.agents.registry import get_agent_registry
from ADAM.core.exceptions import AgentError
from ADAM.skills.engine import get_skill_engine

logger = logging.getLogger(__name__)


class AgentLifecycle:
    """Manage agent enable/disable/start/stop lifecycle."""

    def __init__(self) -> None:
        self._engine = get_skill_engine()
        from ADAM.ecc.engine import ECC
        self._ecc = ECC()

    async def start(self, agent_id: str, objective: str) -> dict[str, Any]:
        registry = get_agent_registry()
        agent = registry.get(agent_id)
        if not agent:
            raise AgentError(f"Agent '{agent_id}' not found")
        if not agent.get("enabled"):
            raise AgentError(f"Agent '{agent_id}' is disabled")

        result = await self._ecc.run(agent_id=agent_id, objective=objective)
        return result

    def enable(self, agent_id: str) -> dict[str, Any]:
        registry = get_agent_registry()
        agent = registry.get(agent_id)
        if not agent:
            raise AgentError(f"Agent '{agent_id}' not found")
        return registry.update(agent_id, {"enabled": True})

    def disable(self, agent_id: str) -> dict[str, Any]:
        registry = get_agent_registry()
        agent = registry.get(agent_id)
        if not agent:
            raise AgentError(f"Agent '{agent_id}' not found")
        return registry.update(agent_id, {"enabled": False})

    def reset_memory(self, agent_id: str) -> None:
        AgentMemory(agent_id).clear()
