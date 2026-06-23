"""Tests for automation memory integration."""
import os

import pytest

from ADAM.automations.history import JobHistory, reset_job_history
from ADAM.automations.memory import AutomationMemory, reset_automation_memory
from ADAM.automations.registry import AutomationRegistry, reset_automation_registry
from ADAM.automations.workflow import Workflow, WorkflowStore, reset_workflow_store
from ADAM.memory.store import get_memory, reset_memory


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_settings()
    reset_automation_registry()
    reset_workflow_store()
    reset_job_history()
    reset_automation_memory()
    reset_memory()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))


def test_memory_integration(env):
    registry = AutomationRegistry()
    workflow_store = WorkflowStore()
    wf = workflow_store.create(Workflow(workflow_id="wf1", steps=["system.status"]))
    auto = registry.create(
        {
            "automation_id": "auto1",
            "name": "Memory Test",
            "trigger_type": "manual",
            "trigger_config": {},
            "workflow_id": "wf1",
        }
    )

    history = JobHistory()
    history.record(
        {
            "job_id": "job1",
            "workflow_id": "wf1",
            "start_time": "2026-06-22T00:00:00",
            "success": True,
            "output_summary": {"ok": True},
        }
    )

    memory = AutomationMemory()
    memory.record_last_run("wf1", "job1")
    memory.record_failure("wf1", "sample error")

    last = memory.get_last_run("wf1")
    assert last is not None
    assert last["job_id"] == "job1"
