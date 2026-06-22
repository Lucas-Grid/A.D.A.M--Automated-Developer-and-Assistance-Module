"""Built-in system skill example."""
from __future__ import annotations

from typing import Any

from ADAM.skills.base import BaseSkill


class SystemSkill(BaseSkill):
    """A simple built-in skill for system status queries."""

    name: str = "system.status"
    description: str = "Return basic runtime system status"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        del params  # unused
        import platform
        import sys

        return {
            "python": sys.version,
            "platform": platform.platform(),
            "arch": platform.architecture()[0],
        }
