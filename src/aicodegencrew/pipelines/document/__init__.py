"""Document Pipeline — generates C4 and arc42 architecture documentation.

Pipeline + LLM Hybrid: deterministic data collection + single LLM call per chapter.
No agents, no tool loops, no iterations.
"""

from .pipeline import DocumentPipeline

__all__ = ["DocumentPipeline"]
