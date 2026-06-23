"""Tests for workflow system."""
import os

import pytest

from ADAM.automations.workflow import Workflow, WorkflowStore, reset_workflow_store


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_workflow_store()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    return WorkflowStore()


def test_create_and_get_workflow(store):
    wf = store.create(Workflow(workflow_id="wf1", steps=["step1", "step2"]))
    loaded = store.get("wf1")
    assert loaded is not None
    assert loaded.workflow_id == "wf1"
    assert loaded.steps == ["step1", "step2"]


def test_list_workflows(store):
    store.create(Workflow(workflow_id="wf1", steps=["step1"]))
    store.create(Workflow(workflow_id="wf2", steps=["step2"]))
    items = store.list_workflows()
    assert len(items) == 2


def test_delete_workflow(store):
    store.create(Workflow(workflow_id="wf1", steps=["step1"]))
    store.delete("wf1")
    assert store.get("wf1") is None


def test_workflow_persistence(store):
    store.create(Workflow(workflow_id="wf1", steps=["step1"], metadata={"desc": "test"}))
    loaded = store.get("wf1")
    assert loaded.metadata == {"desc": "test"}
