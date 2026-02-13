"""
AI Code Generation Crew

AI-powered SDLC automation using CrewAI with local Ollama models.

Package Structure:
    aicodegencrew/
        cli.py              # Unified CLI entry point
        orchestrator.py     # SDLC pipeline orchestrator

        pipelines/          # Automated processes (no LLM)
            indexing.py     # Phase 0: Repository indexing
            architecture_facts/  # Phase 1: Architecture facts
            tools/          # Shared pipeline tools
            git_ops/        # Future: Git operations
            cicd/           # Future: CI/CD integration
            merge/          # Future: Merge and release

        crews/              # AI agent workflows (LLM required)
            architecture_synthesis/  # Phase 2: Architecture synthesis
            development/    # Phase 4: AI development (PLANNED)

        shared/             # Common utilities
            utils/
            models/
            tools/

Usage:
    python -m aicodegencrew --list
    python -m aicodegencrew --preset document

    from aicodegencrew import SDLCOrchestrator
    from aicodegencrew.pipelines import IndexingPipeline
    from aicodegencrew.crews import ArchitectureCrew
"""

from .cli import main
from .orchestrator import SDLCOrchestrator

__version__ = "0.3.0"

__all__ = [
    "SDLCOrchestrator",
    "__version__",
    "main",
]
