"""Tests for model registry and providers."""
import os

import pytest

from ADAM.core.exceptions import ModelRegistryError
from ADAM.connections.model_registry import ModelRegistry, reset_model_registry


@pytest.fixture()
def model_registry(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_model_registry()
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    return ModelRegistry()


def test_register_and_get(model_registry):
    model = {
        "model_id": "test-model",
        "provider": "ollama",
        "display_name": "Test Model",
        "local_or_remote": "local",
        "supports_chat": True,
        "supports_vision": False,
        "supports_embeddings": False,
        "supports_reasoning": False,
        "context_window": 4096,
        "availability_status": "available",
    }
    registered = model_registry.register(model)
    assert registered["model_id"] == "test-model"
    assert registered["provider"] == "ollama"

    fetched = model_registry.get("test-model")
    assert fetched is not None
    assert fetched["display_name"] == "Test Model"


def test_update_status(model_registry):
    model = {
        "model_id": "m1",
        "provider": "openai",
        "display_name": "M1",
        "local_or_remote": "remote",
    }
    model_registry.register(model)
    updated = model_registry.update_status("m1", "unavailable")
    assert updated["availability_status"] == "unavailable"


def test_list_models(model_registry):
    model_registry.register({"model_id": "m1", "provider": "ollama", "display_name": "M1", "local_or_remote": "local"})
    model_registry.register({"model_id": "m2", "provider": "openai", "display_name": "M2", "local_or_remote": "remote"})
    all_models = model_registry.list_models()
    assert len(all_models) == 2
    ollama_only = model_registry.list_models(provider="ollama")
    assert len(ollama_only) == 1


def test_delete(model_registry):
    model_registry.register({"model_id": "m1", "provider": "x", "display_name": "M1", "local_or_remote": "remote"})
    model_registry.delete("m1")
    assert model_registry.get("m1") is None
