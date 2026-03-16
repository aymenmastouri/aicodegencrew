"""
Phase 0: Indexing Pipeline

Repository indexing: discovery, chunking, embedding, Qdrant vector storage.
Enhanced with symbol extraction, evidence store, repo manifest, and budget engine.
"""

from .budget_engine import BudgetEngine
from .chroma_index_tool import ChromaIndexTool
from .chunker_tool import ChunkerTool
from .embeddings_tool import OllamaEmbeddingsTool
from .indexing_pipeline import (
    IndexingConfig,
    IndexingMetrics,
    IndexingPipeline,
    IndexingState,
    ensure_repo_indexed,
)
from .manifest_builder import ManifestBuilder
from .models import EvidenceRecord, RepoManifest, SymbolRecord
from .repo_discovery_tool import RepoDiscoveryTool
from .repo_reader_tool import RepoReaderTool
from .symbol_extractor import SymbolExtractor

__all__ = [
    "BudgetEngine",
    "ChromaIndexTool",
    "ChunkerTool",
    "EvidenceRecord",
    "IndexingConfig",
    "IndexingMetrics",
    "IndexingPipeline",
    "IndexingState",
    "ManifestBuilder",
    "OllamaEmbeddingsTool",
    "RepoDiscoveryTool",
    "RepoManifest",
    "RepoReaderTool",
    "SymbolExtractor",
    "SymbolRecord",
    "ensure_repo_indexed",
]
