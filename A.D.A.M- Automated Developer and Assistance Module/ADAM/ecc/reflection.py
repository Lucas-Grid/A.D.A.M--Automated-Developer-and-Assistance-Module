"""ECC reflection: analyze outcomes and store lessons."""
from __future__ import annotations

import logging
from typing import Any

from ADAM.ecc.memory import ECCMemory
from ADAM.ecc.telemetry import ECCTelemetry

logger = logging.getLogger(__name__)


class ECCReflection:
    """Reflect on execution outcomes."""

    def __init__(self, memory: ECCMemory | None = None, telemetry: ECCTelemetry | None = None) -> None:
        self._memory = memory or ECCMemory()
        self._telemetry = telemetry or ECCTelemetry()

    def reflect(self, plan: Any, outputs: list[dict[str, Any]]) -> dict[str, Any]:
        failures = [o for o in outputs if not o.get("ok", False)]
        improvements: list[str] = []
        if failures:
            improvements.append("Review failed skills and retry with fallback")
        if len(outputs) > 5:
            improvements.append("Consider breaking large plans into smaller chunks")

        outcome = {
            "plan_id": getattr(plan, "plan_id", "unknown"),
            "success": len(failures) == 0,
            "failures": len(failures),
            "improvements": improvements,
        }
        self._memory.add_reflection(outcome)
        self._telemetry.record("reflection", {"success": outcome["success"], "failures": len(failures)})
        return outcome
