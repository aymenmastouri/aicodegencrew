"""
DEPRECATED: Use pipelines.indexing package instead.

This module provides backward compatibility.
"""

from .indexing import (
    IndexingConfig,
    IndexingMetrics,
    IndexingPipeline,
    IndexingState,
    ensure_repo_indexed,
)

__all__ = [
    "IndexingConfig",
    "IndexingMetrics",
    "IndexingPipeline",
    "IndexingState",
    "ensure_repo_indexed",
]
