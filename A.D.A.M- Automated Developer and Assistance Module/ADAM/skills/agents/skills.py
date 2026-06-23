"""Agent skills for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.agents.agent import Agent
from ADAM.agents.lifecycle import AgentLifecycle
from ADAM.agents.planner import Planner
from ADAM.agents.registry import get_agent_registry
from ADAM.core.exceptions import AgentError
from ADAM.skills.base import BaseSkill
from ADAM.skills.engine import get_skill_engine


class AgentCreateSkill(BaseSkill):
    name = "agent.create"
    description = "Create a new agent"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        registry = get_agent_registry()
        agent = {
            "id": params["id"],
            "name": params["name"],
            "role": params["role"],
            "description": params.get("description", ""),
            "model_id": params.get("model_id"),
            "enabled": params.get("enabled", True),
            "metadata": params.get("metadata", {}),
        }
        created = registry.create(agent)
        return {"agent": created}


class AgentListSkill(BaseSkill):
    name = "agent.list"
    description = "List registered agents"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        registry = get_agent_registry()
        enabled = params.get("enabled")
        agents = registry.list_agents(enabled=enabled)
        return {"agents": agents}


class AgentEnableSkill(BaseSkill):
    name = "agent.enable"
    description = "Enable an agent"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        lifecycle = AgentLifecycle()
        agent = lifecycle.enable(params["id"])
        return {"agent": agent}


class AgentDisableSkill(BaseSkill):
    name = "agent.disable"
    description = "Disable an agent"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        lifecycle = AgentLifecycle()
        agent = lifecycle.disable(params["id"])
        return {"agent": agent}


class AgentRunSkill(BaseSkill):
    name = "agent.run"
    description = "Run an agent against an objective"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        agent_id = params["id"]
        objective = params["objective"]
        lifecycle = AgentLifecycle()
        result = await lifecycle.start(agent_id=agent_id, objective=objective)
        return result
