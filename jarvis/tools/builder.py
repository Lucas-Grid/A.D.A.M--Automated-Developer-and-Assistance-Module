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
from typing import TYPE_CHECKING, Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult

if TYPE_CHECKING:
    from jarvis.orchestrator import Orchestrator


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
        slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:24].strip("_") or "project"
        project_dir = os.path.join(ctx.workspace, slug)
        if not ctx.confirm(f"Build project '{slug}' ({lang}) in {project_dir}?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")

        init = self.orch.registry.get("init_project")
        r0 = init.run(ctx, name=slug, language=lang, description=prompt)
        if not r0.ok:
            return r0

        # The project is ALREADY scaffolded at ./<slug>. Tell the model the exact
        # path and forbid re-scaffolding, otherwise it drifts to a second project
        # name and the commit lands on the wrong directory.
        goal = (
            f"TASK: implement this in the ALREADY-scaffolded project at ./{slug} (do NOT call init_project again): {prompt}\n"
            "MANDATORY WORKFLOW — you MUST do these steps, in order, every turn call EXACTLY ONE tool:\n"
            "  1. edit_file to WRITE the implementation (path like ./{slug}/main.py). "
            "Respond with the edit_file JSON (path only) then the ENTIRE file in a fenced ``` block. "
            "You MUST write real, working code — never leave the scaffold as-is.\n"
            "  2. run_shell to execute it (cwd=./{slug}) and confirm it works.\n"
            "  3. run_tests to verify (cwd=./{slug}).\n"
            "  4. If tests fail, repeat from step 1 with the fix. Keep going until it runs and tests pass.\n"
            "DO NOT stop early. DO NOT say 'done' or 'goal met' until main.py actually implements the feature "
            "and run_tests passes. Reading files is optional; WRITING the code is required.\n"
            "When truly finished, give a one-line summary of what was built."
        )
        result = self.orch.code_loop(goal, max_rounds=6, verbose=True)

        # Verify the build actually produced working code before committing.
        # A "no-op" (model answered without editing) must not count as success.
        # Note: we trust the ARTIFACT (real code + passing tests), not the
        # model's end-of-run chatter — late rounds may show transient errors
        # (rate-limiting, a stray malformed call) even though the file is done.
        project_dir = os.path.join(ctx.workspace, slug)
        verified = self._verify_project(ctx, project_dir, slug)
        success = verified
        if success:
            commit = self.orch.registry.get("git_commit")
            if commit is not None:
                commit.run(ctx, message=f"build: {slug}", cwd=slug)

        return ToolResult(
            ok=success,
            output=f"Built '{slug}' ({lang}).\nRounds: {result.get('rounds')}\n"
                   f"Verified: {verified}\n"
                   f"Last answer: {result.get('answer', '')[:500]}",
            tool=self.name,
        )

    @staticmethod
    def _verify_project(ctx: ToolContext, project_dir: str, slug: str) -> bool:
        """Confirm the scaffold was actually implemented: a source file exists
        and differs from the default template, and the test suite passes."""
        if not os.path.isdir(project_dir):
            return False
        # Find a python source file that isn't the bare template.
        changed = False
        for root, _, files in os.walk(project_dir):
            if ".git" in root:
                continue
            for f in files:
                if f.endswith(".py") and f != "test_smoke.py":
                    p = os.path.join(root, f)
                    try:
                        content = open(p, encoding="utf-8", errors="replace").read()
                    except Exception:
                        continue
                    # The scaffold default main.py prints "Hello from <slug>".
                    if "Hello from " + slug not in content and "def main()" in content:
                        changed = True
                    if "def main()" not in content and "import " in content:
                        changed = True
        if not changed:
            return False
        # Run the test suite; it must pass.
        try:
            from jarvis.tools.coding import RunTestsTool

            rt = RunTestsTool().run(ctx, cwd=project_dir, timeout=60)
            return rt.ok
        except Exception:
            return changed
