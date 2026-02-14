"""Central path constants for all SDLC phases.

Single source of truth — every pipeline, crew, and backend service
imports from here instead of hardcoding directory names.

All paths are RELATIVE segments. Use ``resolve_knowledge_dir(repo_path)``
to get an absolute base path tied to the target repository.
"""

from pathlib import Path

# Phase output directories (relative segments inside knowledge/)
PHASE_DIRS: dict[str, str] = {
    "discover": "knowledge/discover",
    "extract": "knowledge/extract",
    "analyze": "knowledge/analyze",
    "document": "knowledge/document",
    "plan": "knowledge/plan",
    "implement": "knowledge/implement",
    "verify": "knowledge/verify",
    "deliver": "knowledge/deliver",
}

# Frequently-used file paths (relative segments)
PHASE1_FACTS = "knowledge/extract/architecture_facts.json"
PHASE1_EVIDENCE = "knowledge/extract/evidence_map.json"
PHASE2_ANALYSIS = "knowledge/analyze/analyzed_architecture.json"

# ChromaDB lives inside discover phase (relative segment)
CHROMA_DIR = "knowledge/discover"


def resolve_knowledge_dir(repo_path: str | Path) -> Path:
    """Resolve ``knowledge/`` directory relative to the target repository.

    Returns an absolute path so all downstream consumers are CWD-independent.
    """
    return (Path(repo_path) / "knowledge").resolve()


def resolve_phase_dir(repo_path: str | Path, phase_id: str) -> Path:
    """Resolve a single phase output directory relative to the target repo."""
    segment = PHASE_DIRS.get(phase_id, f"knowledge/{phase_id}")
    return (Path(repo_path) / segment).resolve()


def resolve_chroma_dir(repo_path: str | Path) -> str:
    """Resolve ChromaDB directory relative to the target repository."""
    return str((Path(repo_path) / CHROMA_DIR).resolve())
