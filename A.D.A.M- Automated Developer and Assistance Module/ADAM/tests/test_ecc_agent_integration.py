"""Tests for agent integration with ECC."""
import os
import tempfile

import pytest

from ADAM.agents.agent import Agent
from ADAM.agents.lifecycle import AgentLifecycle
from ADAM.agents.registry import get_agent_registry, reset_agent_registry
from ADAM.core.config import reset_settings, get_settings
from ADAM.skills.engine import get_skill_engine


@pytest.fixture()
def lifecycle(monkeypatch):
    db = tempfile.mktemp(suffix=".db")
    monkeypatch.setenv("ADAM_DB_PATH", db)
    reset_settings()
    reset_agent_registry()
    get_skill_engine().discover()
    return AgentLifecycle()


@pytest.mark.asyncio
async def test_agent_lifecycle_uses_ecc(lifecycle):
    registry = get_agent_registry()
    registry.create({
        "id": "agent-ecc-test",
        "name": "ECC Test Agent",
        "role": "tester",
        "description": "Test ECC integration",
        "enabled": True,
        "metadata": {},
    })
    result = await lifecycle.start("agent-ecc-test", "system status")
    assert "plan" in result
    assert "execution" in result
