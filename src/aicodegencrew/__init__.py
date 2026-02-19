"""
AI Code Generation Crew — SDLC Automation Platform

8-phase pipeline from repository indexing to code generation:

    pipelines/          Pure deterministic (no LLM)
        indexing/           Phase 0: Repository indexing (ChromaDB)
        architecture_facts/ Phase 1: Architecture facts extraction

    crews/              LLM agent workflows (CrewAI)
        architecture_analysis/  Phase 2: Architecture analysis
        architecture_synthesis/ Phase 3: Architecture synthesis (C4, arc42)

    hybrid/             Pipeline stages + LLM agents combined
        development_planning/   Phase 4: Development planning
        code_generation/        Phase 5: Code generation + build verification

    shared/             Common utilities, models, and shared tools

Usage:
    aicodegencrew run --preset document
    aicodegencrew codegen --task-id TASK-001
    python -m aicodegencrew list
"""

from .cli import main
from .orchestrator import SDLCOrchestrator

__version__ = "0.6.2"

__all__ = [
    "SDLCOrchestrator",
    "__version__",
    "main",
]
