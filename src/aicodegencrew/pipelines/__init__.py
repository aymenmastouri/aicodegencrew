"""
Pipelines - Deterministic processing (no LLM).

Phase 0: Indexing - Repository indexing to ChromaDB
Phase 1: Architecture Facts - Code analysis to facts.json
"""

from .indexing import IndexingPipeline, ensure_repo_indexed
from .architecture_facts import ArchitectureFactsPipeline

__all__ = [
    "IndexingPipeline",
    "ensure_repo_indexed",
    "ArchitectureFactsPipeline",
]
