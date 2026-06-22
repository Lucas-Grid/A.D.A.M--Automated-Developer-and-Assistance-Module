"""Base skill interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """Abstract skill contract.

    Every skill must implement:
    - name: unique identifier
    - description: human-readable purpose
    - execute: run the skill with provided parameters
    """

    name: str = "base_skill"
    description: str = ""

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run the skill and return a result payload."""

    def validate_params(self, params: dict[str, Any]) -> None:
        """Optional preflight validation."""
