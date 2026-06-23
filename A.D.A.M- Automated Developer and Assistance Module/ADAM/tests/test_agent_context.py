"""Tests for agent context assembly."""
import os

import pytest

from ADAM.agents.context import AgentContext
from ADAM.core.config import reset_settings


@pytest.fixture()
def context(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("ADAM_DB_PATH", str(db))
    reset_settings()
    return AgentContext()


def test_agent_context_build_package(context):
    import asyncio
    package = asyncio.run(context.build_for_agent("agent-1", "system status"))
    assert "agent_id" in package
    assert package["agent_id"] == "agent-1"
    assert "objective" in package
    assert "graph_context" in package
    assert "memory_context" in package
    assert "automation_context" in package
    assert "vector_context" in package
    assert "workspace_context" in package
