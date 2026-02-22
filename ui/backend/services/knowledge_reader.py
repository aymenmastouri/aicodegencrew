"""Service for reading knowledge base files."""

import json
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..schemas import KnowledgeFile, KnowledgeSummary

# Directories excluded from the Knowledge Explorer UI.
# discover contains ChromaDB binary data (not human-readable).
_EXCLUDED_DIRS = {"discover", "archive"}

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
    # Exclude entire directories (e.g. discover)
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


def search_knowledge_files(query: str, max_results: int = 50) -> list[dict]:
    """Search for query string in knowledge text files."""
    results: list[dict] = []
    knowledge_dir = settings.knowledge_dir
    if not knowledge_dir.exists():
        return results
    query_lower = query.lower()
    for path in sorted(knowledge_dir.rglob("*")):
        if not path.is_file() or _is_excluded(path, knowledge_dir):
            continue
        if path.suffix.lower() not in {".json", ".md", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), 1):
                if query_lower in line.lower():
                    results.append(
                        {
                            "file": str(path.relative_to(knowledge_dir)),
                            "line": i,
                            "content": line.strip()[:200],
                        }
                    )
                    if len(results) >= max_results:
                        return results
        except OSError:
            continue
    return results


def generate_container_diagram() -> str:
    """Generate Mermaid graph from containers.json."""
    containers_path = settings.knowledge_dir / "extract" / "containers.json"
    if not containers_path.exists():
        return "graph LR\n  A[No containers data]"
    try:
        data = json.loads(containers_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "graph LR\n  A[Error reading containers]"
    containers = data if isinstance(data, list) else data.get("containers", [])
    if not containers:
        return "graph LR\n  A[No containers found]"

    lines = ["graph TD"]
    # Build nodes (limit for readability)
    seen_ids: set[str] = set()
    for c in containers[:30]:
        name = str(c.get("name", "?")).replace('"', "'")
        tech = str(c.get("technology", ""))
        label = f"{name}<br/><i>{tech}</i>" if tech else name
        cid = _mermaid_id(c.get("id", name))
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        lines.append(f'  {cid}["{label}"]')
    # Add relationships
    for c in containers[:30]:
        cid = _mermaid_id(c.get("id", c.get("name", "")))
        for dep in (c.get("dependencies", []) or [])[:5]:
            did = _mermaid_id(dep)
            if did in seen_ids:
                lines.append(f"  {cid} --> {did}")
    return "\n".join(lines)


def _mermaid_id(raw: object) -> str:
    """Sanitize a string for use as a Mermaid node ID."""
    return str(raw).replace("-", "_").replace(".", "_").replace(" ", "_")


def read_knowledge_file(relative_path: str) -> dict | list | str:
    """Read a knowledge file by relative path."""
    file_path = settings.knowledge_dir / relative_path

    # Security: prevent path traversal BEFORE any file access
    try:
        file_path.resolve().relative_to(settings.knowledge_dir.resolve())
    except ValueError:
        raise ValueError("Path traversal not allowed")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {relative_path}")

    if file_path.suffix == ".json":
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)

    with open(file_path, encoding="utf-8") as f:
        return f.read()
