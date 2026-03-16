"""Duplicate/similar-issue detection via vector store semantic similarity.

Searches the indexed codebase for semantically similar chunks.
Uses the VectorStore abstraction (Qdrant or ChromaDB) with the correct
branch-scoped collection name.
"""

import os
from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def find_duplicates(
    title: str,
    description: str,
    chroma_dir: str,
    top_k: int = 3,
) -> list[dict]:
    """Find semantically similar code chunks via vector store.

    Args:
        title:       Issue title.
        description: Issue description.
        chroma_dir:  Path to ChromaDB directory (legacy param, also checks Qdrant).
        top_k:       Number of results to return.

    Returns:
        List of {"chunk_id": str, "path": str, "score": float, "snippet": str}
    """
    query = f"{title} {description}".strip()
    if not query:
        return []

    # Derive collection name from PROJECT_PATH (branch-scoped)
    collection_name = "repo_docs"
    try:
        from ...shared.project_context import derive_collection_name

        project_path = os.getenv("PROJECT_PATH") or os.getenv("REPO_PATH", "")
        if project_path:
            collection_name = derive_collection_name(project_path)
    except Exception:
        pass

    # Try Qdrant first (preferred), fall back to ChromaDB
    results = _query_qdrant(query, collection_name, top_k)
    if results is not None:
        return results

    results = _query_chroma(query, collection_name, chroma_dir, top_k)
    if results is not None:
        return results

    logger.warning("[DuplicateDetector] No vector store available — skipping")
    return []


def _query_qdrant(query: str, collection_name: str, top_k: int) -> list[dict] | None:
    """Try Qdrant vector store."""
    try:
        from ...shared.utils.qdrant_client import QdrantVectorStore

        store = QdrantVectorStore()
        if not store.enabled:
            return None

        from ...shared.utils.ollama_client import OllamaClient

        embedder = OllamaClient()
        embeddings = embedder.embed_batch([query[:500]])
        if not embeddings:
            return None

        results = store.query(
            collection_name=collection_name,
            query_vector=embeddings[0],
            limit=top_k,
        )

        matches = []
        for point in results:
            payload = point.payload or {}
            matches.append({
                "chunk_id": str(point.id),
                "path": payload.get("source", payload.get("path", "")),
                "score": round(point.score, 3),
                "snippet": (payload.get("content", "")[:200] + "..."),
            })

        logger.info("[DuplicateDetector] Found %d similar chunks (Qdrant)", len(matches))
        return matches

    except Exception as e:
        logger.debug("[DuplicateDetector] Qdrant not available: %s", e)
        return None


def _query_chroma(query: str, collection_name: str, chroma_dir: str, top_k: int) -> list[dict] | None:
    """Fall back to ChromaDB."""
    try:
        from ...shared.utils.chroma_client import create_chroma_client
    except ImportError:
        return None

    try:
        client = create_chroma_client(persistent_path=chroma_dir)
        collection = client.get_collection(collection_name)
    except Exception as e:
        logger.warning("[DuplicateDetector] ChromaDB collection '%s' not found: %s", collection_name, e)
        return None

    try:
        from ...shared.utils.ollama_client import OllamaClient

        embedder = OllamaClient()
        embeddings = embedder.embed_batch([query[:500]])
        if not embeddings:
            return None

        results = collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning("[DuplicateDetector] ChromaDB query failed: %s", e)
        return None

    matches: list[dict] = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for i, chunk_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        doc = docs[i] if i < len(docs) else ""
        dist = dists[i] if i < len(dists) else 1.0
        score = round(max(0, 1 - dist / 2), 3)
        matches.append({
            "chunk_id": chunk_id,
            "path": meta.get("source", meta.get("path", "")),
            "score": score,
            "snippet": (doc[:200] + "...") if len(doc) > 200 else doc,
        })

    logger.info("[DuplicateDetector] Found %d similar chunks (ChromaDB)", len(matches))
    return matches
