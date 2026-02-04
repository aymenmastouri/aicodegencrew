"""
Crews - CrewAI multi-agent workflows.

Phase 2: Architecture Analysis (NEW)
- Multi-agent analysis: Technical, Functional, Quality, Synthesis Lead
- MapReduceAnalysisCrew: Scalable version for large repos (500+ components)
- Output: analyzed_architecture.json

Phase 3: Architecture Synthesis (LLM, evidence-first)
- Synthesizes C4 diagrams and arc42 documentation from architecture facts
- REFACTORED: All logic now in crew.py (no separate tasks.py/agents.py exports)
"""

# Phase 2: Architecture Analysis Crew
from .architecture_analysis.crew import ArchitectureAnalysisCrew
from .architecture_analysis.mapreduce_crew import MapReduceAnalysisCrew

# Phase 3: Architecture Synthesis Crew
from .architecture_synthesis.crew import ArchitectureSynthesisCrew

# Legacy alias for backwards compatibility (deprecated)
ArchitectureCrew = ArchitectureSynthesisCrew

__all__ = [
    "ArchitectureAnalysisCrew",  # Phase 2 (standard)
    "MapReduceAnalysisCrew",     # Phase 2 (scalable for large repos)
    "ArchitectureSynthesisCrew",  # Phase 3
    "ArchitectureCrew",  # Deprecated alias
]

