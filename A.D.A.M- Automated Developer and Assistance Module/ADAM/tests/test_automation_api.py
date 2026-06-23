"""Tests for automation API endpoints."""
import os
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.automations.registry import get_automation_registry, reset_automation_registry
from ADAM.core.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_automation_registry()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_list_automations_empty(client):
    resp = client.get("/api/v1/automations/")
    assert resp.status_code == 200
    assert resp.json()["data"]["automations"] == []


def test_create_and_run_automation_via_api(client):
    registry = get_automation_registry()
    registry.create(
        {
            "automation_id": "auto-api-1",
            "name": "API Created",
            "description": "Created via API tests",
            "enabled": True,
            "trigger_type": "manual",
            "trigger_config": {},
            "workflow_id": "builtins.system.status",
        }
    )

    resp = client.get("/api/v1/automations/")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]["automations"]) == 1
    assert body["data"]["automations"][0]["automation_id"] == "auto-api-1"
