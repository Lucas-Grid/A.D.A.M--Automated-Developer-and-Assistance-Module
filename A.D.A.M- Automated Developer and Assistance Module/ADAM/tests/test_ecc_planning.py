"""Tests for ECC planning."""
import os

import pytest

from ADAM.core.config import reset_settings, get_settings
from ADAM.ecc.planning import ECCPlanner, ECCPlan


@pytest.fixture()
def planner():
    return ECCPlanner()


def test_planner_generates_plan(planner):
    plan = planner.plan(agent_id="agent-1", objective="search knowledge graph", available_skills=["knowledge.search", "system.status"])
    assert isinstance(plan, ECCPlan)
    assert plan.agent_id == "agent-1"
    assert plan.objective == "search knowledge graph"
    assert len(plan.steps) > 0
