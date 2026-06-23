"""Execution engine: run workflows step-by-step."""
from __future__ import annotations

import logging
import time
import uuid
from traceback import format_exc
from typing import Any, Optional

from ADAM.core.exceptions import AutomationError, SkillError
from ADAM.skills.engine import get_skill_engine

logger = logging.getLogger(__name__)


class JobResult:
    """Single step execution result."""

    def __init__(self, step: str, ok: bool, output: Any, error: Optional[str] = None, duration_ms: float = 0.0):
        self.step = step
        self.ok = ok
        self.output = output
        self.error = error
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "ok": self.ok,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class ExecutionEngine:
    """Execute skills from a workflow sequentially."""

    def __init__(self) -> None:
        self._engine = get_skill_engine()

    async def execute_workflow(self, workflow_id: str, steps: list[str]) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        results: list[JobResult] = []
        start = time.perf_counter()

        for step in steps:
            step_start = time.perf_counter()
            try:
                result = await self._engine.execute(step, {})
                duration = (time.perf_counter() - step_start) * 1000
                if result.get("ok"):
                    results.append(JobResult(step=step, ok=True, output=result.get("result"), duration_ms=duration))
                else:
                    results.append(
                        JobResult(
                            step=step,
                            ok=False,
                            output=None,
                            error=result.get("error", "Unknown skill error"),
                            duration_ms=duration,
                        )
                    )
                    raise AutomationError(f"Workflow '{workflow_id}' failed at step '{step}': {results[-1].error}")
            except Exception as exc:
                duration = (time.perf_counter() - step_start) * 1000
                results.append(JobResult(step=step, ok=False, output=None, error=str(exc), duration_ms=duration))
                logger.exception("Workflow %s aborted at %s", workflow_id, step)
                break

        total_duration = (time.perf_counter() - start) * 1000
        return {
            "job_id": job_id,
            "workflow_id": workflow_id,
            "success": all(r.ok for r in results),
            "results": [r.to_dict() for r in results],
            "total_duration_ms": total_duration,
        }


# Singleton
_engine: Optional[ExecutionEngine] = None


def get_execution_engine() -> ExecutionEngine:
    global _engine
    if _engine is None:
        _engine = ExecutionEngine()
    return _engine


def reset_execution_engine() -> None:
    global _engine
    _engine = None
