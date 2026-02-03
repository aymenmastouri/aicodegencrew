"""
DEPRECATED: Use pipelines.indexing package instead.

This module provides backward compatibility.
"""

from .indexing import (
    IndexingPipeline,
    ensure_repo_indexed,
    IndexingConfig,
    IndexingMetrics,
)

__all__ = [
    "IndexingPipeline",
    "ensure_repo_indexed",
    "IndexingConfig", 
    "IndexingMetrics",
]
