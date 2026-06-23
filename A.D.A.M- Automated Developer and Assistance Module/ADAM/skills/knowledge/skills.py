"""Knowledge skills for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.core.exceptions import KnowledgeGraphError
from ADAM.knowledge.context import get_context_engine
from ADAM.knowledge.graph import Entity, VALID_ENTITY_TYPES, get_entity_store
from ADAM.knowledge.memory import get_knowledge_memory
from ADAM.knowledge.queries import get_query_engine
from ADAM.knowledge.relationships import VALID_RELATIONSHIP_TYPES
from ADAM.skills.base import BaseSkill


class KnowledgeAddEntitySkill(BaseSkill):
    name = "knowledge.add_entity"
    description = "Add or update a knowledge graph entity"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        entity_id = params["entity_id"]
        type_ = params["type"]
        name = params["name"]
        metadata = params.get("metadata", {})

        if type_ not in VALID_ENTITY_TYPES:
            raise KnowledgeGraphError(f"Unsupported entity type: {type_}")

        store = get_entity_store()
        existing = store.get_entity(entity_id)
        if existing:
            entity = Entity(
                entity_id=entity_id,
                type=type_,
                name=name,
                metadata={**existing.metadata, **metadata},
                created_at=existing.created_at,
            )
        else:
            entity = Entity(entity_id=entity_id, type=type_, name=name, metadata=metadata)

        store.add_entity(entity)
        get_knowledge_memory().record_entity(entity)
        return {"entity": entity.to_dict()}


class KnowledgeAddRelationshipSkill(BaseSkill):
    name = "knowledge.add_relationship"
    description = "Add a relationship between two entities"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        source_id = params["source_id"]
        target_id = params["target_id"]
        rel_type = params["type"]
        metadata = params.get("metadata", {})

        if rel_type not in VALID_RELATIONSHIP_TYPES:
            raise KnowledgeGraphError(f"Unsupported relationship type: {rel_type}")

        store = get_entity_store()
        if not store.get_entity(source_id):
            raise KnowledgeGraphError(f"Source entity '{source_id}' does not exist")
        if not store.get_entity(target_id):
            raise KnowledgeGraphError(f"Target entity '{target_id}' does not exist")

        rel = store.add_relationship(source_id, target_id, rel_type, metadata)
        get_knowledge_memory().record_relationship(rel)
        return {"relationship": rel}


class KnowledgeSearchSkill(BaseSkill):
    name = "knowledge.search"
    description = "Search knowledge graph entities"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params["query"]
        entity_type = params.get("entity_type")
        engine = get_query_engine()
        results = engine.search(query, entity_type=entity_type)
        return {"results": results}


class KnowledgeContextSkill(BaseSkill):
    name = "knowledge.context"
    description = "Build context package for an entity"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        entity_id = params["entity_id"]
        depth = params.get("depth", 2)
        engine = get_context_engine()
        context = engine.build_context(entity_id, depth=depth)
        return {"context": context}
