"""AI Ops API endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from ADAM.aiops.context_builder import ContextBuilder
from ADAM.aiops.embeddings import get_embedding_provider
from ADAM.aiops.memory_index import MemoryIndexer
from ADAM.aiops.retrieval import Retriever
from ADAM.aiops.vector_store import VectorStore
from ADAM.core.config import get_settings
from ADAM.core.types import ResponseModel
from ADAM.skills.engine import get_skill_engine

router = APIRouter()


def _get_vector_store() -> VectorStore:
    settings = get_settings()
    persist_dir = str(settings.data_dir / "vector_store")
    return VectorStore(persist_directory=persist_dir)


@router.post("/index", response_model=ResponseModel)
async def index_documents(documents: list[str], ids: Optional[list[str]] = None, metadatas: Optional[list[dict]] = None):
    engine = get_skill_engine()
    params = {"documents": documents}
    if ids:
        params["ids"] = ids
    if metadatas:
        params["metadatas"] = metadatas
    result = await engine.execute("vector.index", params)
    return ResponseModel(ok=result["ok"], data=result)


@router.get("/search", response_model=ResponseModel)
async def search_vector(q: str, top_k: int = 5):
    engine = get_skill_engine()
    result = await engine.execute("vector.search", {"query": q, "top_k": top_k})
    return ResponseModel(ok=result["ok"], data=result)


@router.post("/context/build", response_model=ResponseModel)
async def build_context(query: str, entity_id: Optional[str] = None, top_k: int = 5):
    engine = get_skill_engine()
    params = {"query": query, "top_k": top_k}
    if entity_id:
        params["entity_id"] = entity_id
    result = await engine.execute("context.build", params)
    return ResponseModel(ok=result["ok"], data=result)
