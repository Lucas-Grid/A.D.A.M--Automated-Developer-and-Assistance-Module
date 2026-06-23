"""Tests for knowledge API endpoints."""
import os

import pytest
from fastapi.testclient import TestClient

from ADAM.api.v1.router import api_router
from ADAM.core.app import create_app
from ADAM.knowledge.graph import Entity, get_entity_store, reset_entity_store
from ADAM.knowledge.memory import get_knowledge_memory, reset_knowledge_memory
from ADAM.knowledge.queries import get_query_engine, reset_query_engine


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_entity_store()
    reset_query_engine()
    reset_knowledge_memory()
    import os
    os.environ["ADAM_DB_PATH"] = str(tmp_path / "test.db")
    app = create_app()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app)


def test_add_entity_via_api(client):
    resp = client.post("/api/v1/knowledge/entities", params={"entity_id": "e1", "type": "project", "name": "My Project"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["result"]["entity"]["entity_id"] == "e1"


def test_get_entity_via_api(client):
    client.post("/api/v1/knowledge/entities", params={"entity_id": "e1", "type": "project", "name": "My Project"})
    resp = client.get("/api/v1/knowledge/entities/e1")
    assert resp.status_code == 200
    assert resp.json()["data"]["entity"]["name"] == "My Project"
