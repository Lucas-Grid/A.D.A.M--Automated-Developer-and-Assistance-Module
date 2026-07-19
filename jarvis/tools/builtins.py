"""Web search and memory tools."""
from __future__ import annotations

import json
from typing import Any

import requests

from jarvis.tools.registry import Tool, ToolContext, ToolResult


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web via DuckDuckGo HTML and return the top result snippets."
    danger = "safe"
    schema = {"query": "string (required)", "limit": "int (default 5)"}

    def run(self, ctx: ToolContext, query: str = "", limit: int = 5, **_: Any) -> ToolResult:
        if not query:
            return ToolResult(ok=False, output="", tool=self.name, error="query is required")
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            resp.raise_for_status()
            html = resp.text
            # crude result extraction
            import re

            titles = re.findall(r'result__a"[^>]*>(.*?)</a>', html, re.S)
            snips = re.findall(r'result__snippet"[^>]*>(.*?)</a>', html, re.S)
            clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
            out = []
            for i, t in enumerate(titles[: int(limit)]):
                snippet = clean(snips[i]) if i < len(snips) else ""
                out.append(f"{i+1}. {clean(t)}\n   {snippet}")
            if not out:
                return ToolResult(ok=True, output="(no results / parser blocked)", tool=self.name)
            return ToolResult(ok=True, output="\n".join(out), tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class MemoryStoreTool(Tool):
    name = "memory_store"
    description = "Persist a fact/key-value pair to long-term memory."
    danger = "safe"
    schema = {"key": "string (required)", "value": "string (required)",
               "scope": "short|project|global (default global)", "tags": "comma-separated tags"}

    def run(self, ctx: ToolContext, key: str = "", value: str = "", scope: str = "global",
            tags: str = "", **_: Any) -> ToolResult:
        if not ctx.memory:
            return ToolResult(ok=False, output="", tool=self.name, error="Memory layer not configured.")
        if not key:
            return ToolResult(ok=False, output="", tool=self.name, error="key is required")
        try:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
            ctx.memory.store(key, value, scope=scope or "global", tags=tag_list)
            return ToolResult(ok=True, output=f"Saved [{scope or 'global'}]: {key}", tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))


class MemoryRecallTool(Tool):
    name = "memory_recall"
    description = "Recall a stored fact by key, or search across stored memories."
    danger = "safe"
    schema = {"key": "string (required)"}

    def run(self, ctx: ToolContext, key: str = "", **_: Any) -> ToolResult:
        if not ctx.memory:
            return ToolResult(ok=False, output="", tool=self.name, error="Memory layer not configured.")
        try:
            val = ctx.memory.recall(key)
            if val is None:
                # try a fuzzy search
                hits = ctx.memory.search(key)
                if not hits:
                    return ToolResult(ok=True, output=f"(no memory found for: {key})", tool=self.name)
                return ToolResult(ok=True, output="\n".join(f"- {k}: {v}" for k, v in hits), tool=self.name)
            return ToolResult(ok=True, output=f"{key} = {val}", tool=self.name)
        except Exception as e:
            return ToolResult(ok=False, output="", tool=self.name, error=str(e))
