"""Knowledge API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from ADAM.core.types import ResponseModel
from ADAM.knowledge.context import get_context_engine
from ADAM.knowledge.graph import VALID_ENTITY_TYPES, Entity, get_entity_store
from ADAM.knowledge.memory import get_knowledge_memory
from ADAM.knowledge.queries import get_query_engine
from ADAM.knowledge.relationships import VALID_RELATIONSHIP_TYPES
from ADAM.skills.engine import get_skill_engine

router = APIRouter()


@router.post("/entities", response_model=ResponseModel)
async def add_entity(entity_id: str, type: str, name: str, metadata: Optional[dict] = None):
    engine = get_skill_engine()
    result = await engine.execute("knowledge.add_entity", {"entity_id": entity_id, "type": type, "name": name, "metadata": metadata or {}})
    return ResponseModel(ok=result["ok"], data=result)


@router.get("/entities/{entity_id}", response_model=ResponseModel)
def get_entity(entity_id: str):
    store = get_entity_store()
    entity = store.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return ResponseModel(ok=True, data={"entity": entity.to_dict()})


@router.post("/relationships", response_model=ResponseModel)
async def add_relationship(source_id: str, target_id: str, type: str, metadata: Optional[dict] = None):
    engine = get_skill_engine()
    result = await engine.execute(
        "knowledge.add_relationship",
        {"source_id": source_id, "target_id": target_id, "type": type, "metadata": metadata or {}},
    )
    return ResponseModel(ok=result["ok"], data=result)


@router.get("/search", response_model=ResponseModel)
def search_knowledge(q: str, entity_type: Optional[str] = None):
    engine = get_query_engine()
    results = engine.search(q, entity_type=entity_type)
    return ResponseModel(ok=True, data={"results": results})


@router.get("/context/{entity_id}", response_model=ResponseModel)
def get_context(entity_id: str, depth: int = 2):
    engine = get_context_engine()
    context = engine.build_context(entity_id, depth=depth)
    return ResponseModel(ok=True, data={"context": context})
