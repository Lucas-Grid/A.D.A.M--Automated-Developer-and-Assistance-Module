"""Tests for ECC reflection."""
import os

import pytest

from ADAM.core.config import reset_settings, get_settings
from ADAM.ecc.memory import ECCMemory
from ADAM.ecc.planning import ECCPlan
from ADAM.ecc.reflection import ECCReflection


@pytest.fixture()
def reflection():
    return ECCReflection()


def test_reflect_successful_outcome(reflection):
    plan = ECCPlan(agent_id="a", objective="test", goals=["test"], steps=[{"skill": "system.status"}])
    outputs = [{"ok": True, "data": {}}]
    result = reflection.reflect(plan, outputs)
    assert result["success"] is True
    assert result["failures"] == 0


def test_reflect_failed_outcome(reflection):
    plan = ECCPlan(agent_id="a", objective="test", goals=["test"], steps=[{"skill": "system.status"}])
    outputs = [{"ok": False, "error": "boom"}]
    result = reflection.reflect(plan, outputs)
    assert result["success"] is False
    assert result["failures"] == 1
    assert len(result["improvements"]) > 0
