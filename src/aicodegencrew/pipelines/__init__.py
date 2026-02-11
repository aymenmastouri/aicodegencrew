"""
Pipelines - Automated processing.

Phase 0: Indexing - Repository indexing to ChromaDB
Phase 1: Architecture Facts - Code analysis to facts.json
Phase 4: Development Planning - Hybrid (deterministic + 1 LLM call)
Phase 5: Code Generation - Hybrid (deterministic + 1 LLM call per file)
"""

from .indexing import IndexingPipeline, ensure_repo_indexed
from .architecture_facts import ArchitectureFactsPipeline
from .code_generation import CodeGenerationPipeline

__all__ = [
    "IndexingPipeline",
    "ensure_repo_indexed",
    "ArchitectureFactsPipeline",
    "CodeGenerationPipeline",
]
