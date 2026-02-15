"""ChromaDB indexing tool for persistent vector storage.

Best Practices:
- Lazy client initialization for better performance
- Batch operations for efficiency
- Comprehensive error handling
- Metadata tracking for observability
"""

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ...shared.paths import CHROMA_DIR
from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def _normalize_where(where: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a metadata filter to Chroma's expected shape.

    Some Chroma versions require the top-level `where` dict to contain exactly one
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

    # Multiple keys: wrap into a single operator.
    return {"$and": [{k: v} for k, v in where.items()]}


def _normalize_include(include: list[str] | None) -> list[str]:
    """Normalize `include` for Chroma `collection.get()`.

    Chroma expects include items like: documents, embeddings, metadatas, uris, data.
    `ids` are always returned and should NOT be listed in `include`.
    """
    if not include:
        return []
    allowed = {"documents", "embeddings", "metadatas", "distances", "uris", "data"}
    return [item for item in include if item in allowed]


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
    include: list[str] = Field(default_factory=list, description="Fields to include for get (e.g. ['ids','metadatas'])")


class ChromaIndexTool(BaseTool):
    name: str = "chroma_index"
    description: str = (
        "Manages ChromaDB persistent vector store with upsert, query, and count operations. "
        "Optimized for large-scale document retrieval with batch processing support."
    )
    args_schema: type[BaseModel] = ChromaIndexInput

    # Optional override used by tests and power users.
    chroma_dir: str | None = None

    # Performance tuning
    max_retries: int = 3
    retry_delay: float = 1.0

    def _get_client(self):
        """Lazy initialization of ChromaDB client.

        Best Practice: Lazy initialization reduces startup time and memory usage.
        Client is created only when first needed.
        """
        if not hasattr(self, "_client"):
            chroma_dir = self.chroma_dir or CHROMA_DIR
            Path(chroma_dir).mkdir(parents=True, exist_ok=True)

            logger.info(f"Initializing ChromaDB client at: {chroma_dir}")

            self._client = chromadb.PersistentClient(
                path=chroma_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            logger.info("ChromaDB client initialized")
        return self._client

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
        """Execute ChromaDB operation.

        Args:
            operation: 'upsert', 'query', or 'count'
            chunks: Chunks to upsert
            embeddings: Embeddings for chunks
            query_text: Query text
            query_embedding: Query embedding
            top_k: Number of results
            collection_name: Collection name
            collection_metadata: Metadata to store with collection

        Returns:
            Operation result dictionary
        """
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
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
            }

    def _upsert(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        collection_name: str,
        collection_metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Upsert chunks into collection.

        Args:
            chunks: List of chunk dictionaries
            embeddings: List of embedding vectors
            collection_name: Collection name
            collection_metadata: Metadata to store with collection

        Returns:
            Result dictionary
        """
        if not chunks or not embeddings:
            return {
                "success": False,
                "error": "No chunks or embeddings provided",
            }

        # Embeddings tool can return a list containing None entries for failed embeddings.
        # We tolerate that, but we expect one-to-one alignment by index.
        if len(chunks) != len(embeddings):
            return {
                "success": False,
                "error": f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings (expected aligned list)",
            }

        try:
            # Prepare collection metadata
            metadata = {"description": "Repository documentation chunks"}
            if collection_metadata:
                metadata.update(collection_metadata)

            collection = self._get_client().get_or_create_collection(name=collection_name, metadata=metadata)

            # Best-effort: ensure metadata updates even if collection already existed.
            try:
                if hasattr(collection, "modify"):
                    collection.modify(metadata=metadata)
            except Exception as e:
                logger.debug(f"Could not update collection metadata via modify(): {e}")

            # Prepare data for upsert
            ids = []
            texts = []
            metadatas = []
            valid_embeddings = []

            for chunk, embedding in zip(chunks, embeddings, strict=False):
                # Skip if embedding failed (None)
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
                return {
                    "success": False,
                    "error": "No valid chunks to upsert",
                }

            # Upsert to ChromaDB
            collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=valid_embeddings,
                metadatas=metadatas,
            )

            logger.info(f"Upserted {len(ids)} chunks to collection '{collection_name}'")

            return {
                "success": True,
                "upserted_count": len(ids),
                "collection_name": collection_name,
            }

        except Exception as e:
            logger.error(f"Error upserting to ChromaDB: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _query(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
        collection_name: str,
    ) -> dict[str, Any]:
        """Query collection for similar chunks.

        Args:
            query_text: Query text
            query_embedding: Query embedding vector
            top_k: Number of results
            collection_name: Collection name

        Returns:
            Query results dictionary
        """
        if not query_embedding:
            return {
                "success": False,
                "error": "No query embedding provided",
            }

        try:
            client = self._get_client()
            collections = client.list_collections()
            if collection_name not in [c.name for c in collections]:
                return {"success": True, "results": [], "count": 0}

            collection = client.get_collection(name=collection_name)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

            # Format results
            formatted_results = []

            if results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append(
                        {
                            "chunk_id": results["ids"][0][i],
                            "text": results["documents"][0][i] if results["documents"] else "",
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                            "distance": results["distances"][0][i] if results.get("distances") else 0.0,
                        }
                    )

            logger.info(f"Retrieved {len(formatted_results)} results for query")

            return {
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results),
            }

        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _get(
        self,
        collection_name: str,
        where: dict[str, Any],
        limit: int = 0,
        include: list[str] = None,
    ) -> dict[str, Any]:
        """Get documents by metadata filter.

        This is used for incremental indexing checks (e.g., file_path+file_hash).
        """
        include = _normalize_include(include)
        try:
            client = self._get_client()
            collections = client.list_collections()
            if collection_name not in [c.name for c in collections]:
                return {"success": True, "count": 0, "exists": False, "items": {}}

            collection = client.get_collection(name=collection_name)

            get_kwargs: dict[str, Any] = {"where": _normalize_where(where)}
            if include:
                get_kwargs["include"] = include
            if limit and limit > 0:
                get_kwargs["limit"] = limit

            results = collection.get(**get_kwargs)

            # Count heuristic: ids is present in chroma get response
            ids = results.get("ids", []) or []
            return {
                "success": True,
                "exists": True,
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
        """Delete documents by metadata filter (best-effort)."""
        try:
            client = self._get_client()
            collections = client.list_collections()
            if collection_name not in [c.name for c in collections]:
                return {"success": True, "deleted": 0, "exists": False}

            collection = client.get_collection(name=collection_name)

            # Chroma delete doesn't return deleted count reliably across versions
            collection.delete(where=_normalize_where(where))
            return {"success": True, "deleted": 0, "exists": True}

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return {"success": False, "error": str(e), "deleted": 0, "exists": False}

    def _count(
        self,
        collection_name: str,
    ) -> dict[str, Any]:
        """Get document count in collection.

        Args:
            collection_name: Collection name

        Returns:
            Result dictionary with count
        """
        try:
            client = self._get_client()

            # Check if collection exists
            collections = client.list_collections()
            collection_names = [c.name for c in collections]

            if collection_name not in collection_names:
                logger.info(f"Collection '{collection_name}' does not exist")
                return {
                    "success": True,
                    "count": 0,
                    "exists": False,
                }

            collection = client.get_collection(name=collection_name)
            count = collection.count()

            logger.info(f"Collection '{collection_name}' has {count} documents")
            return {
                "success": True,
                "count": count,
                "exists": True,
            }

        except Exception as e:
            logger.error(f"Count failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "exists": False,
            }

    def _get_collection_metadata(self, collection_name: str) -> dict[str, Any]:
        """Get metadata stored with collection.

        Args:
            collection_name: Collection name

        Returns:
            Metadata dictionary (empty if collection doesn't exist)
        """
        try:
            client = self._get_client()
            collections = client.list_collections()
            collection_names = [c.name for c in collections]

            if collection_name not in collection_names:
                return {}

            collection = client.get_collection(name=collection_name)
            return collection.metadata or {}

        except Exception as e:
            logger.error(f"Failed to get collection metadata: {e}")
            return {}
