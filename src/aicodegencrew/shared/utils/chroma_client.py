"""ChromaDB client helpers — DEPRECATED.

ChromaDB has been removed. The project uses Qdrant exclusively.
This stub exists only to provide helpful errors if old code paths
are accidentally invoked.
"""

from __future__ import annotations


def get_chroma_http_config():
    """Deprecated: ChromaDB is no longer used. Use Qdrant instead."""
    return None


def create_chroma_client(*, persistent_path=None, settings=None):
    """Deprecated: ChromaDB is no longer used. Use Qdrant instead."""
    raise ImportError(
        "ChromaDB has been removed. The project now uses Qdrant exclusively. "
        "See shared/utils/qdrant_client.py and shared/utils/vector_store.py."
    )
