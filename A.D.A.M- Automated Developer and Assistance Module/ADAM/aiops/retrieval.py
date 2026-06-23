"""Semantic retrieval over vector store."""
from __future__ import annotations

import logging
from typing import Any, Optional

from ADAM.aiops.embeddings import BaseEmbeddingProvider, get_embedding_provider
from ADAM.aiops.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Query the vector store using natural language."""

    def __init__(self, vector_store: VectorStore, embedding_provider: BaseEmbeddingProvider) -> None:
        self._store = vector_store
        self._embeddings = embedding_provider

    async def search(self, query: str, top_k: int = 5, metadata_filter: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Return top-k most similar documents."""
        query_vector = await self._embeddings.embed(query)
        results = self._store.search(query_vector, top_k=top_k, where=metadata_filter)
        items: list[dict[str, Any]] = []
        for doc, meta, dist in zip(results["documents"], results["metadatas"], results["distances"]):
            items.append(
                {
                    "document": doc,
                    "metadata": meta,
                    "score": 1 - dist,
                }
            )
        return items
