"""Agent memory: per-agent state and history."""
from __future__ import annotations

import json
from typing import Any, Optional

from ADAM.core.config import get_settings
from ADAM.core.exceptions import AgentError


class AgentMemory:
    """Manage agent-specific memory entries."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self._prefix = f"agent.memory.{agent_id}"
        self._history_key = f"agent.history.{agent_id}"
        self._keys: list[str] = []
        from ADAM.memory.store import get_memory
        self._memory = get_memory()

    def set(self, key: str, value: Any) -> None:
        full_key = f"{self._prefix}.{key}"
        self._memory.set(full_key, json.dumps(value))
        if full_key not in self._keys:
            self._keys.append(full_key)

    def get(self, key: str) -> Optional[dict[str, Any]]:
        full_key = f"{self._prefix}.{key}"
        row = self._memory.get(full_key)
        return json.loads(row["value"]) if row else None

    def add_history(self, entry: dict[str, Any]) -> None:
        import uuid
        from datetime import datetime
        entry.setdefault("id", str(uuid.uuid4()))
        entry.setdefault("timestamp", datetime.utcnow().isoformat())
        history = self.get_history()
        history.append(entry)
        self._memory.set(self._history_key, json.dumps(history))

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        row = self._memory.get(self._history_key)
        if not row:
            return []
        data = json.loads(row["value"])
        if not isinstance(data, list):
            return []
        return data[-limit:]

    def clear(self) -> None:
        """Clear all memory and history for this agent."""
        # Delete individual tracked keys
        for key in list(self._keys):
            self._memory.delete(key)
        self._keys.clear()
        # Delete history
        self._memory.delete(self._history_key)
