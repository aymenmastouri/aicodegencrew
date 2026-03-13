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
    """Generate Mermaid graph from containers.json + relations.json."""
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
    # Build nodes
    seen_ids: set[str] = set()
    container_names: set[str] = set()
    for c in containers[:30]:
        name = str(c.get("name", "?")).replace('"', "'")
        tech = str(c.get("technology", ""))
        label = f"{name}<br/><i>{tech}</i>" if tech else name
        cid = _mermaid_id(c.get("id", name))
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        container_names.add(name)
        lines.append(f'  {cid}["{label}"]')

    # Add relationships from containers.json dependencies (if present)
    for c in containers[:30]:
        cid = _mermaid_id(c.get("id", c.get("name", "")))
        for dep in (c.get("dependencies", []) or [])[:5]:
            did = _mermaid_id(dep)
            if did in seen_ids:
                lines.append(f"  {cid} --> {did}")

    # Derive cross-container edges from relations.json
    relations_path = settings.knowledge_dir / "extract" / "relations.json"
    if relations_path.exists():
        try:
            rel_data = json.loads(relations_path.read_text(encoding="utf-8"))
            rels = (
                rel_data
                if isinstance(rel_data, list)
                else rel_data.get("relations", rel_data.get("items", []))
            )
            from collections import Counter

            edge_counts: Counter[tuple[str, str]] = Counter()
            for r in rels:
                src = str(r.get("source", r.get("from", "")))
                tgt = str(r.get("target", r.get("to", "")))
                src_parts = src.split(".")
                tgt_parts = tgt.split(".")
                if len(src_parts) >= 2 and len(tgt_parts) >= 2:
                    src_cont = src_parts[1]
                    tgt_cont = tgt_parts[1]
                    if src_cont != tgt_cont:
                        edge_counts[(src_cont, tgt_cont)] += 1
            added_edges: set[tuple[str, str]] = set()
            for (src_cont, tgt_cont), count in edge_counts.most_common():
                src_id = _mermaid_id(f"container.{src_cont}")
                tgt_id = _mermaid_id(f"container.{tgt_cont}")
                if (
                    src_id in seen_ids
                    and tgt_id in seen_ids
                    and (src_id, tgt_id) not in added_edges
                ):
                    lines.append(f'  {src_id} -->|"{count} calls"| {tgt_id}')
                    added_edges.add((src_id, tgt_id))
        except (json.JSONDecodeError, OSError):
            pass  # relations unavailable — diagram still shows nodes

    return "\n".join(lines)


def _mermaid_id(raw: object) -> str:
    """Sanitize a string for use as a Mermaid node ID."""
    return str(raw).replace("-", "_").replace(".", "_").replace(" ", "_")


def read_knowledge_file(relative_path: str) -> dict | list | str:
    """Read a knowledge file by relative path."""
    file_path = settings.knowledge_dir / relative_path

    # Security: prevent path traversal and symlink TOCTOU attacks.
    # resolve(strict=True) follows symlinks and requires the path to exist,
    # then we verify the resolved real path is within the allowed base.
    base_resolved = settings.knowledge_dir.resolve()
    try:
        resolved = file_path.resolve(strict=True)
    except OSError:
        raise FileNotFoundError(f"File not found: {relative_path}")
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError("Path traversal not allowed")

    try:
        if resolved.suffix == ".json":
            with open(resolved, encoding="utf-8") as f:
                return json.load(f)

        with open(resolved, encoding="utf-8") as f:
            return f.read()
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {relative_path}: {e}") from e
    except OSError as e:
        raise FileNotFoundError(f"Cannot read {relative_path}: {e}") from e
