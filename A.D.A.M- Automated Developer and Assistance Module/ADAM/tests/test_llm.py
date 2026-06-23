"""Tests for llm client and router."""
import os
from typing import Any

import pytest

from ADAM.core.config import reset_settings, get_settings
from ADAM.llm.client import LLMClient
from ADAM.llm.router import LLMRouter
from ADAM.llm.telemetry import LLMTelemetry
from ADAM.llm.types import ChatMessage, MessageRole


class FakeProvider:
    name = "fake"

    def chat(self, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        return {"content": "fake response", "tokens_used": 10}

    def health(self) -> dict[str, Any]:
        return {"status": "healthy"}

    def list_models(self) -> list[dict[str, Any]]:
        return [{"model_id": model, "provider": self.name, "supports_chat": True} for model in ["fake-model"]]


@pytest.fixture()
def temp_settings(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("ADAM_DB_PATH", str(db))
    reset_settings()
    return get_settings()


def test_router_select_model(temp_settings):
    from ADAM.connections.model_registry import get_model_registry
    registry = get_model_registry()
    registry.register({"model_id": "test-model", "provider": "fake", "supports_chat": True, "availability_status": "available"})
    router = LLMRouter()
    model = router.select(preferred_model="test-model")
    assert model["model_id"] == "test-model"


def test_llm_client_chat(temp_settings):
    client = LLMClient()
    client.configure_providers([FakeProvider()])
    messages = [ChatMessage(role=MessageRole.USER, content="hi")]
    response = client.chat(messages)
    assert response.content == "fake response"
    assert response.provider == "fake"


def test_telemetry_records_call():
    telemetry = LLMTelemetry()
    telemetry.record_call(model="m", provider="p", latency_ms=42, tokens=10, success=True)
    # No exception = success
