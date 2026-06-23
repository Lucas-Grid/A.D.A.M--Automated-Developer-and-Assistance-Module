"""LLM types for ADAM OS."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    role: MessageRole
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: int = 0
    stop_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    content: str
    done: bool = False
    model: str = ""
    provider: str = ""
