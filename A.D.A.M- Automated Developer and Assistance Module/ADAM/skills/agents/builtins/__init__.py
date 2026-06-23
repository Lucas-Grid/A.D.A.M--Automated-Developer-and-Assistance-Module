"""Built-in agent configurations for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.agents.registry import get_agent_registry

_BUILTIN_AGENTS: list[dict[str, Any]] = [
    {
        "id": "architect",
        "name": "Architect Agent",
        "role": "architect",
        "description": "Plans and designs system architecture, selects models and skills for objectives.",
        "model_id": None,
        "enabled": True,
        "metadata": {"builtin": True, "role": "architect"},
    },
    {
        "id": "researcher",
        "name": "Research Agent",
        "role": "researcher",
        "description": "Gathers information from knowledge graph, vector store, and external sources.",
        "model_id": None,
        "enabled": True,
        "metadata": {"builtin": True, "role": "researcher"},
    },
    {
        "id": "automation",
        "name": "Automation Agent",
        "role": "automation",
        "description": "Creates and manages automations, workflows, and scheduled tasks.",
        "model_id": None,
        "enabled": True,
        "metadata": {"builtin": True, "role": "automation"},
    },
]


def seed_builtin_agents() -> None:
    """Register built-in agents if they do not already exist."""
    registry = get_agent_registry()
    for agent in _BUILTIN_AGENTS:
        existing = registry.get(agent["id"])
        if existing is None:
            registry.create(agent)
