# =============================================================================
# Phase 2: Architecture Synthesis Crew
# =============================================================================
# Senior Software Architect performing Reverse Engineering & Top-Down Analysis
#
# REFACTORED: All task building is now in crew.py
# C4 Tasks (Top-Down): Context -> Container -> Component
# arc42 Tasks (Reverse Engineering): Introduction -> Strategy -> Blocks -> Runtime
# =============================================================================

from .crew import ArchitectureSynthesisCrew

__all__ = [
    "ArchitectureSynthesisCrew",
]

