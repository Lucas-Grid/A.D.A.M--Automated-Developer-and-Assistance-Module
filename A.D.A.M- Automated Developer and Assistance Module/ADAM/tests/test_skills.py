"""Tests for skill engine."""
import pytest

from ADAM.skills.engine import get_skill_engine


@pytest.fixture()
def engine():
    from ADAM.skills.engine import get_skill_engine
    return get_skill_engine()


def test_list_skills(engine):
    skills = engine.list_skills()
    assert isinstance(skills, list)
    assert any(s["name"] == "system.status" for s in skills)
