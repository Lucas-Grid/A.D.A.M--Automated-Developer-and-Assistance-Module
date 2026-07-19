"""Lightweight vector memory for Jarvis (folds ADAM's semantic recall in).

Design choices (dependency-light, no ChromaDB/numpy):
  * Storage is SQLite (already a project dependency) — one table of
    (id, collection, text, embedding blob, metadata_json, ts).
  * Embeddings come from an OpenAI-compatible embeddings endpoint. The default
    is NVIDIA NIM (nvidia/nv-embed-v1) — matching Jarvis's "NIM is the main
    provider" directive — configured via NVIDIA_NIM_API_KEY. Ollama
    (nomic-embed-text) and any OpenAI-compatible endpoint also work.
  * Similarity search is pure-Python cosine over the stored vectors.
  * If no embedding provider is reachable, the store degrades gracefully to
    substring search so semantic tools still function (just less precisely).

This mirrors ADAM's VectorStore + embedding providers but without the heavy
ChromaDB dependency.
"""
from __future__ import annotations

import json
import os
import sqlite3
import struct
import time
from typing import Any, Optional, Sequence

import requests


# --------------------------------------------------------------------------
# Embedding client (OpenAI-compatible). Sync + requests-only.
# --------------------------------------------------------------------------
class Embedder:
    """Tiny OpenAI-compatible embeddings client. No SDK required."""

    def __init__(
        self,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_key: str = "",
        model: str = "nvidia/nv-embed-v1",
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise RuntimeError("no embedding API key configured")
        resp = requests.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "input": texts},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        # Normalise: NIM returns "embedding", some return "vector".
        return [d.get("embedding") or d.get("vector") for d in data]

    @classmethod
    def from_env(cls, model: str = "nvidia/nv-embed-v1") -> "Embedder":
        key = os.environ.get("NVIDIA_NIM_API_KEY", "")
        if key:
            return cls("https://integrate.api.nvidia.com/v1", key, model)
        # Fall back to a local Ollama embedder if present.
        return cls("http://localhost:11434/v1", "", "nomic-embed-text")


# --------------------------------------------------------------------------
# Vector store (SQLite-backed, pure-Python cosine).
# --------------------------------------------------------------------------
def _pack(vec: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(vec)}d", *vec)


def _unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 8}d", blob))


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorMemory:
    """SQLite-backed semantic memory with optional embedding-based recall."""

    def __init__(self, db_path: str = "jarvis_vector.db", embedder: Optional[Embedder] = None) -> None:
        self.db_path = db_path
        self._embedder = embedder
        self._have_embed = embedder is not None
        conn = sqlite3.connect(db_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS vectors (
                   id TEXT PRIMARY KEY,
                   collection TEXT NOT NULL,
                   text TEXT NOT NULL,
                   embedding BLOB,
                   metadata TEXT,
                   ts REAL NOT NULL
               )"""
        )
        conn.commit()
        conn.close()

    def _embedder_available(self) -> bool:
        if self._have_embed and self._embedder is not None:
            return True
        if self._embedder is None:
            try:
                self._embedder = Embedder.from_env()
                self._have_embed = True
            except Exception:
                self._have_embed = False
        return self._have_embed and self._embedder is not None

    def remember(self, text: str, collection: str = "default", key: Optional[str] = None,
                 metadata: Optional[dict] = None) -> str:
        cid = key or f"{collection}:{int(time.time()*1000)}:{abs(hash(text))%10**8}"
        vec = None
        if self._embedder_available() and self._embedder is not None:
            try:
                vec = self._embedder.embed([text])[0]
            except Exception:
                vec = None
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO vectors (id, collection, text, embedding, metadata, ts) "
            "VALUES (?,?,?,?,?,?)",
            (cid, collection, text, _pack(vec) if vec else None,
             json.dumps(metadata or {}), time.time()),
        )
        conn.commit()
        conn.close()
        return cid

    def recall(self, query: str, collection: str = "default", top_k: int = 5) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        if collection:
            rows = conn.execute(
                "SELECT id, collection, text, embedding, metadata FROM vectors WHERE collection=? ORDER BY ts DESC",
                (collection,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, collection, text, embedding, metadata FROM vectors ORDER BY ts DESC"
            ).fetchall()
        conn.close()
        if not rows:
            return []

        # Embedding-based search when possible.
        if self._embedder_available() and self._embedder is not None:
            try:
                qvec = self._embedder.embed([query])[0]
                scored = []
                for rid, rcol, rtext, rvec, rmeta in rows:
                    if rvec:
                        sim = _cosine(qvec, _unpack(rvec))
                        scored.append((sim, rid, rcol, rtext, rmeta))
                if scored:
                    scored.sort(key=lambda x: x[0], reverse=True)
                    return [
                        {"id": r[1], "collection": r[2], "text": r[3], "score": round(r[0], 4),
                         "metadata": json.loads(r[4] or "{}")}
                        for r in scored[:top_k]
                    ]
            except Exception:
                pass

        # Graceful fallback: substring / token overlap ranking.
        qlow = query.lower()
        qtokens = set(qlow.split())
        scored = []
        for rid, rcol, rtext, _rvec, rmeta in rows:
            rlow = rtext.lower()
            if qlow in rlow:
                score = 1.0
            elif qtokens:
                overlap = sum(1 for t in qtokens if t in rlow)
                score = overlap / len(qtokens)
            else:
                score = 0.0
            scored.append((score, rid, rcol, rtext, rmeta))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": r[1], "collection": r[2], "text": r[3], "score": round(r[0], 4),
             "metadata": json.loads(r[4] or "{}")}
            for r in scored[:top_k] if r[0] > 0
        ]

    def count(self, collection: str = "") -> int:
        conn = sqlite3.connect(self.db_path)
        if collection:
            n = conn.execute("SELECT COUNT(*) FROM vectors WHERE collection=?", (collection,)).fetchone()[0]
        else:
            n = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        conn.close()
        return n
