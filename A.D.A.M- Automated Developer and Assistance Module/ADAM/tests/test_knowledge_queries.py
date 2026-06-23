"""Tests for knowledge graph queries."""
import os

import pytest

from ADAM.knowledge.graph import Entity, EntityStore, get_entity_store, reset_entity_store
from ADAM.knowledge.queries import KnowledgeQueryEngine, get_query_engine, reset_query_engine
from ADAM.knowledge.relationships import VALID_RELATIONSHIP_TYPES


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_entity_store()
    reset_query_engine()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    return EntityStore()


def test_neighbors(store):
    store.add_entity(Entity(entity_id="e1", type="workspace", name="WS"))
    store.add_entity(Entity(entity_id="e2", type="model", name="Model"))
    store.add_relationship("e1", "e2", "USES")

    engine = get_query_engine()
    neighbors = engine.neighbors("e1")
    assert len(neighbors) == 1
    assert neighbors[0]["entity"]["entity_id"] == "e2"
    assert neighbors[0]["relationship"]["type"] == "USES"


def test_related_entities_filtered(store):
    store.add_entity(Entity(entity_id="e1", type="project", name="P"))
    store.add_entity(Entity(entity_id="e2", type="workspace", name="W"))
    store.add_entity(Entity(entity_id="e3", type="model", name="M"))
    store.add_relationship("e1", "e2", "OWNS")
    store.add_relationship("e1", "e3", "USES")

    engine = get_query_engine()
    owns = engine.related_entities("e1", rel_type="OWNS")
    assert len(owns) == 1
    assert owns[0]["entity"]["entity_id"] == "e2"


def test_search(store):
    store.add_entity(Entity(entity_id="e1", type="project", name="Alpha"))
    store.add_entity(Entity(entity_id="e2", type="workspace", name="Beta"))
    engine = get_query_engine()
    results = engine.search("alpha")
    assert len(results) == 1
    assert results[0]["entity_id"] == "e1"
