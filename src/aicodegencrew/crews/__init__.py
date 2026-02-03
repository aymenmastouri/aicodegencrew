"""
Crews - CrewAI multi-agent workflows.

Phase 2: Architecture Synthesis (LLM, evidence-first)
- Synthesizes C4 diagrams and arc42 documentation from architecture facts
- REFACTORED: All logic now in crew.py (no separate tasks.py/agents.py exports)
"""

# Phase 2: Architecture Synthesis Crew
from .architecture_synthesis.crew import ArchitectureSynthesisCrew

# Legacy alias for backwards compatibility (deprecated)
ArchitectureCrew = ArchitectureSynthesisCrew

__all__ = [
    "ArchitectureSynthesisCrew",
    "ArchitectureCrew",  # Deprecated alias
]

