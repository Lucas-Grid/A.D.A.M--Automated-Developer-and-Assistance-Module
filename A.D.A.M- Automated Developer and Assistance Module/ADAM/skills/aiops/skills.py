"""AI Ops skills for ADAM OS."""
from __future__ import annotations

from typing import Any

from ADAM.aiops.context_builder import ContextBuilder
from ADAM.aiops.embeddings import get_embedding_provider
from ADAM.aiops.memory_index import MemoryIndexer
from ADAM.aiops.retrieval import Retriever
from ADAM.aiops.vector_store import VectorStore
from ADAM.core.exceptions import AIOpsError
from ADAM.skills.base import BaseSkill
from ADAM.core.config import get_settings


def _get_vector_store() -> VectorStore:
    settings = get_settings()
    persist_dir = str(settings.data_dir / "vector_store")
    return VectorStore(persist_directory=persist_dir)


def _get_indexer() -> MemoryIndexer:
    provider = get_embedding_provider("ollama")
    return MemoryIndexer(vector_store=_get_vector_store(), embedding_provider=provider)


class VectorIndexSkill(BaseSkill):
    name = "vector.index"
    description = "Index documents into the vector store"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        documents = params["documents"]
        ids = params.get("ids")
        metadatas = params.get("metadatas")

        if ids and len(ids) != len(documents):
            raise AIOpsError("ids length must match documents length")

        import uuid

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        provider = get_embedding_provider("ollama")
        embeddings = await provider.embed_batch(documents)

        store = _get_vector_store()
        store.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return {"indexed": len(ids)}


class VectorSearchSkill(BaseSkill):
    name = "vector.search"
    description = "Semantic search over the vector store"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params["query"]
        top_k = params.get("top_k", 5)

        provider = get_embedding_provider("ollama")
        store = _get_vector_store()
        retriever = Retriever(vector_store=store, embedding_provider=provider)
        results = await retriever.search(query, top_k=top_k)
        return {"results": results}


class ContextBuildSkill(BaseSkill):
    name = "context.build"
    description = "Build unified context package from multiple sources"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params["query"]
        entity_id = params.get("entity_id")
        top_k = params.get("top_k", 5)

        provider = get_embedding_provider("ollama")
        store = _get_vector_store()
        retriever = Retriever(vector_store=store, embedding_provider=provider)
        builder = ContextBuilder(retriever=retriever)
        package = await builder.build(query=query, entity_id=entity_id, top_k=top_k)
        return {"context": package}


class MemoryReindexSkill(BaseSkill):
    name = "memory.reindex"
    description = "Reindex all memory sources into the vector store"

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        indexer = _get_indexer()
        result = await indexer.reindex_all()
        return result
