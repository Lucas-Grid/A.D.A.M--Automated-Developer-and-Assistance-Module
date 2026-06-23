"""Tests for agent runtime."""
import os

import pytest

from ADAM.agents.agent import Agent
from ADAM.agents.memory import AgentMemory
from ADAM.agents.registry import get_agent_registry, reset_agent_registry
from ADAM.agents.runtime import AgentRuntime
from ADAM.core.exceptions import AgentError
from ADAM.core.config import reset_settings
from ADAM.skills.engine import get_skill_engine


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("ADAM_DB_PATH", str(db))
    reset_settings()
    reset_agent_registry()
    registry = get_agent_registry()
    registry.create({
        "id": "agent-1",
        "name": "Test Agent",
        "role": "assistant",
        "enabled": True,
    })
    return registry


def test_runtime_executes_plan(registry):
    from ADAM.agents.planner import Planner
    planner = Planner()
    plan = planner.plan("agent-1", "get system status", ["system.status"])
    runtime = AgentRuntime()
    import asyncio
    result = asyncio.run(runtime.run("agent-1", plan))
    assert result["agent_id"] == "agent-1"
    assert result["status"] == "completed"
