"""Duplicate/similar-issue detection via Qdrant vector store semantic similarity.

Searches the indexed codebase for semantically similar chunks.
Uses the Qdrant vector store with the correct branch-scoped collection name.
"""

import os
from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def find_duplicates(
    title: str,
    description: str,
    discover_dir: str = "",
    top_k: int = 3,
) -> list[dict]:
    """Find semantically similar code chunks via Qdrant vector store.

    Args:
        title:        Issue title.
        description:  Issue description.
        discover_dir: Legacy param (ignored — Qdrant uses QDRANT_URL).
        top_k:        Number of results to return.

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

    results = _query_qdrant(query, collection_name, top_k)
    if results is not None:
        return results

    logger.warning("[DuplicateDetector] Qdrant not available -- skipping")
    return []


def _query_qdrant(query: str, collection_name: str, top_k: int) -> list[dict] | None:
    """Try Qdrant vector store."""
    try:
        from ...shared.utils.qdrant_client import QdrantVectorClient

        store = QdrantVectorClient()
        if not store._client:
            return None

        from ...shared.utils.ollama_client import OllamaClient

        embedder = OllamaClient()
        embeddings = embedder.embed_batch([query[:500]])
        if not embeddings:
            return None

        results = store.query(
            collection_name=collection_name,
            query_embeddings=embeddings,
            n_results=top_k,
        )

        matches = []
        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        dists_list = results.get("distances", [[]])[0]

        for i, chunk_id in enumerate(ids_list):
            meta = metas_list[i] if i < len(metas_list) else {}
            doc = docs_list[i] if i < len(docs_list) else ""
            dist = dists_list[i] if i < len(dists_list) else 1.0
            score = round(max(0, 1 - dist), 3)
            matches.append({
                "chunk_id": chunk_id,
                "path": meta.get("file_path", meta.get("source", meta.get("path", ""))),
                "score": score,
                "snippet": (doc[:200] + "...") if len(doc) > 200 else doc,
            })

        logger.info("[DuplicateDetector] Found %d similar chunks (Qdrant)", len(matches))
        return matches

    except Exception as e:
        logger.debug("[DuplicateDetector] Qdrant not available: %s", e)
        return None
