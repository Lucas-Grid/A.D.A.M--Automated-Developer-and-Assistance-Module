"""Workspace memory integration."""
from __future__ import annotations

import json
from typing import Any

from ADAM.memory.store import get_memory
from ADAM.workspace.analyzer import ProjectAnalyzer


class WorkspaceMemory:
    """Persist workspace analysis results into Memory Store."""

    def __init__(self) -> None:
        self.memory = get_memory()
        self.analyzer = ProjectAnalyzer()

    def save_current(self, workspace_name: str, analysis: dict[str, Any]) -> None:
        self.memory.set("workspace.current", workspace_name, tags=["workspace"])
        self.memory.set("workspace.summary", json.dumps(analysis), tags=["workspace", "summary"])
        self.memory.set("workspace.languages", json.dumps(analysis.get("languages", [])), tags=["workspace", "languages"])
        self.memory.set("workspace.frameworks", json.dumps(analysis.get("frameworks", [])), tags=["workspace", "frameworks"])

    def load_current(self) -> dict[str, Any]:
        name = self.memory.get("workspace.current")
        summary = self.memory.get("workspace.summary")
        return {
            "current_workspace": name["value"] if name else None,
            "summary": json.loads(summary["value"]) if summary else None,
        }
