"""
RAG Query Tool - Qdrant Semantic Search

Semantic search to find relevant code context without loading the entire
codebase into context.

Usage:
- rag_query(query="security annotations", limit=10)
- rag_query(query="TODO FIXME", limit=20)
"""

import json
from pathlib import Path
from typing import Any, ClassVar

from .base_tool import BaseTool
from pydantic import BaseModel, Field

from ..utils.logger import setup_logger
from ..utils.ollama_client import OllamaClient
from ..utils.token_budget import MAX_SNIPPET_LENGTH, RAG_MAX_RESPONSE_CHARS, truncate_response
from ..utils.vector_store import get_vector_store

logger = setup_logger(__name__)


class _OllamaEmbedder:
    """Thin wrapper around OllamaClient for query-time embedding."""

    def __init__(self):
        self._client = OllamaClient()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._client.embed_batch(texts)


class RAGQueryInput(BaseModel):
    """Input schema for RAGQueryTool."""

    query: str = Field(
        ..., description="Semantic search query (e.g., 'security annotations', 'error handling patterns', 'TODO FIXME')"
    )
    limit: int = Field(default=10, description="Maximum number of results to return (default 10, max 10)")
    file_filter: str = Field(
        default="", description="Optional: filter by file path pattern (e.g., 'Service.java', 'Controller')"
    )
    content_type: str = Field(default="", description="Optional: filter by content type ('code', 'doc', 'config')")


