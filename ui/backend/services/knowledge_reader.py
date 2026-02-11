"""Service for reading knowledge base files."""

import json
from pathlib import Path
from datetime import datetime

from ..config import settings
from ..schemas import KnowledgeFile, KnowledgeSummary


def _file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {".json": "json", ".md": "md", ".drawio": "drawio"}.get(suffix, "other")


def list_knowledge_files() -> KnowledgeSummary:
    """List all files in the knowledge directory."""
    knowledge_dir = settings.knowledge_dir
    if not knowledge_dir.exists():
        return KnowledgeSummary(total_files=0, total_size_bytes=0, files=[])

    files: list[KnowledgeFile] = []
    total_size = 0

    for path in sorted(knowledge_dir.rglob("*")):
        if path.is_file() and not any(
            p == "archive" for p in path.relative_to(knowledge_dir).parts
        ):
            size = path.stat().st_size
            total_size += size
            files.append(
                KnowledgeFile(
                    path=str(path.relative_to(knowledge_dir)),
                    name=path.name,
                    size_bytes=size,
                    modified=datetime.fromtimestamp(
                        path.stat().st_mtime
                    ).isoformat(),
                    type=_file_type(path),
                )
            )

    return KnowledgeSummary(
        total_files=len(files), total_size_bytes=total_size, files=files
    )


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
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
