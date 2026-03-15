# Inject OS/Windows certificate store FIRST — before any HTTP library loads.
# Corporate environments use self-signed CAs that are not in certifi's bundle.
try:
    import truststore as _truststore
    _truststore.inject_into_ssl()
except ImportError:
    pass  # graceful fallback if truststore is not installed

"""
AI Code Generation Crew — SDLC Automation Platform

8-phase pipeline from repository indexing to code generation:

    pipelines/          Pipeline + LLM phases
        indexing/           Phase 0: Repository indexing (ChromaDB)
        architecture_facts/ Phase 1: Architecture facts extraction
        analysis/           Phase 2: Architecture analysis
        triage/             Phase 3: Issue triage
        plan/               Phase 4: Development planning
        document/           Phase 6: Architecture documentation
        review/             Phase 8: Review & consistency guard

    crews/              CrewAI agent phases
        implement/          Phase 5: Code generation + build verification
        testing/            Phase 7: Test generation

    shared/             Common utilities, models, and shared tools

Usage:
    aicodegencrew run --preset document
    aicodegencrew codegen --task-id TASK-001
    python -m aicodegencrew list
"""

from .cli import main
from .orchestrator import SDLCOrchestrator

def _read_version() -> str:
    """Read version from pyproject.toml or importlib.metadata."""
    # 1. Try importlib.metadata (works when package is installed, e.g. in Docker)
    try:
        from importlib.metadata import version
        return version("aicodegencrew")
    except Exception:
        pass
    # 2. Fallback: read pyproject.toml (dev mode)
    from pathlib import Path
    try:
        toml_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if toml_path.exists():
            for line in toml_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("version"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "0.7.3"

__version__ = _read_version()

__all__ = [
    "SDLCOrchestrator",
    "__version__",
    "main",
]
