"""Tests for knowledge graph storage."""
import os

import pytest

from ADAM.core.exceptions import KnowledgeGraphError
from ADAM.knowledge.graph import Entity, EntityStore, VALID_ENTITY_TYPES, get_entity_store, reset_entity_store


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_entity_store()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    return EntityStore()


def test_add_and_get_entity(store):
    entity = store.add_entity(Entity(entity_id="e1", type="project", name="My Project"))
    loaded = store.get_entity("e1")
    assert loaded is not None
    assert loaded.name == "My Project"
    assert loaded.type == "project"


def test_invalid_entity_type_rejected():
    store = EntityStore()
    with pytest.raises(KnowledgeGraphError):
        store.add_entity(Entity(entity_id="e1", type="invalid_type", name="Bad"))


def test_search_entities(store):
    store.add_entity(Entity(entity_id="e1", type="project", name="Alpha"))
    store.add_entity(Entity(entity_id="e2", type="workspace", name="Beta"))
    results = store.search("alpha")
    assert len(results) == 1
    assert results[0].entity_id == "e1"


def test_add_relationship(store):
    store.add_entity(Entity(entity_id="e1", type="workspace", name="WS"))
    store.add_entity(Entity(entity_id="e2", type="model", name="Model"))
    rel = store.add_relationship("e1", "e2", "USES")
    assert rel["type"] == "USES"
    assert rel["source_id"] == "e1"
    assert rel["target_id"] == "e2"
