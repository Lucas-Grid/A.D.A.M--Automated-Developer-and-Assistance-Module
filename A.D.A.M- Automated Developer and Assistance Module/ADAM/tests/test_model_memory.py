"""Tests for model memory integration."""
import asyncio
import pytest

from ADAM.connections.model_registry import ModelRegistry, reset_model_registry
from ADAM.skills.model.skills import ModelSelectSkill
from ADAM.memory.store import get_memory, reset_memory


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_model_registry()
    import os
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    return ModelRegistry()


@pytest.fixture()
def memory(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_memory()
    import os
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    return get_memory()


def test_select_persists_to_memory(registry, memory):
    registry.register(
        {
            "model_id": "m1",
            "provider": "ollama",
            "display_name": "M1",
            "local_or_remote": "local",
            "supports_chat": True,
        }
    )
    skill = ModelSelectSkill()
    result = asyncio.run(skill.execute({"model_id": "m1"}))
    assert result["selected"]["model_id"] == "m1"
    assert memory.get("models.selected")["value"] == "m1"
