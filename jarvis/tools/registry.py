"""Tool registry and the Tool protocol.

A Tool is any callable object with a ``name``, a ``description``, and a
``run(ctx, **args) -> ToolResult`` method. Tools declare a ``danger`` level so
the orchestrator can require human confirmation for risky operations. New
skills are added by registering an instance -- no core changes needed.
"""
from __future__ import annotations

from typing import Any, Callable

from jarvis.types import ToolResult


class Tool:
    name: str = "unnamed"
    description: str = ""
    danger: str = "safe"  # safe | moderate | high
    schema: dict[str, Any] = {}
    # §3.1: each tool declares required permissions and a sandbox profile so
    # the orchestrator/executor can gate and isolate it. Kept declarative and
    # optional so existing tools keep working. Permissions use a plain mutable
    # default (never mutated in place) because Tool is a plain class, not a
    # dataclass -- dataclasses.field would leak a Field object into spec().
    permissions: list[str] = []
    sandbox_profile: str = "none"  # none | inprocess | docker

    def run(self, ctx: "ToolContext", **args: Any) -> ToolResult:  # pragma: no cover
        raise NotImplementedError

    def spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "danger": self.danger,
            "schema": self.schema,
            "permissions": self.permissions,
            "sandbox_profile": self.sandbox_profile,
        }


class FunctionTool(Tool):
    """Wrap a plain function as a Tool."""

    def __init__(
        self,
        name: str,
        fn: Callable[..., ToolResult],
        description: str = "",
        danger: str = "safe",
        schema: dict[str, Any] | None = None,
        permissions: list[str] | None = None,
        sandbox_profile: str = "none",
    ) -> None:
        self.name = name
        self._fn = fn
        self.description = description
        self.danger = danger
        self.schema = schema or {}
        self.permissions = permissions or []
        self.sandbox_profile = sandbox_profile

    def run(self, ctx: "ToolContext", **args: Any) -> ToolResult:
        return self._fn(ctx, **args)


class ToolContext:
    """Per-request context handed to every tool.

    Carries the working directory, memory handle, and confirmation callback.
    """

    def __init__(
        self,
        workspace: str = ".",
        memory: Any = None,
        ask_confirm: Callable[[str], bool] | None = None,
        provider_info: dict[str, Any] | None = None,
    ) -> None:
        self.workspace = workspace
        self.memory = memory
        self.ask_confirm = ask_confirm
        self.provider_info = provider_info or {}

    def confirm(self, message: str) -> bool:
        if self.ask_confirm is None:
            return True
        return self.ask_confirm(message)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def catalogue(self) -> str:
        lines = []
        for t in self._tools.values():
            d = f" [{t.danger}]" if t.danger != "safe" else ""
            lines.append(f"- {t.name}{d} ({t.description})")
        return "\n".join(lines)

    def names(self) -> list[str]:
        return list(self._tools.keys())


# --- convenient decorator ----------------------------------------------------
_REG: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    global _REG
    if _REG is None:
        _REG = ToolRegistry()
    return _REG


def tool(name: str, description: str = "", danger: str = "safe", schema: dict[str, Any] | None = None):
    """Decorator to register a function as a tool."""

    def deco(fn: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
        get_registry().register(FunctionTool(name, fn, description, danger, schema))
        return fn

    return deco
