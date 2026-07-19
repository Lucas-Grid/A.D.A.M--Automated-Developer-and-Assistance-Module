"""Meta-agent tool generator (jarvis-ai-assistant pattern).

The assistant can *bootstrap its own tools*: given a natural-language
description, it emits a small, safe Python function body that is written to
tools/generated/<name>.py and dynamically registered. This realizes the
"tools self-improve from natural language" idea without a heavy framework.

Generated files live under the workspace so they're inspectable and the user
can disable/delete them. Generation is gated by human confirmation because it
writes code.
"""
from __future__ import annotations

import os
import re
from typing import Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult, get_registry


class MetaAgentTool(Tool):
    name = "meta_create_tool"
    description = "Generate a new Python tool from a natural-language description and register it live."
    danger = "high"
    schema = {
        "name": "string (required) - tool name, snake_case",
        "description": "string (required) - what it does",
        "body": "string (required) - Python function body using ctx and returning a ToolResult",
    }

    def run(
        self,
        ctx: ToolContext,
        name: str = "",
        description: str = "",
        body: str = "",
        **_: Any,
    ) -> ToolResult:
        if not (name and body):
            return ToolResult(ok=False, output="", tool=self.name, error="name and body are required")
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", name or ""):
            return ToolResult(ok=False, output="", tool=self.name, error="name must be snake_case")
        if not ctx.confirm(f"Generate and register tool '{name}'? Review the body first."):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")

        gen_dir = os.path.join(ctx.workspace, "tools", "generated")
        os.makedirs(gen_dir, exist_ok=True)
        path = os.path.join(gen_dir, f"{name}.py")
        module_src = (
            "from jarvis.tools.registry import Tool, ToolResult, ToolContext\n\n"
            f"def _impl(ctx: ToolContext, **kwargs):\n"
            + "\n".join(f"    {line}" for line in body.splitlines())
            + "\n\n"
            "class GeneratedTool(Tool):\n"
            f"    name = {name!r}\n"
            f"    description = {description!r}\n"
            f"    danger = 'moderate'\n"
            "    def run(self, ctx, **kwargs):\n"
            "        return _impl(ctx, **kwargs)\n"
        )
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(module_src)
            # dynamic import + register
            import importlib.util

            spec = importlib.util.spec_from_file_location(f"jarvis_gen_{name}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            get_registry().register(mod.GeneratedTool())
            return ToolResult(
                ok=True,
                output=f"Created and registered tool '{name}' at {path}",
                tool=self.name,
            )
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=f"generation failed: {e}")
