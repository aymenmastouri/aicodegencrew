"""
RAG Query Tool - ChromaDB Semantic Search

CrewAI Best Practice: Use semantic search to find relevant code context
without loading the entire codebase into context.

Usage:
- rag_query(query="security annotations", limit=10)
- rag_query(query="TODO FIXME", limit=20)
"""

import json
from pathlib import Path
from typing import Any, ClassVar

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..utils.chroma_client import get_chroma_http_config
from ..utils.logger import setup_logger
from ..utils.ollama_client import OllamaClient
from ..utils.token_budget import MAX_SNIPPET_LENGTH, RAG_MAX_RESPONSE_CHARS, truncate_response

logger = setup_logger(__name__)


class _OllamaEmbedder:
    """Thin wrapper around OllamaClient for query-time embedding.

    Instead of passing an embedding_function to ChromaDB (which conflicts
    with collections created without one), we embed queries ourselves and
    pass ``query_embeddings`` to ``collection.query()``.
    """

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
    ChromaDB semantic search for code context.

    CrewAI Best Practice:
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
        "Semantic search in the indexed codebase via ChromaDB. "
        "Use natural language queries to find relevant code snippets. "
        "Examples: 'security annotations', 'TODO FIXME', 'error handling'"
    )
    args_schema: type[BaseModel] = RAGQueryInput

    # Configuration - Default paths to check (in order)
    chroma_dir: str = ""  # Will be auto-detected
    collection_name: str = "repo_docs"

    _client: Any | None = None
    _collection: Any | None = None
    _embedder: Any | None = None
    _evidence_index: dict[str, dict] | None = None

    # Standard locations for ChromaDB (ClassVar = not a Pydantic field)
    CHROMA_PATHS: ClassVar[list[str]] = [
        "knowledge/discover",  # Primary location (Phase 0 output)
        ".cache/.chroma",  # Legacy location
        ".chroma_db",  # Legacy location
        ".chroma",  # Alternative
    ]

    def __init__(self, chroma_dir: str = None, **kwargs):
        """Initialize with optional chroma dir override."""
        super().__init__(**kwargs)
        if chroma_dir:
            self.chroma_dir = chroma_dir

    def _find_chroma_path(self) -> str | None:
        """Find ChromaDB in standard locations."""
        # Check explicit config first
        if self.chroma_dir and Path(self.chroma_dir).exists():
            return self.chroma_dir

        # Resolve project root from __file__ (stable, independent of CWD)
        # __file__ = src/aicodegencrew/shared/tools/rag_query_tool.py
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

        for rel_path in self.CHROMA_PATHS:
            full_path = base_dir / rel_path
            if full_path.exists():
                logger.info(f"Found ChromaDB at: {full_path}")
                return str(full_path)

        return None

    def _get_collection(self):
        """Get ChromaDB collection with lazy initialization."""
        if self._collection is not None:
            return self._collection

        try:
            import chromadb
            from chromadb.config import Settings

            http_cfg = get_chroma_http_config()
            if http_cfg is not None:
                host, port, ssl = http_cfg
                logger.info(f"Connecting to ChromaDB server at {host}:{port} (ssl={ssl})")
                self._client = chromadb.HttpClient(
                    host=host,
                    port=port,
                    ssl=ssl,
                    settings=Settings(anonymized_telemetry=False),
                )
            else:
                chroma_path = self._find_chroma_path()

                if not chroma_path or not Path(chroma_path).exists():
                    logger.warning(f"ChromaDB not found. Searched paths: {self.CHROMA_PATHS}")
                    return None

                self._client = chromadb.PersistentClient(
                    path=chroma_path,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                )

            # Open collection WITHOUT an embedding_function.
            # The indexing pipeline (Phase 0) creates the collection without one
            # and upserts pre-computed Ollama embeddings directly.  Passing an
            # embedding_function here causes a ChromaDB conflict error.
            # Instead, we embed queries ourselves via _OllamaEmbedder and pass
            # query_embeddings to collection.query().
            try:
                self._collection = self._client.get_collection(
                    name=self.collection_name,
                )
                self._embedder = _OllamaEmbedder()
                logger.info(f"Connected to ChromaDB collection: {self.collection_name}")
            except Exception as e:
                logger.warning(f"Collection '{self.collection_name}' not found: {e}")
                return None

            return self._collection

        except ImportError:
            logger.error("chromadb not installed. Run: pip install chromadb")
            return None
        except Exception as e:
            logger.error(f"ChromaDB error: {e}")
            return None

    def _load_evidence_index(self) -> dict[str, dict]:
        """Lazy-load evidence.jsonl as dict[chunk_id -> record]."""
        if self._evidence_index is not None:
            return self._evidence_index

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
            collection = self._get_collection()

            if collection is None:
                return json.dumps({"error": "ChromaDB not available. Run Phase 0 (indexing) first.", "results": []})

            # Hard cap limit - reduced to prevent context overflow
            limit = min(limit, 10)

            # Build where filter (ChromaDB supports $eq, $ne, $in, $nin for strings)
            where_filter = None
            if content_type and content_type in ("code", "doc", "config"):
                where_filter = {"content_type": content_type}

            # Fetch extra results when file_filter is set (post-query filtering)
            fetch_limit = limit * 3 if file_filter else limit

            # Embed query ourselves (avoids ChromaDB embedding function conflict)
            query_embedding = self._embedder.embed([query])
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=fetch_limit,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            # Post-query filter by file_path substring (ChromaDB lacks $contains)
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

                    # Enrich with evidence metadata if available
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
