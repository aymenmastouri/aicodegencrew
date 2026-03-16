"""Central path constants for all SDLC phases.

Single source of truth — every pipeline, crew, and backend service
imports from here instead of hardcoding directory names.

All paths are RELATIVE to the project root (CWD).
The target repository (repo_path) is only used as INPUT for analysis.
Phase outputs always go into the PROJECT's knowledge/ directory.
"""

from pathlib import Path

# Phase output directories (relative to project root)
PHASE_DIRS: dict[str, str] = {
    "discover": "knowledge/discover",
    "extract": "knowledge/extract",
    "analyze": "knowledge/analyze",
    "document": "knowledge/document",
    "triage": "knowledge/triage",
    "plan": "knowledge/plan",
    "implement": "knowledge/implement",
    "verify": "knowledge/verify",
    "deliver": "knowledge/deliver",
}

# Frequently-used file paths (relative to project root)
KNOWLEDGE_DIR = Path("knowledge")
PHASE1_FACTS = "knowledge/extract/architecture_facts.json"
PHASE1_EVIDENCE = "knowledge/extract/evidence_map.json"
PHASE2_ANALYSIS = "knowledge/analyze/analyzed_architecture.json"

# Vector store artifacts live inside discover phase
DISCOVER_DIR = "knowledge/discover"

# Backward-compat alias (deprecated — use DISCOVER_DIR)
CHROMA_DIR = DISCOVER_DIR

# Discover phase artifacts (new in v0.6)
DISCOVER_SYMBOLS = "knowledge/discover/symbols.jsonl"
DISCOVER_EVIDENCE = "knowledge/discover/evidence.jsonl"
DISCOVER_MANIFEST = "knowledge/discover/repo_manifest.json"


# ── Multi-project aware path resolvers ───────────────────────────────────────
# These delegate to project_context to resolve the active project subfolder.
# Import is lazy to avoid circular imports at module load time.


def get_discover_dir(project_slug: str | None = None) -> str:
    """Return discover directory for *project_slug* (or the active project)."""
    from .project_context import get_discover_dir as _ctx_get_discover_dir

    return _ctx_get_discover_dir(project_slug)


# Backward-compat alias (deprecated — use get_discover_dir)
def get_chroma_dir(project_slug: str | None = None) -> str:
    """Deprecated: use get_discover_dir() instead."""
    return get_discover_dir(project_slug)


def get_discover_symbols(project_slug: str | None = None) -> str:
    """Return path to symbols.jsonl for *project_slug* (or the active project)."""
    from .project_context import get_discover_dir

    return str(Path(get_discover_dir(project_slug)) / "symbols.jsonl")


def get_discover_evidence(project_slug: str | None = None) -> str:
    """Return path to evidence.jsonl for *project_slug* (or the active project)."""
    from .project_context import get_discover_dir

    return str(Path(get_discover_dir(project_slug)) / "evidence.jsonl")


def get_discover_manifest(project_slug: str | None = None) -> str:
    """Return path to repo_manifest.json for *project_slug* (or the active project)."""
    from .project_context import get_discover_dir

    return str(Path(get_discover_dir(project_slug)) / "repo_manifest.json")
