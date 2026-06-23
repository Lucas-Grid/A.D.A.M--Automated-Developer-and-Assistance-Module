"""Tests for ECC memory."""
import os
import tempfile

import pytest

from ADAM.core.config import reset_settings
from ADAM.ecc.memory import ECCMemory
from ADAM.memory.store import reset_memory


@pytest.fixture()
def ecc_memory(monkeypatch):
    db = tempfile.mktemp(suffix=".db")
    monkeypatch.setenv("ADAM_DB_PATH", db)
    reset_settings()
    reset_memory()
    return ECCMemory()


def test_ecc_memory_observations(ecc_memory):
    ecc_memory.add_observation({"event": "test"})
    obs = ecc_memory.get_observations()
    assert len(obs) == 1
    assert obs[0]["event"] == "test"


def test_ecc_memory_reflections(ecc_memory):
    ecc_memory.add_reflection({"success": True})
    refs = ecc_memory.get_reflections()
    assert len(refs) == 1
    assert refs[0]["success"] is True


def test_ecc_memory_lessons(ecc_memory):
    ecc_memory.add_lesson("retry on failure")
    lessons = ecc_memory.get_lessons()
    assert len(lessons) == 1
    assert lessons[0]["lesson"] == "retry on failure"


def test_ecc_memory_decisions(ecc_memory):
    ecc_memory.add_decision({"choice": "model-a"})
    decs = ecc_memory.get_decisions()
    assert len(decs) == 1
    assert decs[0]["choice"] == "model-a"
