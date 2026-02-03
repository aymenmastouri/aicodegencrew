"""
Phase 0: Indexing Pipeline

Repository indexing: discovery, chunking, embedding, ChromaDB storage.
"""

from .repo_discovery_tool import RepoDiscoveryTool
from .repo_reader_tool import RepoReaderTool
from .chunker_tool import ChunkerTool
from .embeddings_tool import OllamaEmbeddingsTool
from .chroma_index_tool import ChromaIndexTool
from .indexing_pipeline import (
    ensure_repo_indexed,
    IndexingConfig,
    IndexingMetrics,
)
from .pipeline import IndexingPipeline

__all__ = [
    "IndexingPipeline",
    "ensure_repo_indexed",
    "IndexingConfig",
    "IndexingMetrics",
    "RepoDiscoveryTool",
    "RepoReaderTool",
    "ChunkerTool",
    "OllamaEmbeddingsTool",
    "ChromaIndexTool",
]
