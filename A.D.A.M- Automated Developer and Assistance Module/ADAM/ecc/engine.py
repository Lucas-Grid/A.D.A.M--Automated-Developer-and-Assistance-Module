"""ECC engine: orchestrates reasoning, planning, validation, execution, reflection."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.core.exceptions import AgentError
from ADAM.ecc.memory import ECCMemory
from ADAM.ecc.planning import ECCPlanner, ECCPlan
from ADAM.ecc.reflection import ECCReflection
from ADAM.ecc.reasoning import ECCReasoning
from ADAM.ecc.telemetry import ECCTelemetry
from ADAM.ecc.validation import ECCValidation
from ADAM.skills.engine import get_skill_engine

logger = logging.getLogger(__name__)


class ECC:
    """Expensive Cognition Cycle engine."""

    def __init__(self) -> None:
        self._reasoning = ECCReasoning()
        self._planner = ECCPlanner()
        self._validation = ECCValidation()
        self._reflection = ECCReflection()
        self._memory = ECCMemory()
        self._telemetry = ECCTelemetry()

    def _get_runtime(self):
        from ADAM.agents.runtime import AgentRuntime
        return AgentRuntime()

    def _get_context_builder(self):
        from ADAM.agents.context import AgentContext
        return AgentContext()

    def _get_agent_memory(self, agent_id: str):
        from ADAM.agents.memory import AgentMemory
        return AgentMemory(agent_id)

    async def run(self, agent_id: str, objective: str) -> dict[str, Any]:
        with self._telemetry.timer() as t:
            available = [s["name"] for s in get_skill_engine().list_skills()]

            context = await self._get_context_builder().build_for_agent(agent_id=agent_id, objective=objective)
            reasoning = await self._reasoning.reason(objective, context)
            plan = self._planner.plan(agent_id, objective, available)

            validation = self._validation.validate_plan(plan)
            if not validation["valid"]:
                raise AgentError(f"Plan validation failed: {validation['errors']}")

            result = await self._get_runtime().run(agent_id, plan)
            reflection = self._reflection.reflect(plan, result.get("outputs", []))

            self._memory.add_decision({
                "agent_id": agent_id,
                "objective": objective,
                "plan_id": plan.plan_id,
                "success": reflection.get("success", False),
            })

        self._telemetry.record("cycle_complete", {
            "agent_id": agent_id,
            "plan_id": plan.plan_id,
            "duration_ms": getattr(t, "elapsed_ms", 0),
            "success": reflection.get("success", False),
        })
        return {
            "plan": plan.__dict__,
            "reasoning": reasoning,
            "validation": validation,
            "execution": result,
            "reflection": reflection,
        }
