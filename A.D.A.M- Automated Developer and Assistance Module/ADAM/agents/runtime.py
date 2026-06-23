"""Agent runtime: execute plans using skills and providers."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.agents.memory import AgentMemory
from ADAM.agents.planner import Plan
from ADAM.core.exceptions import AgentError
from ADAM.skills.engine import get_skill_engine

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Execute agent plans via Skill Engine."""

    def __init__(self) -> None:
        self._engine = get_skill_engine()

    async def run(self, agent_id: str, plan: Plan) -> dict[str, Any]:
        """Execute a plan and return results."""
        outputs: list[dict[str, Any]] = []
        memory = AgentMemory(agent_id)

        for step in plan.steps:
            skill_name = step.get("skill")
            params = step.get("params", {})
            if not skill_name:
                continue

            logger.info("Agent %s executing skill %s", agent_id, skill_name)
            result = await self._engine.execute(skill_name, params)
            outputs.append(result)

            memory.add_history(
                {
                    "skill": skill_name,
                    "params": params,
                    "result": result,
                }
            )

            if not result.get("ok", False):
                raise AgentError(f"Skill '{skill_name}' failed: {result.get('error')}")

        plan.status = "completed"
        return {
            "plan_id": plan.plan_id,
            "agent_id": agent_id,
            "status": plan.status,
            "steps": len(outputs),
            "outputs": outputs,
        }
