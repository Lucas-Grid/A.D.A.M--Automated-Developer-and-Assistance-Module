"""Orchestrator: the agent loop.

Turns a natural-language request into a sequence of tool calls by repeatedly:

    plan    -> ask the provider (with the tool catalogue) for the next action
    act     -> execute the chosen tool
    observe -> feed the tool result back as a 'tool' message
    answer  -> when the provider emits a plain response (no tool), return it

This is the MRKL / ReAct pattern from the roadmap. The provider returns either
a JSON tool-call envelope ({"tool": ..., "args": ...}) or free text. The local
provider implements that envelope deterministically; real LLM providers are
prompted to emit the same envelope via the system prompt.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from jarvis.memory import Memory, ShortTermMemory, TaskList, Telemetry
from jarvis.providers.base import LLMProvider
from jarvis.providers.registry import get_provider
from jarvis.tools.registry import ToolContext, ToolRegistry, get_registry
from jarvis.types import Message, ToolResult


class Orchestrator:
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        registry: Optional[ToolRegistry] = None,
        memory: Optional[Memory] = None,
        max_steps: int = 12,
        require_confirmation: bool = True,
        workspace: str = ".",
        ask_confirm: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.provider = provider or get_provider()
        self.registry = registry or get_registry()
        self.memory = memory or Memory()
        self.short = ShortTermMemory()
        self.max_steps = max_steps
        self.require_confirmation = require_confirmation
        self.workspace = workspace
        self._ask_confirm = ask_confirm
        self.tasks = TaskList()        # side-channel (jarvis-ai-assistant)
        self.telemetry = Telemetry()    # step cost/latency (OpenJarvis)
        # Semantic memory + voice handles (lazily used by knowledge tools).
        from jarvis.vectormem import VectorMemory

        self.vector = VectorMemory(db_path="jarvis_vector.db")
        from jarvis.voice import Voice

        self.voice = Voice()
        # Bind the project-builder tool to this orchestrator (Phase C entry point)
        from jarvis.tools.builder import ProjectBuilderTool

        self.registry.register(ProjectBuilderTool(self))

    # --- public API ---------------------------------------------------------
    def chat(self, user_input: str, verbose: bool = True) -> str:
        """Run one request through the agent loop and return the final answer."""
        self.short.clear()  # each request is a fresh turn for the local planner
        self.short.add("user", user_input)
        system = self._system_prompt(self._recalled_context(user_input))
        for step in range(self.max_steps):
            messages = [Message("system", system)] + [
                Message(m["role"], m["content"], tool_name=m.get("tool")) for m in self.short.snapshot()
            ]
            try:
                # Agent turns are stateful (they depend on prior tool results),
                # so never serve a cached response here — that would replay stale
                # tool calls. The cache is only for stateless one-shot generates.
                result = self.provider.generate(messages)
            except Exception as exc:  # provider/network failure -> retry the turn
                err = f"[provider error] {exc}"
                if verbose:
                    print(f"  {err} — retrying...")
                self.short.add("system", err)
                continue
            action = self._parse_action(result.text or "")
            if action is None:
                # Provider chose to answer directly (or returned no parseable text).
                text = result.text or ""
                self.short.add("assistant", text)
                if verbose:
                    print(f"\n[Jarvis] {text}")
                return text

            tool_name = action["tool"]
            args = action.get("args", {}) or {}
            tool = self.registry.get(tool_name)
            if tool is None:
                obs = f"ERROR: unknown tool '{tool_name}'. Available: {', '.join(self.registry.names())}"
                self.short.add("tool", obs, tool=tool_name)
                if verbose:
                    print(f"  [step {step+1}] {obs}")
                continue

            if verbose:
                print(f"  [step {step+1}] -> {tool_name}({_short_args(args)})")

            # Human-in-the-loop gate for risky tools.
            if self.require_confirmation and tool.danger in ("moderate", "high"):
                if not self._confirm(tool, args):
                    obs = "ERROR: action cancelled by user."
                    self.short.add("tool", obs, tool=tool_name)
                    continue

            ctx = ToolContext(
                workspace=self.workspace,
                memory=self.memory,
                ask_confirm=self._confirm if self.require_confirmation else None,
                provider_info={"provider": self.provider.name, "model": self.provider.model},
            )
            ctx.vector = self.vector
            ctx.voice = self.voice
            import time

            t0 = time.perf_counter()
            try:
                res: ToolResult = tool.run(ctx, **args)
            except Exception as e:  # never let a tool crash the loop
                res = ToolResult(ok=False, output="", tool=tool_name, error=repr(e))
            ms = (time.perf_counter() - t0) * 1000
            self.telemetry.record(tool_name, ms, tokens=len(str(args)))
            self.tasks.add(f"{tool_name}({_short_args(args)})")
            obs = res.format_for_prompt()
            self.short.add("tool", obs, tool=tool_name)
            if verbose:
                print(f"        {obs[:300]}")

        final = (
            "I reached the step limit without producing a final answer. "
            "Here is the last observation:\n"
            + (self.short.snapshot()[-1]["content"] if self.short.snapshot() else "(none)")
        )
        self.short.add("assistant", final)
        return final

    def ask_full(self, user_input: str, verbose: bool = False) -> dict[str, Any]:
        """OpenJarvis-style: return content + tool_results + telemetry."""
        answer = self.chat(user_input, verbose=verbose)
        tool_results = [
            {"tool": m.get("tool"), "content": m["content"]}
            for m in self.short.snapshot()
            if m["role"] == "tool"
        ]
        return {
            "content": answer,
            "tool_results": tool_results,
            "telemetry": self.telemetry.summary(),
            "tasks": self.tasks.snapshot(),
        }

    def code_loop(self, goal: str, max_rounds: int = 5, verbose: bool = True) -> dict[str, Any]:
        """Autonomous coding cycle (Phase A): build toward ``goal``, and if a
        run/test step fails, feed the error back and retry. Each round is one
        full agent pass; the orchestrator already does edit->run->observe
        inside a pass, so this adds a *cross-round* retry budget on failure.
        """
        last_answer = ""
        for rnd in range(1, max_rounds + 1):
            prompt = goal if rnd == 1 else (
                f"{goal}\n\nRound {rnd}: the previous attempt was not successful. "
                "Review the last tool output/error, fix the code, and re-run until it works."
            )
            last_answer = self.chat(prompt, verbose=verbose)
            # success heuristic: no recent tool reported an error AND the model
            # actually edited a file (a read-only "goal met" is not success).
            recent = [m for m in self.short.snapshot() if m["role"] == "tool"]
            failed = any(m["content"].startswith("[") and "ERROR" in m["content"] for m in recent[-3:])
            edited = any(m.get("tool") == "edit_file" and "ERROR" not in m["content"]
                         for m in recent[-3:])
            if not failed and edited:
                if verbose:
                    print(f"\n[Jarvis] goal met after {rnd} round(s).")
                return {"success": True, "rounds": rnd, "answer": last_answer,
                        "tool_results": self._tool_results(), "telemetry": self.telemetry.summary()}
            if verbose:
                print(f"\n[Jarvis] round {rnd} had errors; retrying...")
        return {"success": False, "rounds": max_rounds, "answer": last_answer,
                "tool_results": self._tool_results(), "telemetry": self.telemetry.summary()}

    def _tool_results(self) -> list[dict]:
        return [
            {"tool": m.get("tool"), "content": m["content"]}
            for m in self.short.snapshot()
            if m["role"] == "tool"
        ]

    # --- internals ----------------------------------------------------------
    def _recalled_context(self, user_input: str) -> str:
        """Pull relevant stored context (facts + semantic recall) for this turn."""
        parts: list[str] = []
        # 1) Key/value memory facts.
        try:
            facts = self.memory.all() if hasattr(self.memory, "all") else []
            if facts:
                lines = [f"- {f.get('key')}: {f.get('value')}" for f in facts[:20]]
                parts.append("STORED FACTS:\n" + "\n".join(lines))
        except Exception:
            pass
        # 2) Semantic recall (meaning-based) for the current query.
        try:
            hits = self.vector.recall(user_input, collection=None, top_k=3)
            if hits:
                lines = [f"- (sim {h['score']:.2f}) {h['text']}" for h in hits]
                parts.append("RELEVANT PAST NOTES:\n" + "\n".join(lines))
        except Exception:
            pass
        return "\n\n".join(parts)

    def _system_prompt(self, recalled: str = "") -> str:
        cat = self.registry.catalogue()
        block = ""
        if recalled:
            block = (
                "\nBelow is context recalled from memory for this request. Use it when "
                "relevant; do not repeat it back unless asked.\n"
                f"{recalled}\n"
            )
        return (
            "You are JARVIS, a desktop-centric autonomous AI assistant.\n"
            "You have access to these tools:\n"
            f"TOOLS:\n{cat}\n\n"
            "To call a tool, respond with ONLY a JSON object of the form:\n"
            '{"tool": "<tool_name>", "args": {<tool_args>}}\n'
            "When the task is complete or no tool is needed, respond with a short "
            "natural-language answer for the user. Never invent tool names.\n"
            "If a tool call is needed, emit the JSON and nothing else.\n\n"
            "IMPORTANT FILE-WRITING RULE (avoids broken JSON): to write or overwrite a "
            "file, respond with the edit_file JSON (path only) followed by the ENTIRE "
            "file text in a fenced code block. Do NOT put the code inside the JSON, and "
            "do NOT use an 'operation' field — just path + fenced block, like:\n"
            '{"tool": "edit_file", "args": {"path": "src/app.py"}}\n'
            "```\n<full file contents here>\\n```\n"
            "The orchestrator uses the fenced block as the file contents. This works "
            "even when the code contains quotes, braces, or newlines. Always include "
            "the fenced block right after the JSON — never send a file-write call "
            "without it."
            + block
        )

    @staticmethod
    def _parse_action(text: str) -> Optional[dict[str, Any]]:
        text = text.strip()
        end = -1  # used by the post-JSON code fallback; harmless for XML path
        obj = None  # set by the XML or JSON branch below
        # Support both JSON tool-call envelopes ({"tool":..., "args":...}) and
        # Anthropic/XML-style calls (<function=...><parameter=...>...</parameter>).
        xml_obj = _parse_xml_action(text)
        if xml_obj is not None and xml_obj.get("tool"):
            obj = xml_obj
        else:
            # Find the first balanced {...} object. A greedy regex over-matches when
            # the response has trailing prose, so scan braces manually.
            start = text.find("{")
            if start < 0:
                return None
            depth = 0
            in_str = False
            esc = False
            end = -1
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if obj is None:
            if end < 0:
                return None
            span = text[start : end + 1]
            # 1) strict-tolerant parse (handles literal newlines/tabs in strings).
            try:
                obj = json.loads(span, strict=False)
            except json.JSONDecodeError:
                obj = None
            # 2) Repair LLM-mangled JSON (raw quotes/braces inside strings, etc.).
            #    json_repair is optional; fall back to the brace scan below if absent.
            if obj is None:
                try:
                    import json_repair  # type: ignore

                    obj = json_repair.loads(span)
                except Exception:
                    obj = None
        if not (isinstance(obj, dict) and "tool" in obj and isinstance(obj["tool"], str)):
            # Last-ditch rescue for file-writing tools whose JSON is too mangled
            # to parse: synthesize a valid action from the raw text below.
            if '"edit_file"' in text or '"file_write"' in text:
                obj = {"tool": "edit_file", "args": {}}
            else:
                return None
        # File-writing tools: make sure we have a path + the file contents, even
        # when the model emitted broken JSON, omitted the fence, or used an
        # unexpected key. We never let a write call go out without real content.
        if obj.get("tool") in ("edit_file", "file_write"):
            args = obj.setdefault("args", {})
            # Path: from parsed args, else regex the raw JSON/response.
            path = args.get("path") or args.get("filename") or args.get("file") or args.get("filepath")
            if not path:
                m = re.search(r'"path"\s*:\s*"([^"]*)"', text)
                if m:
                    path = m.group(1)
            if path:
                args["path"] = path
            # Content: parsed key, fenced block, post-JSON code, or a raw
            # content/new/insert_text/diff value pulled from the response text.
            content = (
                args.get("content") or args.get("new") or args.get("diff")
                or args.get("insert_text") or args.get("text") or ""
            )
            if not content:
                content = _extract_fenced_block(text)
            if not content:
                after = text[end + 1 :].strip() if end >= 0 else text.strip()
                if after and not after.startswith(("{", '"')) and _looks_like_code(after):
                    content = after
            if not content:
                content = _extract_raw_value(text, ("content", "new", "insert_text", "diff", "text"))
            if content:
                args["operation"] = args.get("operation") or "write"
                args["content"] = content
        return obj

    def _confirm(self, tool: Any, args: dict) -> bool:
        if self._ask_confirm is not None:
            return self._ask_confirm(f"{tool.name}({_short_args(args)}) [{tool.danger}]")
        # Default: auto-allow when confirmation disabled is handled by caller.
        return True


def _looks_like_code(s: str) -> bool:
    """Heuristic: does this text look like source code rather than prose?"""
    markers = ("def ", "class ", "import ", "print(", "return ", "=", "function", "public ", "var ", "#!/")
    return any(m in s for m in markers)


def _extract_fenced_block(text: str) -> Optional[str]:
    """Return the contents of the first ``` fenced code block in ``text``."""
    m = re.search(r"```[^\n]*\n(.*?)\n```", text, re.S)
    if m:
        return m.group(1)
    return None


def _extract_raw_value(text: str, keys: tuple[str, ...]) -> str:
    """Pull a string value for one of ``keys`` from JSON-ish text, tolerating
    raw quotes/braces inside the value (which break strict JSON). Best-effort:
    used only as a last resort for file-write content."""
    for key in keys:
        m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"(.*?)(?:"\,|"\}\s*\}|"\}\s*$)', text, re.S)
        if m:
            val = m.group(1)
            # Unescape the common sequences the model may have included.
            return val.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    return ""


def _parse_xml_action(text: str) -> Optional[dict[str, Any]]:
    """Parse Anthropic/XML-style tool calls, tolerating the many shapes models
    emit. The tool name may appear as <function=NAME>, <tool: NAME>, <tool>NAME</tool>,
    etc. Args may be <parameter=key>val</parameter>, <args><key>val</key></args>,
    or JSON inside <args>{...}</args>. Returns {"tool":..., "args":{...}}.
    """
    # 1) Tool name: <function=NAME> / <tool: NAME> / <tool=NAME> / <tool>NAME</tool>
    nm = re.search(r"<(?:function|tool)\b[:=>]?\s*([\w_-]+)", text)
    if not nm:
        # also accept <tool>NAME</tool> (NAME after the bare tag)
        nm = re.search(r"<(?:function|tool)>\s*([\w_-]+)\s*</(?:function|tool)>", text)
    if not nm:
        return None
    tool = nm.group(1)
    args: dict[str, Any] = {}
    # 2a) JSON object inside <args>{...}</args>
    jm = re.search(r"<args>\s*(\{.*?\})\s*</args>", text, re.S)
    if jm:
        try:
            inner = json.loads(jm.group(1))
            if isinstance(inner, dict):
                args.update(inner)
        except Exception:
            pass
    # 2b) <parameter=key>value</parameter>
    for pm in re.finditer(r"<parameter=([\w_-]+)>(.*?)</parameter>", text, re.S):
        args[pm.group(1)] = pm.group(2)
    # 2c) <key>value</key> pairs (inside or outside <args>). Scan the inner
    #     content of each <args> block separately, otherwise the greedy
    #     <args>...</args> match swallows its own children.
    segments = [text]
    for am in re.finditer(r"<args>(.*?)</args>", text, re.S):
        segments.append(am.group(1))
    for seg in segments:
        for pm in re.finditer(r"<([\w_-]+)>(.*?)</\1>", seg, re.S):
            if pm.group(1) in ("args", "tool", "function", "tool_call", "parameter"):
                continue
            args.setdefault(pm.group(1), pm.group(2))
    if not args and "<args>" in text:
        # <args> had no JSON and no <key>val</key>; grab its raw text as a hint
        raw = re.search(r"<args>(.*?)</args>", text, re.S)
        if raw:
            args["_raw"] = raw.group(1).strip()
    return {"tool": tool, "args": args}


def _short_args(args: dict, n: int = 60) -> str:
    s = json.dumps(args, default=str)
    return s if len(s) <= n else s[: n - 3] + "..."
