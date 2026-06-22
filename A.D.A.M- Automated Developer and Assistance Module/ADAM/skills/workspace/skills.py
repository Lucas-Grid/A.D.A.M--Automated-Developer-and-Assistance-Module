"""Workspace skills for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.skills.base import BaseSkill
from ADAM.workspace.analyzer import ProjectAnalyzer
from ADAM.workspace.manager import get_workspace_manager
from ADAM.workspace.memory import WorkspaceMemory
from ADAM.workspace.scanner import RepositoryScanner


class WorkspaceScanSkill(BaseSkill):
    name = "workspace.scan"
    description = "Scan a workspace directory for languages and dependency files"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params.get("path")
        if not path:
            raise ValueError("Missing 'path' parameter")
        scanner = RepositoryScanner(path)
        return scanner.scan()


class WorkspaceAnalyzeSkill(BaseSkill):
    name = "workspace.analyze"
    description = "Analyze a workspace directory and return structured analysis data"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        path = params.get("path")
        if not path:
            raise ValueError("Missing 'path' parameter")
        analyzer = ProjectAnalyzer()
        return analyzer.analyze(path)


class WorkspaceSummarySkill(BaseSkill):
    name = "workspace.summary"
    description = "Register workspace, analyze it, and persist summary into Memory Store"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        path = params.get("path")
        description = params.get("description", "")
        if not name or not path:
            raise ValueError("Missing 'name' or 'path' parameter")

        manager = get_workspace_manager()
        workspace = manager.register(name, path, description)

        analyzer = ProjectAnalyzer()
        analysis = analyzer.analyze(path)

        memory = WorkspaceMemory()
        memory.save_current(name, analysis)

        return {"workspace": workspace, "analysis": analysis}
