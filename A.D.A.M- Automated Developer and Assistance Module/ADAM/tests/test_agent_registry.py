"""Tests for agent registry."""
import os

import pytest

from ADAM.agents.agent import Agent
from ADAM.agents.registry import AgentRegistry, get_agent_registry, reset_agent_registry
from ADAM.core.exceptions import AgentError
from ADAM.core.config import reset_settings, get_settings


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("ADAM_DB_PATH", str(db))
    reset_settings()
    reset_agent_registry()
    return get_agent_registry()


def test_create_and_get_agent(registry):
    agent = {
        "id": "agent-1",
        "name": "Test Agent",
        "role": "assistant",
        "description": "Test",
        "model_id": "model-1",
        "enabled": True,
        "metadata": {"key": "value"},
    }
    created = registry.create(agent)
    assert created["id"] == "agent-1"
    assert created["name"] == "Test Agent"
    fetched = registry.get("agent-1")
    assert fetched is not None
    assert fetched["role"] == "assistant"


def test_list_agents(registry):
    registry.create({"id": "a1", "name": "A1", "role": "assistant"})
    registry.create({"id": "a2", "name": "A2", "role": "researcher"})
    all_agents = registry.list_agents()
    assert len(all_agents) == 2


def test_update_agent(registry):
    registry.create({"id": "a1", "name": "A1", "role": "assistant"})
    updated = registry.update("a1", {"name": "A1 Updated"})
    assert updated["name"] == "A1 Updated"


def test_delete_agent(registry):
    registry.create({"id": "a1", "name": "A1", "role": "assistant"})
    registry.delete("a1")
    assert registry.get("a1") is None
