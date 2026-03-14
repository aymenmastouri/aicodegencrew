"""Qdrant vector store client — thread-safe singleton.

Implements the VectorStoreProtocol for Qdrant Cloud / on-prem.
All methods are no-op safe when qdrant-client is not installed.

Env vars:
    QDRANT_URL: Qdrant server URL (required)
    QDRANT_API_KEY: API key for authentication (optional)
    QDRANT_COLLECTION: Default collection name (default: repo_docs)
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_instance_lock = threading.Lock()
_instance: QdrantVectorClient | None = None


class QdrantVectorClient:
    """Qdrant implementation of VectorStoreProtocol. Thread-safe singleton."""

    def __init__(self):
        self._client = None
        self._url = os.getenv("QDRANT_URL", "").strip()
        self._api_key = os.getenv("QDRANT_API_KEY", "").strip() or None

        if not self._url:
            logger.warning("[Qdrant] QDRANT_URL not set — Qdrant operations will fail")
            return

        try:
            # On-prem platforms use self-signed CAs. truststore injects the OS
            # cert store into Python's ssl module, but qdrant-client uses httpx
            # which needs an explicit ssl context to pick up the injected certs.
            # Also: qdrant-client needs host+port (not a full URL) for HTTPS to
            # connect to port 443 instead of the default gRPC port 6334.
            import ssl
            from urllib.parse import urlparse

            from qdrant_client import QdrantClient

            try:
                import truststore

                truststore.inject_into_ssl()
            except ImportError:
                pass
            ssl_context = ssl.create_default_context()

            parsed = urlparse(self._url)
            is_https = parsed.scheme == "https"
            host = parsed.hostname or self._url
            port = parsed.port or (443 if is_https else 6333)

            self._client = QdrantClient(
                host=host,
                port=port,
                api_key=self._api_key,
                https=is_https,
                verify=ssl_context,
                timeout=30,
            )
            logger.info("[Qdrant] Connected to %s:%d (https=%s)", host, port, is_https)
        except ImportError:
            logger.warning("[Qdrant] qdrant-client not installed — pip install qdrant-client")
        except Exception as exc:
            logger.warning("[Qdrant] Failed to connect: %s", exc)

    def __new__(cls):
        global _instance
        with _instance_lock:
            if _instance is None:
                _instance = super().__new__(cls)
            return _instance

    def _ensure_collection(self, collection_name: str, vector_size: int):
        """Create collection if it doesn't exist."""
        from qdrant_client.models import Distance, VectorParams

        collections = [c.name for c in self._client.get_collections().collections]
        if collection_name not in collections:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info("[Qdrant] Created collection '%s' (dim=%d)", collection_name, vector_size)

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not self._client:
            return

        from qdrant_client.models import PointStruct

        if embeddings:
            self._ensure_collection(collection_name, len(embeddings[0]))

        points = []
        for doc_id, doc, emb, meta in zip(ids, documents, embeddings, metadatas, strict=False):
            # Qdrant requires UUID or int point IDs; use a deterministic UUID from string ID
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))
            payload = {**meta, "document": doc, "original_id": doc_id}
            points.append(PointStruct(id=point_id, vector=emb, payload=payload))

        self._client.upsert(collection_name=collection_name, points=points)
        logger.info("[Qdrant] Upserted %d points to '%s'", len(points), collection_name)

    def query(
        self,
        collection_name: str,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Query returns ChromaDB-compatible result format for drop-in compatibility."""
        if not self._client:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_vector = query_embeddings[0] if query_embeddings else []
        if not query_vector:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        # Convert where filter to Qdrant filter
        query_filter = self._build_filter(where) if where else None

        results = self._client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=n_results,
            query_filter=query_filter,
            with_payload=True,
        )

        # Convert to ChromaDB-compatible format
        ids = []
        documents = []
        metadatas = []
        distances = []

        for hit in results:
            payload = hit.payload or {}
            ids.append(payload.get("original_id", str(hit.id)))
            documents.append(payload.pop("document", ""))
            payload.pop("original_id", None)
            metadatas.append(payload)
            # Qdrant returns similarity score (higher = better), ChromaDB returns distance (lower = better)
            distances.append(1.0 - hit.score)

        return {"ids": [ids], "documents": [documents], "metadatas": [metadatas], "distances": [distances]}

    def get(
        self,
        collection_name: str,
        where: dict[str, Any],
        limit: int = 0,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self._client:
            return {"ids": [], "documents": [], "metadatas": []}

        query_filter = self._build_filter(where) if where else None

        # limit=0 means "return all" — scroll in batches to get everything
        if limit > 0:
            points, _ = self._client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        else:
            # Scroll all points in batches
            all_points = []
            next_offset = None
            while True:
                batch, next_offset = self._client.scroll(
                    collection_name=collection_name,
                    scroll_filter=query_filter,
                    limit=256,
                    offset=next_offset,
                    with_payload=True,
                )
                all_points.extend(batch)
                if next_offset is None:
                    break
            points = all_points

        ids = []
        documents = []
        metadatas = []

        for point in points:
            payload = dict(point.payload or {})
            ids.append(payload.pop("original_id", str(point.id)))
            documents.append(payload.pop("document", ""))
            metadatas.append(payload)

        return {"ids": ids, "documents": documents, "metadatas": metadatas}

    def delete(self, collection_name: str, where: dict[str, Any]) -> dict[str, Any]:
        if not self._client:
            return {"deleted": 0}

        query_filter = self._build_filter(where) if where else None
        if query_filter:
            self._client.delete(collection_name=collection_name, points_selector=query_filter)
        return {"deleted": 0}

    def count(self, collection_name: str) -> int:
        if not self._client:
            return 0
        try:
            info = self._client.get_collection(collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    @staticmethod
    def _build_filter(where: dict[str, Any]):
        """Convert simple key=value filter dict to Qdrant Filter."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        conditions = []
        for key, value in where.items():
            if str(key).startswith("$"):
                continue  # Skip operator keys
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

        if not conditions:
            return None
        return Filter(must=conditions)
