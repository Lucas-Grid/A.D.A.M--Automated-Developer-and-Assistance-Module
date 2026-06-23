"""ChromaDB-backed vector store."""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError as exc:  # pragma: no cover
    raise ImportError("chromadb is required for aiops vector store") from exc


class VectorStore:
    """Thin wrapper over ChromaDB client."""

    def __init__(self, persist_directory: str, collection_name: str = "default") -> None:
        self._client = chromadb.PersistentClient(path=persist_directory, settings=ChromaSettings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    def add(self, ids: list[str], documents: list[str], embeddings: list[list[float]], metadatas: Optional[list[dict[str, Any]]] = None) -> None:
        self._collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def upsert(self, ids: list[str], documents: list[str], embeddings: list[list[float]], metadatas: Optional[list[dict[str, Any]]] = None) -> None:
        self._collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def search(self, query_embedding: list[float], top_k: int = 5, where: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        results = self._collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)
        formatted: dict[str, Any] = {
            "ids": results.get("ids", [[]])[0],
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        }
        return formatted

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(name=self._collection.name, metadata={"hnsw:space": "cosine"})
