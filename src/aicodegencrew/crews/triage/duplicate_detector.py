"""Duplicate/similar-issue detection via ChromaDB semantic similarity.

Searches the indexed codebase for semantically similar chunks.
"""

from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def find_duplicates(
    title: str,
    description: str,
    chroma_dir: str,
    top_k: int = 3,
) -> list[dict]:
    """Find semantically similar code chunks via ChromaDB.

    Args:
        title:       Issue title.
        description: Issue description.
        chroma_dir:  Path to ChromaDB directory.
        top_k:       Number of results to return.

    Returns:
        List of {"chunk_id": str, "path": str, "score": float, "snippet": str}
    """
    query = f"{title} {description}".strip()
    if not query:
        return []

    try:
        from ...shared.utils.chroma_client import create_chroma_client
    except ImportError:
        logger.warning("[DuplicateDetector] chromadb not installed — skipping")
        return []

    try:
        client = create_chroma_client(persistent_path=chroma_dir)
        collection = client.get_collection("repo_docs")
    except Exception as e:
        logger.warning("[DuplicateDetector] Could not open ChromaDB: %s", e)
        return []

    try:
        # Embed query ourselves (collection was indexed without a default embedding function)
        from ...shared.utils.ollama_client import OllamaClient
        embedder = OllamaClient()
        embeddings = embedder.embed_batch([query[:500]])
        if not embeddings:
            logger.warning("[DuplicateDetector] Embedding failed — skipping duplicate detection")
            return []
        results = collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning("[DuplicateDetector] ChromaDB query failed: %s", e)
        return []

    matches: list[dict] = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for i, chunk_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        doc = docs[i] if i < len(docs) else ""
        dist = dists[i] if i < len(dists) else 1.0
        # ChromaDB returns L2 distance; convert to similarity score
        score = round(max(0, 1 - dist / 2), 3)
        matches.append({
            "chunk_id": chunk_id,
            "path": meta.get("source", meta.get("path", "")),
            "score": score,
            "snippet": (doc[:200] + "...") if len(doc) > 200 else doc,
        })

    logger.info("[DuplicateDetector] Found %d similar chunks", len(matches))
    return matches
