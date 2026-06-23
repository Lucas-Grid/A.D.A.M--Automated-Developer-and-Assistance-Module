"""Memory indexing: ingest workspace summaries, knowledge, history, documents."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from ADAM.aiops.embeddings import BaseEmbeddingProvider, get_embedding_provider
from ADAM.aiops.vector_store import VectorStore
from ADAM.automations.history import get_job_history
from ADAM.knowledge.graph import get_entity_store
from ADAM.knowledge.queries import get_query_engine
from ADAM.memory.store import get_memory

logger = logging.getLogger(__name__)


class MemoryIndexer:
    """Index memory and knowledge data into the vector store."""

    def __init__(self, vector_store: VectorStore, embedding_provider: BaseEmbeddingProvider, batch_size: int = 64) -> None:
        self._store = vector_store
        self._embeddings = embedding_provider
        self._batch_size = batch_size

    async def index_memory(self, query: str = "", limit: int = 500) -> int:
        """Index memory entries into the vector store."""
        memory = get_memory()
        rows = memory.search(query or "", limit=limit)
        if not rows:
            return 0

        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []

        for row in rows:
            doc = f"{row['key']}: {row['value']}"
            ids.append(str(uuid.uuid4()))
            documents.append(doc)
            metadatas.append({"source": "memory", "key": row["key"]})

        for i in range(0, len(documents), self._batch_size):
            batch_docs = documents[i : i + self._batch_size]
            batch_emb = await self._embeddings.embed_batch(batch_docs)
            embeddings.extend(batch_emb)

        self._store.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return len(ids)

    async def index_knowledge_entities(self, entity_type: Optional[str] = None) -> int:
        """Index knowledge graph entities."""
        store = get_entity_store()
        entities = store.search("", entity_type=entity_type)
        if not entities:
            return 0

        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []

        for entity in entities:
            doc = f"{entity.type}: {entity.name}"
            ids.append(str(uuid.uuid4()))
            documents.append(doc)
            metadatas.append({"source": "knowledge", "entity_id": entity.entity_id, "type": entity.type})

        for i in range(0, len(documents), self._batch_size):
            batch_docs = documents[i : i + self._batch_size]
            batch_emb = await self._embeddings.embed_batch(batch_docs)
            embeddings.extend(batch_emb)

        self._store.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return len(ids)

    async def index_automation_history(self, workflow_id: Optional[str] = None, limit: int = 200) -> int:
        """Index automation job history."""
        history = get_job_history()
        jobs = history.list_jobs(workflow_id=workflow_id, success=None)[:limit]
        if not jobs:
            return 0

        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []

        for job in jobs:
            doc = f"Automation {job['workflow_id']}: {'succeeded' if job['success'] else 'failed'}"
            ids.append(str(uuid.uuid4()))
            documents.append(doc)
            metadatas.append({"source": "automation", "job_id": job["job_id"], "workflow_id": job["workflow_id"]})

        for i in range(0, len(documents), self._batch_size):
            batch_docs = documents[i : i + self._batch_size]
            batch_emb = await self._embeddings.embed_batch(batch_docs)
            embeddings.extend(batch_emb)

        self._store.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return len(ids)

    async def reindex_all(self) -> dict[str, int]:
        """Reindex all supported sources."""
        self._store.reset()
        memory_count = await self.index_memory()
        knowledge_count = await self.index_knowledge_entities()
        automation_count = await self.index_automation_history()
        return {"memory": memory_count, "knowledge": knowledge_count, "automation": automation_count}
