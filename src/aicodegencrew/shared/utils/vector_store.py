"""Vector Store abstraction layer — switch between ChromaDB and Qdrant via VECTOR_DB env var.

Usage:
    from aicodegencrew.shared.utils.vector_store import get_vector_store

    store = get_vector_store()
    store.upsert("repo_docs", ids, documents, embeddings, metadatas)
    results = store.query("repo_docs", query_embeddings, n_results=10)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class VectorStoreProtocol(Protocol):
    """Unified interface for vector store backends."""

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None: ...

    def query(
        self,
        collection_name: str,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def get(
        self,
        collection_name: str,
        where: dict[str, Any],
        limit: int = 0,
        include: list[str] | None = None,
    ) -> dict[str, Any]: ...

    def delete(
        self,
        collection_name: str,
        where: dict[str, Any],
    ) -> dict[str, Any]: ...

    def count(self, collection_name: str) -> int: ...


class ChromaVectorStore:
    """ChromaDB implementation of VectorStoreProtocol.

    Wraps the existing chroma_client helpers to conform to the unified interface.
    """

    def __init__(self, persistent_path: str | None = None):
        from .chroma_client import create_chroma_client

        self._client = create_chroma_client(persistent_path=persistent_path)

    def _get_or_create(self, name: str):
        return self._client.get_or_create_collection(name=name)

    def _get_if_exists(self, name: str):
        collections = self._client.list_collections()
        if name not in [c.name for c in collections]:
            return None
        return self._client.get_collection(name=name)

    def upsert(self, collection_name, ids, documents, embeddings, metadatas) -> None:
        col = self._get_or_create(collection_name)
        col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def query(self, collection_name, query_embeddings, n_results=10, where=None) -> dict[str, Any]:
        col = self._get_if_exists(collection_name)
        if col is None:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        kwargs: dict[str, Any] = {"query_embeddings": query_embeddings, "n_results": n_results}
        if where:
            kwargs["where"] = where
        kwargs["include"] = ["documents", "metadatas", "distances"]
        return col.query(**kwargs)

    def get(self, collection_name, where, limit=0, include=None) -> dict[str, Any]:
        col = self._get_if_exists(collection_name)
        if col is None:
            return {"ids": [], "documents": [], "metadatas": []}
        kwargs: dict[str, Any] = {}
        if where:
            kwargs["where"] = where
        if limit > 0:
            kwargs["limit"] = limit
        if include:
            kwargs["include"] = include
        return col.get(**kwargs)

    def delete(self, collection_name, where) -> dict[str, Any]:
        col = self._get_if_exists(collection_name)
        if col is None:
            return {"deleted": 0}
        col.delete(where=where)
        return {"deleted": 0}

    def count(self, collection_name) -> int:
        col = self._get_if_exists(collection_name)
        return col.count() if col else 0


def get_vector_store(persistent_path: str | None = None) -> VectorStoreProtocol:
    """Factory: return the configured vector store backend.

    Reads VECTOR_DB env var (default: "chroma"). When "qdrant", returns
    QdrantVectorClient; otherwise returns ChromaVectorStore.
    """
    backend = os.getenv("VECTOR_DB", "chroma").strip().lower()

    if backend == "qdrant":
        from .qdrant_client import QdrantVectorClient

        return QdrantVectorClient()

    return ChromaVectorStore(persistent_path=persistent_path)
