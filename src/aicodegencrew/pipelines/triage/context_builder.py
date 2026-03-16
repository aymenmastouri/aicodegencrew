"""KnowledgeLoader — loads all available phase outputs for triage context.

Gracefully handles missing files/phases: missing data = empty dict/list.
"""

import json
from pathlib import Path
from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def _load_json(path: Path) -> Any:
    """Load a JSON file, returning None on failure."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("[KnowledgeLoader] Failed to load %s: %s", path, e)
        return None


def _load_jsonl(path: Path, limit: int = 0) -> list[dict]:
    """Load a JSONL file, returning empty list on failure.

    Args:
        path:  JSONL file path.
        limit: Max records to load (0 = unlimited).
    """
    if not path.exists():
        return []
    records: list[dict] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
                if limit and len(records) >= limit:
                    break
    except Exception as e:
        logger.warning("[KnowledgeLoader] Failed to load %s: %s", path, e)
    return records


def _list_files(directory: Path, pattern: str) -> list[str]:
    """List file paths matching a glob pattern, returning empty list if dir missing."""
    if not directory.exists():
        return []
    return sorted(str(p) for p in directory.glob(pattern))


class KnowledgeLoader:
    """Load all available phase outputs for triage context."""

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.root = Path(knowledge_dir)

    def load_available_context(self) -> dict[str, Any]:
        """Load key files per phase. Missing files/phases → empty values."""
        ctx: dict[str, Any] = {
            "discover": self._load_discover(),
            "extract": self._load_extract(),
            "analyze": self._load_analyze(),
            "document": self._load_document(),
            "state": self._load_state(),
        }
        loaded = [k for k, v in ctx.items() if v]
        logger.info("[KnowledgeLoader] Loaded context from: %s", loaded)
        return ctx

    # ── discover ────────────────────────────────────────────────────────

    def _load_discover(self) -> dict[str, Any]:
        # Try active-project subfolder first, then legacy flat layout
        from ...shared.paths import get_discover_dir

        active_dir = Path(get_discover_dir())
        d = active_dir if active_dir.exists() else self.root / "discover"

        return {
            "symbols": _load_jsonl(d / "symbols.jsonl"),
            "evidence": _load_jsonl(d / "evidence.jsonl"),
            "repo_manifest": _load_json(d / "repo_manifest.json") or {},
            "indexing_state": _load_json(d / ".indexing_state.json") or {},
        }

    # ── extract ─────────────────────────────────────────────────────────

    def _load_extract(self) -> dict[str, Any]:
        d = self.root / "extract"
        return {
            "architecture_facts": _load_json(d / "architecture_facts.json") or {},
        }

    # ── analyze ─────────────────────────────────────────────────────────

    def _load_analyze(self) -> dict[str, Any]:
        d = self.root / "analyze"
        return {
            "analyzed_architecture": _load_json(d / "analyzed_architecture.json") or {},
        }

    # ── document ────────────────────────────────────────────────────────

    def _load_document(self) -> dict[str, Any]:
        d = self.root / "document"
        return {
            "arc42_chapters": _list_files(d / "arc42", "*.md"),
            "c4_diagrams": _list_files(d / "c4", "*.drawio") + _list_files(d / "c4", "*.md"),
            "coverage": _load_json(d / "quality" / "coverage.json") or {},
        }

    # ── state ───────────────────────────────────────────────────────────

    def _load_state(self) -> dict[str, Any]:
        logs_dir = self.root.parent / "logs"
        return {
            "phase_state": _load_json(logs_dir / "phase_state.json") or {},
        }
