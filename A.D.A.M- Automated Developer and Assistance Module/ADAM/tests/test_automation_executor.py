"""Tests for automation execution engine."""
import os

import pytest

from ADAM.automations.executor import ExecutionEngine, reset_execution_engine


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_execution_engine()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    return ExecutionEngine()


@pytest.mark.asyncio
async def test_execute_workflow_success(engine):
    result = await engine.execute_workflow("wf1", ["system.status"])
    assert result["success"] is True
    assert "results" in result
    assert result["workflow_id"] == "wf1"


@pytest.mark.asyncio
async def test_execute_workflow_failure_stops(engine):
    result = await engine.execute_workflow("wf1", ["nonexistent.skill", "system.status"])
    assert result["success"] is False
    assert len(result["results"]) >= 1
    first = result["results"][0]
    assert first["ok"] is False
    assert first["error"] is not None
