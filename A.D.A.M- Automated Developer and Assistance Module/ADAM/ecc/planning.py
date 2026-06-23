"""ECC planning: produce goals, subtasks, dependencies, execution order."""
from __future__ import annotations

import uuid
from typing import Any

from ADAM.core.exceptions import AgentError


class ECCPlan:
    """Execution plan from ECC."""

    def __init__(self, agent_id: str, objective: str, goals: list[str], steps: list[dict[str, Any]]) -> None:
        self.plan_id = str(uuid.uuid4())
        self.agent_id = agent_id
        self.objective = objective
        self.goals = goals
        self.steps = steps
        self.status = "pending"
        self.created_at = __import__("datetime").datetime.utcnow().isoformat()


class ECCPlanner:
    """Plan execution from objective."""

    def plan(self, agent_id: str, objective: str, available_skills: list[str]) -> ECCPlan:
        goals = [objective]
        steps: list[dict[str, Any]] = []
        lowered = objective.lower()

        if "knowledge" in lowered or "graph" in lowered:
            if "knowledge.search" in available_skills:
                steps.append({"skill": "knowledge.search", "params": {"query": objective}})
        elif "vector" in lowered or "semantic" in lowered:
            if "vector.search" in available_skills:
                steps.append({"skill": "vector.search", "params": {"query": objective, "top_k": 5}})
            if "context.build" in available_skills:
                steps.append({"skill": "context.build", "params": {"query": objective}})
        elif "automation" in lowered or "run" in lowered:
            if "automation.list" in available_skills:
                steps.append({"skill": "automation.list", "params": {}})
        elif "workspace" in lowered:
            if "workspace.scan" in available_skills:
                steps.append({"skill": "workspace.scan", "params": {}})
        else:
            if "system.status" in available_skills:
                steps.append({"skill": "system.status", "params": {}})
            else:
                steps.append({"skill": "context.build", "params": {"query": objective}})

        if not steps:
            steps.append({"skill": "system.status", "params": {}})

        return ECCPlan(agent_id=agent_id, objective=objective, goals=goals, steps=steps)
