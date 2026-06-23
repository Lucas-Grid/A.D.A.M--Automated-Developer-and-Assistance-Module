"""LLM client: unified interface for agents, skills, and API."""
from __future__ import annotations

from typing import Any

from ADAM.llm.execution import LLMExecution
from ADAM.llm.types import ChatMessage, LLMResponse
from ADAM.llm.streaming import StreamHandler


class LLMClient:
    """Facade for LLM execution."""

    def __init__(self) -> None:
        self._execution = LLMExecution()
        self._stream = StreamHandler()

    def configure_providers(self, providers: list[Any]) -> None:
        self._execution.set_providers(providers)

    def chat(self, messages: list[ChatMessage], model_id: str | None = None, **kwargs: Any) -> LLMResponse:
        return self._execution.chat(messages, model_id=model_id, **kwargs)

    def stream(self, messages: list[ChatMessage], model_id: str | None = None, **kwargs: Any):
        yield from self._execution.stream(messages, model_id=model_id, **kwargs)
