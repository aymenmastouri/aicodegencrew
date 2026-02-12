"""
DEPRECATED: Use pipelines.indexing instead.

This module provides backward compatibility.
"""

from ..indexing import (
    ChromaIndexTool,
    ChunkerTool,
    IndexingConfig,
    IndexingMetrics,
    IndexingPipeline,
    OllamaEmbeddingsTool,
    RepoDiscoveryTool,
    RepoReaderTool,
    ensure_repo_indexed,
)

# Alias
EmbeddingsTool = OllamaEmbeddingsTool

__all__ = [
    "ChromaIndexTool",
    "ChunkerTool",
    "EmbeddingsTool",
    "IndexingConfig",
    "IndexingMetrics",
    "IndexingPipeline",
    "OllamaEmbeddingsTool",
    "RepoDiscoveryTool",
    "RepoReaderTool",
    "ensure_repo_indexed",
]
