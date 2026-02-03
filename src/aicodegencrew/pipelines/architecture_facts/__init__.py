"""
Phase 1: Architecture Facts Pipeline

Deterministic extraction of architecture facts from source code.
NO LLM. NO interpretation. Only facts + evidence.

Usage:
    from aicodegencrew.pipelines.architecture_facts import ArchitectureFactsPipeline
    
    pipeline = ArchitectureFactsPipeline(repo_path="/path/to/repo")
    result = pipeline.kickoff()
"""

from .pipeline import ArchitectureFactsPipeline

__all__ = [
    "ArchitectureFactsPipeline",
]
