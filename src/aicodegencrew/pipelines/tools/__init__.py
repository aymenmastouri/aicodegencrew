"""
DEPRECATED: Use pipelines.indexing instead.

This module provides backward compatibility.
"""

from ..indexing import (
    IndexingPipeline,
    ensure_repo_indexed,
    IndexingConfig,
    IndexingMetrics,
    RepoDiscoveryTool,
    RepoReaderTool,
    ChunkerTool,
    OllamaEmbeddingsTool,
    ChromaIndexTool,
)

# Alias
EmbeddingsTool = OllamaEmbeddingsTool

__all__ = [
    "IndexingPipeline",
    "ensure_repo_indexed",
    "IndexingConfig",
    "IndexingMetrics",
    "RepoDiscoveryTool",
    "RepoReaderTool",
    "ChunkerTool",
    "OllamaEmbeddingsTool",
    "EmbeddingsTool",
    "ChromaIndexTool",
]
