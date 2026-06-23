"""ECC reasoning: observe, reason, decide."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ADAM.ecc.telemetry import ECCTelemetry

logger = logging.getLogger(__name__)


class ECCReasoning:
    """Reason over context to produce insights."""

    def __init__(self, telemetry: ECCTelemetry | None = None) -> None:
        self._telemetry = telemetry or ECCTelemetry()

    async def reason(self, objective: str, context: dict[str, Any]) -> dict[str, Any]:
        from ADAM.agents.context import AgentContext
        context = await AgentContext().build_for_agent(agent_id="", objective=objective)
        with self._telemetry.timer() as t:
            insights: list[str] = []
            if context.get("graph_context"):
                insights.append("Knowledge graph context available")
            if context.get("vector_context"):
                insights.append("Vector retrieval results available")
            if context.get("automation_history"):
                insights.append("Automation history present")
            if context.get("agent_memory"):
                insights.append("Agent memory loaded")
            result = {
                "objective": objective,
                "insights": insights,
                "reasoning": "Structured reasoning based on available context",
            }
        self._telemetry.record("reasoning", {"duration_ms": getattr(t, "elapsed_ms", 0), "insights": len(insights)})
        return result
