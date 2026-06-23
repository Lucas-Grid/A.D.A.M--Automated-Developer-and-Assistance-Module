"""Tests for agent planner."""
import pytest

from ADAM.agents.planner import Planner


@pytest.fixture()
def planner():
    return Planner()


def test_planner_returns_plan(planner):
    plan = planner.plan("agent-1", "search the knowledge graph", ["knowledge.search", "vector.search", "context.build", "system.status"])
    assert plan.agent_id == "agent-1"
    assert plan.objective == "search the knowledge graph"
    assert len(plan.steps) >= 1
