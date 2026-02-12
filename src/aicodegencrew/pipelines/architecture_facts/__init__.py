"""
Phase 1: Architecture Facts Pipeline

Deterministic extraction of architecture facts from source code.
NO LLM. NO interpretation. Only facts + evidence.

Pipeline:
    Index -> Collectors (parallel) -> Raw Facts -> Model Builder -> Canonical JSON

Architecture:
    - Collectors: Extract raw facts with their own IDs
    - Model Builder: Deduplicate, normalize IDs, resolve relations
    - Dimension Writers: Write separate JSON files per dimension

Usage:
    from aicodegencrew.pipelines.architecture_facts import ArchitectureFactsPipeline

    pipeline = ArchitectureFactsPipeline(repo_path="/path/to/repo")
    result = pipeline.kickoff()
"""

from .dimension_writers import CanonicalModelWriter
from .model_builder import (
    ArchitectureLayer,
    ArchitectureModel,
    ArchitectureModelBuilder,
    CanonicalIdGenerator,
    LayerClassifier,
)
from .pipeline import ArchitectureFactsPipeline

__all__ = [
    "ArchitectureFactsPipeline",
    "ArchitectureLayer",
    "ArchitectureModel",
    "ArchitectureModelBuilder",
    "CanonicalIdGenerator",
    "CanonicalModelWriter",
    "LayerClassifier",
]
