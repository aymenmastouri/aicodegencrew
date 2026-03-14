"""Vector store indexing tool for persistent vector storage.

Supports ChromaDB (default) and Qdrant via VECTOR_DB env var.
Uses the unified VectorStoreProtocol for all operations.

Best Practices:
- Lazy client initialization for better performance
- Batch operations for efficiency
- Comprehensive error handling
- Metadata tracking for observability
"""

import os
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ...shared.paths import get_chroma_dir
from ...shared.utils.logger import setup_logger
from ...shared.utils.vector_store import get_vector_store

logger = setup_logger(__name__)


def _normalize_where(where: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a metadata filter.

    Some backends require the top-level `where` dict to contain exactly one
    operator (e.g. `$and`, `$or`). Our incremental indexing naturally builds
    multi-field equality filters like `{repo_path: ..., file_path: ..., file_hash: ...}`.
    This helper converts those into `{"$and": [{"repo_path": ...}, ...]}`.
    """
    if not where:
        return {}

    # If caller already provided an operator-based expression, leave it alone.
    if any(str(k).startswith("$") for k in where.keys()):
        return where

    # Single key is fine as-is.
    if len(where) <= 1:
        return where

    # Multiple keys: wrap into a single operator (ChromaDB format).
    # Qdrant client handles this internally, but wrapping is safe for both.
    return {"$and": [{k: v} for k, v in where.items()]}


class ChromaIndexInput(BaseModel):
    """Input schema for ChromaIndexTool."""

    operation: str = Field(..., description="Operation: 'upsert', 'query', 'get', 'delete', or 'count'")
    chunks: list[dict[str, Any]] = Field(default_factory=list, description="Chunks to upsert")
    embeddings: list[list[float]] = Field(default_factory=list, description="Embeddings for chunks")
    query_text: str = Field(default="", description="Query text for search")
    query_embedding: list[float] = Field(default_factory=list, description="Query embedding")
    top_k: int = Field(default=10, description="Number of results to return")
    collection_name: str = Field(default="repo_docs", description="Collection name")
    collection_metadata: dict[str, Any] = Field(default_factory=dict, description="Collection metadata")
    where: dict[str, Any] = Field(default_factory=dict, description="Metadata filter for get/delete")
    limit: int = Field(default=0, description="Max number of items to return for get (0 = no limit)")
    include: list[str] = Field(default_factory=list, description="Fields to include for get")


class ChromaIndexTool(BaseTool):
    name: str = "chroma_index"
    description: str = (
        "Manages persistent vector store with upsert, query, and count operations. "
        "Backend selected via VECTOR_DB env var (chroma or qdrant)."
    )
    args_schema: type[BaseModel] = ChromaIndexInput

    # Optional override used by tests and power users.
    chroma_dir: str | None = None

    # Performance tuning
    max_retries: int = 3
    retry_delay: float = 1.0

    def _get_vector_store(self):
        """Lazy initialization of the unified vector store backend.

        Uses VECTOR_DB env var to select between ChromaDB and Qdrant.
        Falls back to ChromaDB when VECTOR_DB is not set.
        """
        if not hasattr(self, "_vector_store"):
            if os.getenv("VECTOR_DB", "chroma").strip().lower() == "qdrant":
                self._vector_store = get_vector_store()
                logger.info("Using Qdrant vector store backend")
            else:
                chroma_dir = self.chroma_dir or get_chroma_dir()
                Path(chroma_dir).mkdir(parents=True, exist_ok=True)
                self._vector_store = get_vector_store(persistent_path=chroma_dir)
                logger.info(f"Using ChromaDB vector store backend at: {chroma_dir}")
        return self._vector_store

    def _run(
        self,
        operation: str,
        chunks: list[dict[str, Any]] = None,
        embeddings: list[list[float]] = None,
        query_text: str = "",
        query_embedding: list[float] = None,
        top_k: int = 10,
        collection_name: str = "repo_docs",
        collection_metadata: dict[str, Any] = None,
        where: dict[str, Any] = None,
        limit: int = 0,
        include: list[str] = None,
    ) -> dict[str, Any]:
        """Execute vector store operation."""
        if operation == "upsert":
            return self._upsert(chunks, embeddings, collection_name, collection_metadata)
        elif operation == "query":
            return self._query(query_text, query_embedding, top_k, collection_name)
        elif operation == "get":
            return self._get(collection_name, where=where or {}, limit=limit, include=include or [])
        elif operation == "delete":
            return self._delete(collection_name, where=where or {})
        elif operation == "count":
            return self._count(collection_name)
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    def _upsert(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        collection_name: str,
        collection_metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Upsert chunks into collection."""
        if not chunks or not embeddings:
            return {"success": False, "error": "No chunks or embeddings provided"}

        if len(chunks) != len(embeddings):
            return {
                "success": False,
                "error": f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings (expected aligned list)",
            }

        try:
            store = self._get_vector_store()

            # Prepare data for upsert
            ids = []
            texts = []
            metadatas = []
            valid_embeddings = []

            for chunk, embedding in zip(chunks, embeddings, strict=False):
                if embedding is None:
                    continue

                chunk_id = chunk.get("chunk_id", "")
                text = chunk.get("text", "")

                if not chunk_id or not text:
                    continue

                ids.append(chunk_id)
                texts.append(text)
                meta = {
                    "file_path": chunk.get("file_path", ""),
                    "file_hash": chunk.get("file_hash", ""),
                    "repo_path": chunk.get("repo_path", ""),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "start_char": chunk.get("start_char", 0),
                    "end_char": chunk.get("end_char", 0),
                }
                if chunk.get("content_type"):
                    meta["content_type"] = chunk["content_type"]
                metadatas.append(meta)
                valid_embeddings.append(embedding)

            if not ids:
                return {"success": False, "error": "No valid chunks to upsert"}

            store.upsert(collection_name, ids, texts, valid_embeddings, metadatas)

            logger.info(f"Upserted {len(ids)} chunks to collection '{collection_name}'")

            return {
                "success": True,
                "upserted_count": len(ids),
                "collection_name": collection_name,
            }

        except Exception as e:
            logger.error(f"Error upserting: {e}")
            return {"success": False, "error": str(e)}

    def _query(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
        collection_name: str,
    ) -> dict[str, Any]:
        """Query collection for similar chunks."""
        if not query_embedding:
            return {"success": False, "error": "No query embedding provided"}

        try:
            store = self._get_vector_store()
            results = store.query(collection_name, query_embeddings=[query_embedding], n_results=top_k)

            # Format results
            formatted_results = []
            ids_list = results.get("ids", [[]])[0]
            docs_list = results.get("documents", [[]])[0]
            meta_list = results.get("metadatas", [[]])[0]
            dist_list = results.get("distances", [[]])[0]

            for i in range(len(ids_list)):
                formatted_results.append({
                    "chunk_id": ids_list[i],
                    "text": docs_list[i] if i < len(docs_list) else "",
                    "metadata": meta_list[i] if i < len(meta_list) else {},
                    "distance": dist_list[i] if i < len(dist_list) else 0.0,
                })

            logger.info(f"Retrieved {len(formatted_results)} results for query")

            return {"success": True, "results": formatted_results, "count": len(formatted_results)}

        except Exception as e:
            logger.error(f"Error querying: {e}")
            return {"success": False, "error": str(e)}

    def _get(
        self,
        collection_name: str,
        where: dict[str, Any],
        limit: int = 0,
        include: list[str] = None,
    ) -> dict[str, Any]:
        """Get documents by metadata filter."""
        try:
            store = self._get_vector_store()
            results = store.get(collection_name, where=_normalize_where(where), limit=limit, include=include)

            ids = results.get("ids", []) or []
            return {
                "success": True,
                "exists": len(ids) > 0,
                "count": len(ids),
                "items": results,
            }

        except Exception as e:
            logger.error(f"Get failed: {e}")
            return {"success": False, "error": str(e), "count": 0, "exists": False, "items": {}}

    def _delete(
        self,
        collection_name: str,
        where: dict[str, Any],
    ) -> dict[str, Any]:
        """Delete documents by metadata filter."""
        try:
            store = self._get_vector_store()
            result = store.delete(collection_name, where=_normalize_where(where))
            return {"success": True, "deleted": result.get("deleted", 0), "exists": True}

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return {"success": False, "error": str(e), "deleted": 0, "exists": False}

    def _count(self, collection_name: str) -> dict[str, Any]:
        """Get document count in collection."""
        try:
            store = self._get_vector_store()
            count = store.count(collection_name)

            logger.info(f"Collection '{collection_name}' has {count} documents")
            return {"success": True, "count": count, "exists": count > 0}

        except Exception as e:
            logger.error(f"Count failed: {e}")
            return {"success": False, "error": str(e), "count": 0, "exists": False}

    def _get_collection_metadata(self, collection_name: str) -> dict[str, Any]:
        """Get metadata stored with collection.

        Note: Only supported with ChromaDB backend. Returns empty dict for Qdrant.
        """
        if os.getenv("VECTOR_DB", "chroma").strip().lower() == "qdrant":
            return {}

        try:
            store = self._get_vector_store()
            # ChromaVectorStore has _get_if_exists that returns a collection
            col = store._get_if_exists(collection_name)
            return (col.metadata or {}) if col else {}
        except Exception as e:
            logger.error(f"Failed to get collection metadata: {e}")
            return {}
