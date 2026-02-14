"""
Pipelines - Pure deterministic processing (no LLM).

Phase 0: Indexing - Repository indexing to ChromaDB
Phase 1: Architecture Facts - Code analysis to facts.json

Hybrid phases (pipeline + LLM) have moved to hybrid/ package:
- Phase 4: Development Planning -> hybrid.development_planning
- Phase 5: Code Generation -> hybrid.code_generation
"""

from .architecture_facts import ArchitectureFactsPipeline
from .indexing import IndexingPipeline, ensure_repo_indexed

__all__ = [
    "ArchitectureFactsPipeline",
    "IndexingPipeline",
    "ensure_repo_indexed",
]
