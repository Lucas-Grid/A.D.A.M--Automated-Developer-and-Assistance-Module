"""Filesystem tools: list and read files in the workspace."""
from __future__ import annotations

import os
from typing import Any

from jarvis.tools.registry import Tool, ToolContext, ToolResult


class FileListTool(Tool):
    name = "file_list"
    description = "List files and directories in a path (defaults to the workspace root)."
    danger = "safe"
    schema = {"path": "string - directory to list (default '.')"}

    def run(self, ctx: ToolContext, path: str = ".", **_: Any) -> ToolResult:
        target = os.path.join(ctx.workspace, path) if not os.path.isabs(path) else path
        try:
            entries = []
            for name in sorted(os.listdir(target)):
                full = os.path.join(target, name)
                kind = "dir" if os.path.isdir(full) else "file"
                entries.append(f"{kind:4s} {name}")
            return ToolResult(ok=True, output="\n".join(entries) or "(empty)", tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class FileReadTool(Tool):
    name = "file_read"
    description = "Read the text contents of a file (first 2000 lines)."
    danger = "safe"
    schema = {"path": "string (required) - file to read"}

    MAX_BYTES = 200_000

    def run(self, ctx: ToolContext, path: str = "", **kw: Any) -> ToolResult:
        path = path or kw.get("filename") or kw.get("file") or kw.get("filepath") or ""
        if not path:
            return ToolResult(ok=False, output="", tool=self.name, error="path is required")
        target = os.path.join(ctx.workspace, path) if not os.path.isabs(path) else path
        if not os.path.isfile(target):
            return ToolResult(ok=False, output="", tool=self.name, error=f"Not a file: {path}")
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read(self.MAX_BYTES)
            return ToolResult(ok=True, output=data, tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class FileWriteTool(Tool):
    name = "file_write"
    description = "Write text to a file in the workspace (creates/overwrites)."
    danger = "moderate"
    schema = {"path": "string (required)", "content": "string (required)"}

    def run(self, ctx: ToolContext, path: str = "", content: str = "", **kw: Any) -> ToolResult:
        path = path or kw.get("filename") or kw.get("file") or kw.get("filepath") or ""
        content = content or kw.get("text") or ""
        if not path:
            return ToolResult(ok=False, output="", tool=self.name, error="path is required")
        target = os.path.join(ctx.workspace, path) if not os.path.isabs(path) else path
        if not ctx.confirm(f"Write {len(content)} chars to {target}?"):
            return ToolResult(ok=False, output="", tool=self.name, error="Cancelled by user.")
        try:
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(content or "")
            return ToolResult(ok=True, output=f"Wrote {len(content or '')} chars to {target}", tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))
