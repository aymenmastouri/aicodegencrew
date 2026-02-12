"""Service for reading knowledge base files."""

import json
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..schemas import KnowledgeFile, KnowledgeSummary

# Directories excluded from the Knowledge Explorer UI.
# phase0_indexing contains ChromaDB binary data (not human-readable).
_EXCLUDED_DIRS = {"phase0_indexing"}

# File types recognized for rendering.
_FILE_TYPES = {
    ".json": "json",
    ".md": "md",
    ".drawio": "drawio",
    ".html": "html",
    ".adoc": "adoc",
    ".confluence": "confluence",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}

# Binary/internal files excluded from listing.
_EXCLUDED_NAMES = {"run_report.json", ".indexing_state.json"}
_EXCLUDED_SUFFIXES = {".sqlite3", ".bin", ".pickle"}


def _file_type(path: Path) -> str:
    return _FILE_TYPES.get(path.suffix.lower(), "other")


def _is_excluded(path: Path, knowledge_dir: Path) -> bool:
    """Check if a file should be excluded from the Knowledge Explorer."""
    rel = path.relative_to(knowledge_dir)
    # Exclude entire directories (e.g. phase0_indexing)
    if rel.parts and rel.parts[0] in _EXCLUDED_DIRS:
        return True
    # Exclude specific filenames
    if path.name in _EXCLUDED_NAMES:
        return True
    # Exclude binary file types
    if path.suffix.lower() in _EXCLUDED_SUFFIXES:
        return True
    return False


def list_knowledge_files() -> KnowledgeSummary:
    """List all files in the knowledge directory (excluding indexing data)."""
    knowledge_dir = settings.knowledge_dir
    if not knowledge_dir.exists():
        return KnowledgeSummary(total_files=0, total_size_bytes=0, files=[])

    files: list[KnowledgeFile] = []
    total_size = 0

    for path in sorted(knowledge_dir.rglob("*")):
        if not path.is_file():
            continue
        if _is_excluded(path, knowledge_dir):
            continue
        size = path.stat().st_size
        total_size += size
        files.append(
            KnowledgeFile(
                path=str(path.relative_to(knowledge_dir)),
                name=path.name,
                size_bytes=size,
                modified=datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                type=_file_type(path),
            )
        )

    return KnowledgeSummary(total_files=len(files), total_size_bytes=total_size, files=files)


def read_knowledge_file(relative_path: str) -> dict | list | str:
    """Read a knowledge file by relative path."""
    file_path = settings.knowledge_dir / relative_path
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")

    # Security: prevent path traversal
    try:
        file_path.resolve().relative_to(settings.knowledge_dir.resolve())
    except ValueError:
        raise ValueError("Path traversal not allowed")

    if file_path.suffix == ".json":
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    with open(file_path, encoding="utf-8") as f:
        return f.read()
