"""LLM skills for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.core.exceptions import ProviderError
from ADAM.llm.client import LLMClient
from ADAM.llm.router import LLMRouter
from ADAM.llm.telemetry import LLMTelemetry
from ADAM.llm.types import ChatMessage, MessageRole
from ADAM.skills.base import BaseSkill


class LLMChatSkill(BaseSkill):
    name = "llm.chat"
    description = "Unified chat completion across providers"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        client = LLMClient()
        messages = [
            ChatMessage(role=MessageRole(m["role"]), content=m["content"])
            for m in params.get("messages", [])
        ]
        response = client.chat(messages, model_id=params.get("model_id"))
        return {
            "ok": True,
            "data": {
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "tokens_used": response.tokens_used,
                "latency_ms": response.latency_ms,
            },
        }


class LLMStreamSkill(BaseSkill):
    name = "llm.stream"
    description = "Stream chat completion tokens"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        client = LLMClient()
        messages = [
            ChatMessage(role=MessageRole(m["role"]), content=m["content"])
            for m in params.get("messages", [])
        ]
        tokens: list[str] = []
        for chunk in client.stream(messages, model_id=params.get("model_id")):
            tokens.append(chunk.get("content", ""))
        return {
            "ok": True,
            "data": {
                "content": "".join(tokens),
                "model": params.get("model_id", "unknown"),
            },
        }


class LLMHealthSkill(BaseSkill):
    name = "llm.health"
    description = "Check provider/model health via model registry"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        router = LLMRouter()
        try:
            model = router.select(preferred_model=params.get("model_id"))
            return {"ok": True, "data": {"status": "healthy", "model": model}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


class LLMRouteSkill(BaseSkill):
    name = "llm.route"
    description = "Route request to best available model"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        router = LLMRouter()
        model = router.select(task_type=params.get("task_type", "chat"), preferred_model=params.get("model_id"))
        return {"ok": True, "data": model}
