"""
Hybrid phases — pipeline stages + LLM agents combined.

Phase 4: Development Planning - Deterministic stages + 1 LLM call
Phase 5: Code Generation - Hierarchical CrewAI team
"""

from .code_generation import ImplementCrew
from .development_planning import DevelopmentPlanningPipeline

__all__ = ["DevelopmentPlanningPipeline", "ImplementCrew"]
