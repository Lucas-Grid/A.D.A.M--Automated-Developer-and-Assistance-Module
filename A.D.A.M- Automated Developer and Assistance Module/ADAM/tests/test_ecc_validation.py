"""Tests for ECC validation."""
import os

import pytest

from ADAM.core.config import reset_settings, get_settings
from ADAM.ecc.planning import ECCPlan
from ADAM.ecc.validation import ECCValidation


@pytest.fixture()
def validation():
    return ECCValidation()


def test_validate_valid_plan(validation):
    plan = ECCPlan(agent_id="a", objective="search", goals=["search"], steps=[{"skill": "knowledge.search"}])
    result = validation.validate_plan(plan)
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_missing_skill(validation):
    plan = ECCPlan(agent_id="a", objective="search", goals=["search"], steps=[{"skill": "nonexistent.skill"}])
    result = validation.validate_plan(plan)
    assert result["valid"] is False
    assert len(result["errors"]) > 0
