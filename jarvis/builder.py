"""Project builder (Phase C entry point): turn a natural-language prompt into a
scaffolded, coded, tested project using the agentic coding engine (Phase A).

This is the "Jarvis, build me an app" command. It:
  1. picks a language (from the prompt or default),
  2. scaffolds the project (init_project),
  3. drives the orchestrator's code_loop to implement + run + test it,
  4. commits the result.

It deliberately reuses existing tools rather than re-implementing file I/O.
"""
from __future__ import annotations

import os
import re
from typing import Any

from jarvis.orchestrator import Orchestrator
from jarvis.tools.registry import Tool, ToolContext, ToolResult


_LANG_HINTS = {
    "node": ["node", "javascript", "typescript", "react", "express", "npm"],
    "python": ["python", "flask", "fastapi", "django", "py", "pip"],
}


def detect_language(prompt: str) -> str:
    p = prompt.lower()
    scores = {lang: sum(1 for kw in kws if kw in p) for lang, kws in _LANG_HINTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "python"


class ProjectBuilderTool(Tool):
    name = "build_project"
    description = "Build a runnable project from a natural-language prompt: scaffold, implement, run tests, and commit."
    danger = "high"
    schema = {"prompt": "string (required) - what to build", "language": "python|node|generic (optional, auto-detected)"}

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orch = orchestrator

    def run(self, ctx: ToolContext, prompt: str = "", language: str = "", **_: Any) -> ToolResult:
        if not prompt:
            return ToolResult(ok=False, output="", tool=self.name, error="prompt is required")
        lang = language or detect_language(prompt)
        # derive a project name from the prompt
        slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:24].strip("_") or "project"
        project_dir = os.path.join(ctx.workspace, slug)
        if not ctx.confirm(f"Build project '{slug}' ({lang}) in {project_dir}?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")

        # 1) scaffold
        init = self.orch.registry.get("init_project")
        r0 = init.run(ctx, name=slug, language=lang, description=prompt)
        if not r0.ok:
            return r0

        # 2) drive the agentic coding loop with a concrete, tool-grounded goal
        goal = (
            f"Build the project at ./{slug} per this request: {prompt}\n"
            f"Steps: edit files with edit_file, run it with run_shell, verify with run_tests, "
            f"and fix any errors until the project works and its tests pass. "
            f"When done, summarize what was built."
        )
        result = self.orch.code_loop(goal, max_rounds=5, verbose=True)

        # 3) commit if we have a git tool
        commit = self.orch.registry.get("git_commit")
        if commit is not None and result.get("success"):
            commit.run(ctx, message=f"build: {slug}", cwd=slug)

        return ToolResult(
            ok=result.get("success", False),
            output=f"Built '{slug}' ({lang}).\nRounds: {result.get('rounds')}\n"
                   f"Last answer: {result.get('answer', '')[:500]}",
            tool=self.name,
        )
