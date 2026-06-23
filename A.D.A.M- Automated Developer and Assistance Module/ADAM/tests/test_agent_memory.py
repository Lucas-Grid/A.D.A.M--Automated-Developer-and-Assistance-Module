"""Tests for agent memory."""
import pytest

from ADAM.agents.memory import AgentMemory


@pytest.fixture()
def agent_memory():
    return AgentMemory(agent_id="agent-1")


def test_agent_memory_set_get(agent_memory):
    agent_memory.set("foo", {"bar": 1})
    assert agent_memory.get("foo") == {"bar": 1}


def test_agent_memory_history(agent_memory):
    agent_memory.add_history({"event": "started"})
    history = agent_memory.get_history()
    assert len(history) >= 1
    assert history[-1]["event"] == "started"


def test_agent_memory_clear(agent_memory):
    agent_memory.set("foo", {"bar": 1})
    agent_memory.add_history({"event": "started"})
    agent_memory.clear()
    assert agent_memory.get("foo") is None
    assert agent_memory.get_history() == []
