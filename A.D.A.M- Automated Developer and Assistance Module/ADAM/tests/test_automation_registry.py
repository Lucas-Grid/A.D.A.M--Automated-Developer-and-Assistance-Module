"""Tests for automations registry."""
import os

import pytest

from ADAM.automations.registry import AutomationRegistry, reset_automation_registry


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_automation_registry()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    return AutomationRegistry()


def test_create_automation(registry):
    item = registry.create(
        {
            "automation_id": "auto1",
            "name": "Nightly Scan",
            "description": "Scan workspace nightly",
            "enabled": True,
            "trigger_type": "schedule",
            "trigger_config": {"cron": "0 2 * * *"},
            "workflow_id": "nightly_workspace_scan",
        }
    )
    assert item["automation_id"] == "auto1"
    assert item["enabled"] == 1


def test_get_automation(registry):
    registry.create(
        {
            "automation_id": "auto1",
            "name": "Nightly Scan",
            "trigger_type": "schedule",
            "trigger_config": {"cron": "0 2 * * *"},
            "workflow_id": "nightly_workspace_scan",
        }
    )
    item = registry.get("auto1")
    assert item["name"] == "Nightly Scan"


def test_list_automations(registry):
    registry.create(
        {
            "automation_id": "auto1",
            "name": "Scan",
            "trigger_type": "schedule",
            "trigger_config": {},
            "workflow_id": "wf1",
        }
    )
    registry.create(
        {
            "automation_id": "auto2",
            "name": "Alert",
            "trigger_type": "startup",
            "trigger_config": {},
            "workflow_id": "wf2",
        }
    )
    all_items = registry.list_automations()
    assert len(all_items) == 2
    startup_items = registry.list_automations(trigger_type="startup")
    assert len(startup_items) == 1


def test_update_automation(registry):
    registry.create(
        {
            "automation_id": "auto1",
            "name": "Scan",
            "trigger_type": "schedule",
            "trigger_config": {},
            "workflow_id": "wf1",
        }
    )
    updated = registry.update("auto1", {"enabled": False})
    assert updated["enabled"] == 0


def test_delete_automation(registry):
    registry.create(
        {
            "automation_id": "auto1",
            "name": "Scan",
            "trigger_type": "schedule",
            "trigger_config": {},
            "workflow_id": "wf1",
        }
    )
    registry.delete("auto1")
    assert registry.get("auto1") is None
