"""Automation memory integration."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from ADAM.automations.history import get_job_history
from ADAM.memory.store import get_memory


class AutomationMemory:
    """Persist automation state into Memory Store."""

    def __init__(self) -> None:
        self._memory = get_memory()
        self._history = get_job_history()

    def record_last_run(self, workflow_id: str, job_id: str) -> None:
        self._memory.set(
            f"automation.last_run.{workflow_id}",
            job_id,
            tags=["automation", "last_run", workflow_id],
        )

    def record_failure(self, workflow_id: str, error: str) -> None:
        key = f"automation.failures.{workflow_id}.{datetime.utcnow().isoformat()}"
        self._memory.set(key, error, tags=["automation", "failure", workflow_id])

    def get_last_run(self, workflow_id: str) -> Optional[dict[str, Any]]:
        raw = self._memory.get(f"automation.last_run.{workflow_id}")
        if not raw:
            return None
        job_id = raw["value"]
        return self._history.get(job_id)

    def get_recent_failures(self, workflow_id: str, limit: int = 10) -> list[dict[str, Any]]:
        prefix = f"automation.failures.{workflow_id}."
        return [item for key, item in self._memory.search(prefix)[:limit]]


# Singleton
_memory: Optional[AutomationMemory] = None


def get_automation_memory() -> AutomationMemory:
    global _memory
    if _memory is None:
        _memory = AutomationMemory()
    return _memory


def reset_automation_memory() -> None:
    global _memory
    _memory = None
