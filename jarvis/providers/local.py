"""Local deterministic provider.

This provider needs no network and no API key. It implements a tiny but real
"plan-then-act" brain so the whole Jarvis loop is demonstrable end-to-end on
any machine: it inspects the available tool catalogue and the user's request,
then emits a structured tool-call in the same JSON envelope the orchestrator
parses for every provider. When no tool clearly matches, it answers with a
plain-language response.

It is intentionally transparent and safe: it never guesses at shell/power
commands, and it routes everything through the real tool registry so side
effects stay sandboxed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Sequence

from jarvis.providers.base import LLMProvider
from jarvis.types import GenerationResult, Message


class LocalProvider(LLMProvider):
    name = "local"
    model = "deterministic"

    def generate(
        self,
        messages: Sequence[Message],
        max_tokens: int = 1024,
        temperature: float = 0.7,
        stop: Sequence[str] | None = None,
    ) -> GenerationResult:
        # The last user message is the active request.
        request = ""
        catalogue_hint = ""
        for m in messages:
            if m.role == "user" and m.content:
                request = m.content
            if m.role == "system" and "TOOLS:" in m.content:
                catalogue_hint = m.content

        # If we already have a tool result in context, the previous action
        # completed -- synthesize a final answer instead of re-calling.
        has_tool_result = any(m.role == "tool" for m in messages)
        if has_tool_result:
            answer = self._summarize(request, messages)
            return GenerationResult(text=answer, provider=self.name, model=self.model)

        decision = self._decide(request, catalogue_hint)
        if decision is not None:
            # Emit the exact JSON envelope the orchestrator expects.
            payload = json.dumps({"tool": decision["tool"], "args": decision["args"]})
            return GenerationResult(text=payload, provider=self.name, model=self.model)

        # No tool matched and nothing to observe: answer conversationally.
        answer = self._summarize(request, messages)
        return GenerationResult(text=answer, provider=self.name, model=self.model)

    # --- decision heuristics -------------------------------------------------
    def _decide(self, request: str, catalogue: str) -> dict[str, Any] | None:
        r = request.lower()

        # Code execution: "run/python/execute/script" with code present.
        if re.search(r"\b(run|execute|python|script)\b", r) and ("```" in request or "code" in r or "print" in r):
            code = self._extract_code(request)
            if code:
                return {"tool": "sandbox_exec", "args": {"code": code, "language": "python"}}

        # Remember something.
        if re.search(r"\b(remember|save|note|memorize)\b", r):
            # remember: <key> = <value> or remember that <fact>
            m = re.match(r".*?(?:remember|save|note)\s*(?:that\s*)?(.*?)(?:=|is\s|:)\s*(.+)", request, re.I)
            if "=" in request or ":" in request:
                parts = re.split(r"=|is|:", request, maxsplit=1)
                key = parts[0].lower().replace("remember", "").replace("save", "").replace("note", "").strip(" :")
                val = parts[1].strip()
                if key and val:
                    return {"tool": "memory_store", "args": {"key": key, "value": val}}
            fact = re.sub(r"(?i)remember (that )?", "", request).strip()
            if fact:
                return {"tool": "memory_store", "args": {"key": fact[:40], "value": fact}}

        # Recall something.
        if re.search(r"\b(recall|what did i|do you remember|retrieve)\b", r):
            m = re.search(r"(?:recall|retrieve)\s+(.+)", request, re.I)
            key = m.group(1).strip().rstrip("?") if m else request
            return {"tool": "memory_recall", "args": {"key": key}}

        # Build a project from a prompt (Phase C). The local brain can scaffold a
        # real runnable project via init_project (no LLM needed), but the heavier
        # build_project needs an LLM to implement files — so defer that to a real
        # provider and keep the offline path honest/useful instead of looping.
        if re.match(r"(?i)^\s*(build|create|make|scaffold|generate)\b", request) and (
            "build " in r or "build_project" in r or "project" in r or "app" in r
        ):
            prompt = re.sub(r"(?i)^(build|create|make|scaffold|generate)\s+(me\s+|a\s+|an\s+|the\s+)?", "", request).strip(" .")
            # Offline: scaffold a runnable project; the LLM-driven builder is for
            # real providers. init_project creates a working 'hello' app reliably.
            return {"tool": "init_project", "args": {"name": self._slug(prompt), "language": "python", "description": prompt}}

        # Run a shell command.
        if re.search(r"\b(run_shell|shell|execute|bash|sh\b|cmd)\b", r):
            cmd = re.sub(r"(?i)^(run_shell|shell|execute|bash|sh|cmd)\b[:\s]*", "", request).strip()
            if cmd:
                return {"tool": "run_shell", "args": {"command": cmd}}

        # Edit/write a file — only when a real path AND code content are present
        # (the orchestrator pulls the fenced block as content). Without both we
        # can't act, so fall through to a plain answer instead of an error loop.
        if re.search(r"\b(edit_file|write|create file|save file)\b", r) or "edit_file" in r:
            m = re.search(r"(?:edit_file|write|create file|save file)\s+([\w./\\-]+)", r)
            path = m.group(1) if m else ""
            content = self._extract_code(request)
            if path and content:
                return {"tool": "edit_file", "args": {"path": path, "content": content}}

        # Web search.
        if re.search(r"\b(search|look up|google|find out|research)\b", r):
            q = re.sub(r"(?i)(please\s+)?(search|look up|google|find out|research)\s+(for\s+|about\s+)?", "", request)
            q = q.strip(" .?")
            if q:
                return {"tool": "web_search", "args": {"query": q}}

        # File listing / reading in the workspace.
        if re.search(r"\b(list|show|ls|read|cat|files?|directory|folder)\b", r):
            path = "."
            m = re.search(r"(?:in|of|for|under|at)\s+([\w./\\-]+)", request)
            if m:
                path = m.group(1).strip(" .")
            if re.search(r"\b(read|cat|contents?)\b", r):
                return {"tool": "file_read", "args": {"path": path if path != "." else (m.group(1) if m else ".")}}
            return {"tool": "file_list", "args": {"path": path}}

        # Fall back to matching a tool name literally mentioned in the request.
        for name in self._tool_names(catalogue):
            if name in r:
                return {"tool": name, "args": {"_raw": request}}
        return None

    @staticmethod
    def _tool_names(catalogue: str) -> list[str]:
        # catalogue lines look like:  - name (desc)
        names = re.findall(r"-\s+([a-z_][a-z0-9_]*)\s*\(", catalogue)
        return names

    @staticmethod
    def _slug(text: str, max_len: int = 24) -> str:
        """Turn a free-text prompt into a filesystem-safe project name."""
        import re as _re
        slug = _re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        slug = slug[:max_len].strip("_")
        return slug or "project"

    @staticmethod
    def _extract_code(text: str) -> str | None:
        # Prefer a fenced code block.
        m = re.search(r"```(?:python|py)?\s*(.*?)```", text, re.S)
        if m:
            code = m.group(1).strip()
            if code:
                return code
        # Otherwise strip a leading imperative prefix like "run this python:".
        stripped = re.sub(
            r"(?i)^\s*(run|execute|python|shell|sh|bash|do)\b.*?:\s*", "", text
        ).strip()
        if not stripped:
            return None
        # Validate it is at least syntactically plausible Python.
        try:
            compile(stripped, "<check>", "exec")
        except SyntaxError:
            return None
        return stripped

    @staticmethod
    def _summarize(request: str, messages: Sequence[Message]) -> str:
        # Reference the most recent tool result in context.
        last_tool = None
        for m in messages:
            if m.role == "tool":
                last_tool = m
        if last_tool is not None:
            return (
                f"I ran that through {last_tool.tool_name or 'a tool'} and here is what came back:\n"
                f"{last_tool.content}\n\n"
                f"(Local provider is deterministic and key-free; configure a real "
                f"provider in .jarvis.yaml for full natural-language reasoning.)"
            )
        return (
            "I'm running on the built-in local brain, which needs no API key. "
            "I can run Python in a sandbox, manage files, search the web, and remember facts. "
            "Try: 'run this python: print(2**10)', 'list files', 'remember api_key = secret123', "
            "or 'search for FastAPI tutorials'. To unlock full LLM reasoning, add a provider in .jarvis.yaml."
        )
