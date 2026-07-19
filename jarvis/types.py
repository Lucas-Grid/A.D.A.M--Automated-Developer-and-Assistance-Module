"""Shared data types for Jarvis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Message:
    """A single conversation turn.

    role is one of: system, user, assistant, tool.
    For tool messages, ``tool_name`` identifies which tool produced it.
    """

    role: str
    content: str
    tool_name: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_name:
            d["tool_name"] = self.tool_name
        return d


@dataclass
class GenerationResult:
    """Result returned by an LLM provider."""

    text: str
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw: Any = None
    cached: bool = False  # True when served from the §4.3 response cache


@dataclass
class ToolResult:
    """Result returned by a tool execution."""

    ok: bool
    output: str
    tool: str = ""
    error: Optional[str] = None

    def to_message(self) -> Message:
        return Message(
            role="tool",
            content=self.output if self.ok else f"ERROR: {self.error}",
            tool_name=self.tool or None,
        )

    def format_for_prompt(self) -> str:
        status = "OK" if self.ok else "ERROR"
        if self.ok:
            return f"[{self.tool} -> {status}] {self.output}"
        return f"[{self.tool} -> {status}] {self.error or self.output or '(no detail)'}"


@dataclass
class Action:
    """A tool-call parsed from model output."""

    tool: str
    args: dict[str, Any]
