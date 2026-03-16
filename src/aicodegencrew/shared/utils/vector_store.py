"""Vector Store abstraction layer — Qdrant-only.

Usage:
    from aicodegencrew.shared.utils.vector_store import get_vector_store

    store = get_vector_store()
    store.upsert("repo_docs", ids, documents, embeddings, metadatas)
    results = store.query("repo_docs", query_embeddings, n_results=10)
"""

from __future__ import annotations

import logging
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


def get_vector_store(persistent_path: str | None = None) -> VectorStoreProtocol:
    """Factory: return the Qdrant vector store backend.

    The *persistent_path* parameter is accepted for backward compatibility
    but ignored — Qdrant uses its own server URL from QDRANT_URL env var.
    """
    from .qdrant_client import QdrantVectorClient

    return QdrantVectorClient()