class RAGQueryTool(BaseTool):
    """
    Qdrant semantic search for code context.

    - Semantic search finds relevant code snippets
    - Much more efficient than reading entire files
    - Supports natural language queries

    Usage Examples:
    1. rag_query(query="@PreAuthorize security") - Find security annotations
    2. rag_query(query="TODO FIXME HACK") - Find technical debt markers
    3. rag_query(query="Workflow state transition") - Find business logic
    """

    name: str = "rag_query"
    description: str = (
        "Semantic search in the indexed codebase via Qdrant vector store. "
        "Use natural language queries to find relevant code snippets. "
        "Examples: 'security annotations', 'TODO FIXME', 'error handling'. "
        "IMPORTANT: Call once per query with a SINGLE set of parameters, not an array."
    )
    args_schema: type[BaseModel] = RAGQueryInput

    # Configuration
    chroma_dir: str = ""  # Kept for API compat (ignored — Qdrant uses QDRANT_URL)
    collection_name: str = ""  # Auto-derived from repo+branch if empty

    _vector_store: Any | None = None
    _embedder: Any | None = None
    _evidence_index: dict[str, dict] | None = None

    def __init__(self, chroma_dir: str = None, collection_name: str = None, **kwargs):
        """Initialize with optional collection name override."""
        super().__init__(**kwargs)
        if chroma_dir:
            self.chroma_dir = chroma_dir  # kept for API compat
        if collection_name:
            self.collection_name = collection_name
        # Auto-derive collection name from PROJECT_PATH + branch if not set
        if not self.collection_name:
            try:
                import os

                from ..project_context import derive_collection_name

                project_path = os.getenv("PROJECT_PATH") or os.getenv("REPO_PATH", "")
                if project_path:
                    self.collection_name = derive_collection_name(project_path)
                else:
                    self.collection_name = "repo_docs"
            except Exception:
                self.collection_name = "repo_docs"

    def _get_store(self):
        """Get vector store with lazy initialization."""
        if self._vector_store is not None:
            return self._vector_store

        self._vector_store = get_vector_store()
        self._embedder = _OllamaEmbedder()
        logger.info("Using Qdrant vector store for RAG queries")
        return self._vector_store

    def _load_evidence_index(self) -> dict[str, dict]:
        """Lazy-load evidence.jsonl as dict[chunk_id -> record]."""
        if self._evidence_index is not None:
            return self._evidence_index

        # Try active-project aware path first, then legacy flat path
        from ..paths import get_discover_evidence

        evidence_path = Path(get_discover_evidence())
        if not evidence_path.exists():
            # Legacy fallback
            base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
            evidence_path = base_dir / "knowledge" / "discover" / "evidence.jsonl"

        if not evidence_path.exists():
            self._evidence_index = {}
            return self._evidence_index

        index = {}
        try:
            with open(evidence_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rec = json.loads(line)
                        cid = rec.get("chunk_id", "")
                        if cid:
                            index[cid] = rec
            logger.info(f"Loaded {len(index)} evidence records")
        except Exception as e:
            logger.debug(f"Could not load evidence.jsonl: {e}")

        self._evidence_index = index
        return self._evidence_index

    def _run(
        self,
        query: str,
        limit: int = 10,
        file_filter: str = "",
        content_type: str = "",
    ) -> str:
        """
        Execute semantic search.

        Args:
            query: Natural language search query
            limit: Max results (capped at 10)
            file_filter: Optional file path filter
            content_type: Optional content type filter ('code', 'doc', 'config')

        Returns:
            JSON string with matching code snippets
        """
        try:
            store = self._get_store()

            if store is None:
                return json.dumps({"error": "Vector store not available. Run Phase 0 (indexing) first.", "results": []})

            # Hard cap limit - reduced to prevent context overflow
            limit = min(limit, 10)

            # Build where filter
            where_filter = None
            if content_type and content_type in ("code", "doc", "config"):
                where_filter = {"content_type": content_type}

            # Fetch extra results when file_filter is set (post-query filtering)
            fetch_limit = limit * 3 if file_filter else limit

            # Embed query
            query_embedding = self._embedder.embed([query])
            if not query_embedding:
                return json.dumps({"error": "Embedding failed -- check API_BASE and OPENAI_API_KEY in .env", "results": []})

            results = store.query(
                self.collection_name,
                query_embeddings=query_embedding,
                n_results=fetch_limit,
                where=where_filter,
            )

            # Post-query filter by file_path substring
            if file_filter and results and results.get("documents"):
                filtered = {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}
                for i, meta in enumerate(results["metadatas"][0]):
                    fp = meta.get("file_path", "")
                    if file_filter.lower() in fp.lower():
                        filtered["documents"][0].append(results["documents"][0][i])
                        filtered["metadatas"][0].append(meta)
                        filtered["distances"][0].append(results["distances"][0][i])
                        filtered["ids"][0].append(results["ids"][0][i])
                        if len(filtered["documents"][0]) >= limit:
                            break
                results = filtered

            # Load evidence index for enrichment
            evidence_index = self._load_evidence_index()

            # Format results with TOKEN BUDGET
            formatted_results = []

            if results and results.get("documents"):
                documents = results["documents"][0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                ids = results.get("ids", [[]])[0]

                if not (len(documents) == len(metadatas) == len(distances) == len(ids)):
                    logger.warning(
                        "[RAGQuery] Mismatched result arrays: docs=%d, meta=%d, dist=%d, ids=%d",
                        len(documents),
                        len(metadatas),
                        len(distances),
                        len(ids),
                    )

                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 0
                    chunk_id = ids[i] if i < len(ids) else ""

                    # Truncate content to MAX_SNIPPET_LENGTH
                    content = doc[:MAX_SNIPPET_LENGTH] if doc else ""
                    if doc and len(doc) > MAX_SNIPPET_LENGTH:
                        content += "..."

                    result_entry = {
                        "file_path": metadata.get("file_path", "unknown"),
                        "relevance_score": round(1 - distance, 3) if distance else 0,
                        "content": content,
                    }

                    # Evidence metadata: read from Qdrant payload (primary)
                    # or fall back to local evidence.jsonl index (legacy)
                    if metadata.get("start_line"):
                        result_entry["start_line"] = metadata.get("start_line", 0)
                        result_entry["end_line"] = metadata.get("end_line", 0)
                        result_entry["content_type"] = metadata.get("content_type", "")
                        symbols_raw = metadata.get("symbols", "")
                        result_entry["symbols"] = symbols_raw.split(",") if symbols_raw else []
                    else:
                        # Legacy fallback: evidence.jsonl
                        evidence = evidence_index.get(chunk_id)
                        if evidence:
                            result_entry["start_line"] = evidence.get("start_line", 0)
                            result_entry["end_line"] = evidence.get("end_line", 0)
                            result_entry["content_type"] = evidence.get("type", "")
                            result_entry["symbols"] = evidence.get("symbols", [])

                    formatted_results.append(result_entry)

            output = {
                "query": query,
                "file_filter": file_filter,
                "content_type": content_type,
                "result_count": len(formatted_results),
                "results": formatted_results,
            }

            # TOKEN BUDGET: Final truncation check
            output_str = json.dumps(output, indent=2, ensure_ascii=False)
            output_str = truncate_response(output_str, RAG_MAX_RESPONSE_CHARS)

            return output_str

        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return json.dumps({"error": str(e), "results": []})
