"""
Pipelines — deterministic data-collect + LLM phases.

Phase 0: indexing   — repository indexing to Qdrant vector store
Phase 1: extract    — architecture facts to facts.json
Phase 2: analyze    — parallel LLM section analysis + synthesis
Phase 3: triage     — issue classification + context
Phase 4: plan       — hybrid planning (5 stages, 1 LLM call)
Phase 6: document   — document generation
Phase 7: review     — code review synthesis

Phase 5 (implement) uses CrewAI agents — see crews/implement/.
"""

from .architecture_facts import ArchitectureFactsPipeline
from .indexing import IndexingPipeline, ensure_repo_indexed

__all__ = [
    "ArchitectureFactsPipeline",
    "IndexingPipeline",
    "ensure_repo_indexed",
]
