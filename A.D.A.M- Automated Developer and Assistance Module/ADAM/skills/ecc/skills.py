"""ECC skills for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.core.exceptions import AgentError
from ADAM.ecc.engine import ECC
from ADAM.ecc.memory import ECCMemory
from ADAM.ecc.planning import ECCPlanner
from ADAM.ecc.reasoning import ECCReasoning
from ADAM.ecc.reflection import ECCReflection
from ADAM.ecc.telemetry import ECCTelemetry
from ADAM.ecc.validation import ECCValidation
from ADAM.skills.engine import get_skill_engine
from ADAM.skills.base import BaseSkill


class ECCReasonSkill(BaseSkill):
    name = "ecc.reason"
    description = "Run ECC reasoning over objective and context"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        objective = params.get("objective", "")
        from ADAM.agents.context import AgentContext
        context = AgentContext().build(objective)
        reasoning = ECCReasoning().reason(objective, context)
        return {"ok": True, "data": reasoning}


class ECCPlanSkill(BaseSkill):
    name = "ecc.plan"
    description = "Create ECC execution plan for objective"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        agent_id = params.get("agent_id", "default")
        objective = params.get("objective", "")
        skills = [m.name for m in get_skill_engine().registry.list() if m.enabled]
        plan = ECCPlanner().plan(agent_id=agent_id, objective=objective, available_skills=skills)
        return {"ok": True, "data": plan.__dict__}


class ECCValidateSkill(BaseSkill):
    name = "ecc.validate"
    description = "Validate an ECC plan"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        from ADAM.ecc.planning import ECCPlan
        plan_data = params.get("plan")
        if not plan_data:
            return {"ok": False, "error": "Missing plan"}
        plan = ECCPlan(
            agent_id=plan_data["agent_id"],
            objective=plan_data["objective"],
            goals=plan_data.get("goals", []),
            steps=plan_data.get("steps", []),
        )
        validation = ECCValidation().validate_plan(plan)
        return {"ok": True, "data": validation}


class ECCReflectSkill(BaseSkill):
    name = "ecc.reflect"
    description = "Reflect on ECC execution outcome"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        plan_data = params.get("plan", {})
        outputs = params.get("outputs", [])
        from ADAM.ecc.planning import ECCPlan
        plan = ECCPlan(
            agent_id=plan_data.get("agent_id", "unknown"),
            objective=plan_data.get("objective", ""),
            goals=plan_data.get("goals", []),
            steps=plan_data.get("steps", []),
        )
        reflection = ECCReflection().reflect(plan, outputs)
        return {"ok": True, "data": reflection}
