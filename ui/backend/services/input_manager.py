"""Service for managing pipeline input files (tasks, requirements, logs, reference)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import settings
from .env_manager import read_env, write_env

# Max upload size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024

CATEGORIES: dict[str, dict[str, Any]] = {
    "tasks": {
        "env_key": "TASK_INPUT_DIR",
        "label": "Task Files",
        "description": "JIRA exports, tickets, and task descriptions",
        "accepted_extensions": {".xml", ".docx", ".doc", ".pdf", ".txt", ".json"},
        "icon": "task_alt",
    },
    "requirements": {
        "env_key": "REQUIREMENTS_DIR",
        "label": "Requirements",
        "description": "Requirements documents, specifications, and matrices",
        "accepted_extensions": {".xlsx", ".xls", ".docx", ".doc", ".pdf", ".txt", ".csv"},
        "icon": "description",
    },
    "logs": {
        "env_key": "LOGS_DIR",
        "label": "Application Logs",
        "description": "Application logs for analysis and debugging",
        "accepted_extensions": {".log", ".txt", ".xlsx", ".xls", ".csv"},
        "icon": "receipt_long",
    },
    "reference": {
        "env_key": "REFERENCE_DIR",
        "label": "Reference Materials",
        "description": "Mockups, diagrams, and design documents",
        "accepted_extensions": {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".docx", ".pptx", ".drawio", ".md"},
        "icon": "image",
    },
}

_MANAGED_BASE = "inputs"


def _managed_dir(category: str) -> Path:
    """Return the managed directory path for a category."""
    return settings.project_root / _MANAGED_BASE / category


def _safe_filename(filename: str) -> str:
    """Sanitize filename: strip directory components, prevent path traversal."""
    # Take only the basename
    name = Path(filename).name
    # Remove any remaining path separators or null bytes
    name = re.sub(r"[/\\:\x00]", "", name)
    # Collapse multiple dots (prevent hidden files on unix)
    name = re.sub(r"^\.+", "", name)
    if not name:
        raise ValueError("Invalid filename")
    return name


def _validate_extension(category: str, filename: str) -> None:
    """Check file extension against category's accepted set."""
    cat = CATEGORIES.get(category)
    if not cat:
        raise ValueError(f"Unknown category: {category}")
    ext = Path(filename).suffix.lower()
    if ext not in cat["accepted_extensions"]:
        accepted = ", ".join(sorted(cat["accepted_extensions"]))
        raise ValueError(f"Extension '{ext}' not accepted for {category}. Accepted: {accepted}")


def _resolve_category_dir(category: str) -> Path:
    """Resolve the effective directory for a category.

    Priority:
    1. .env value if set and directory exists (external mode)
    2. Managed inputs/{category}/ directory (GUI mode)
    """
    cat = CATEGORIES[category]
    env_values = read_env()
    env_path = env_values.get(cat["env_key"], "").strip()

    if env_path:
        p = Path(env_path)
        if p.is_dir():
            return p

    # Fallback to managed directory
    return _managed_dir(category)


def _ensure_env_configured(category: str) -> None:
    """Auto-set .env var to managed dir if currently empty or pointing to non-existent path."""
    cat = CATEGORIES[category]
    env_values = read_env()
    current = env_values.get(cat["env_key"], "").strip()

    if current:
        # Don't overwrite intentional external paths that exist
        if Path(current).is_dir():
            return

    managed = _managed_dir(category)
    write_env({cat["env_key"]: str(managed)})


def save_uploaded_file(category: str, filename: str, content: bytes) -> dict[str, Any]:
    """Validate, sanitize, and save an uploaded file.

    Returns file metadata dict.
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")

    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB")

    safe_name = _safe_filename(filename)
    _validate_extension(category, safe_name)

    # Upload to wherever the pipeline reads from:
    # external dir if configured, otherwise managed inputs/{category}/
    target_dir = _resolve_category_dir(category)
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / safe_name

    # Deduplicate: append counter if file exists
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        safe_name = target_path.name

    target_path.write_bytes(content)

    # Auto-configure .env to point to managed directory
    _ensure_env_configured(category)

    return {
        "filename": safe_name,
        "category": category,
        "size_bytes": len(content),
        "path": str(target_path),
    }


def delete_input_file(category: str, filename: str) -> bool:
    """Delete a file from the category directory. Returns True if deleted."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")

    safe_name = _safe_filename(filename)
    target_dir = _resolve_category_dir(category)
    target_path = target_dir / safe_name

    # Path traversal protection: ensure resolved path is inside target dir
    try:
        target_path.resolve().relative_to(target_dir.resolve())
    except ValueError:
        raise ValueError("Path traversal detected")

    if target_path.exists():
        target_path.unlink()
        return True
    return False


def list_category_files(category: str) -> list[dict[str, Any]]:
    """List all files in a category directory with metadata."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}")

    target_dir = _resolve_category_dir(category)
    accepted = CATEGORIES[category]["accepted_extensions"]
    files: list[dict[str, Any]] = []

    if not target_dir.is_dir():
        return files

    for f in sorted(target_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in accepted:
            stat = f.stat()
            files.append(
                {
                    "filename": f.name,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    "extension": f.suffix.lower(),
                }
            )

    return files


def list_all_inputs() -> dict[str, Any]:
    """List all categories with their files."""
    result: dict[str, Any] = {}
    for category, meta in CATEGORIES.items():
        files = list_category_files(category)
        result[category] = {
            "label": meta["label"],
            "description": meta["description"],
            "icon": meta["icon"],
            "env_key": meta["env_key"],
            "accepted_extensions": sorted(meta["accepted_extensions"]),
            "files": files,
            "file_count": len(files),
            "total_size": sum(f["size_bytes"] for f in files),
        }
    return result


def get_category_summary() -> dict[str, Any]:
    """Lightweight summary: counts per category for dashboard widgets."""
    summary: dict[str, Any] = {"categories": {}, "total_files": 0, "total_size": 0}
    for category, meta in CATEGORIES.items():
        files = list_category_files(category)
        count = len(files)
        size = sum(f["size_bytes"] for f in files)
        summary["categories"][category] = {
            "label": meta["label"],
            "icon": meta["icon"],
            "file_count": count,
            "total_size": size,
        }
        summary["total_files"] += count
        summary["total_size"] += size
    return summary


def get_categories_metadata() -> list[dict[str, Any]]:
    """Return category metadata (labels, accepted extensions) for frontend rendering."""
    result = []
    for category, meta in CATEGORIES.items():
        result.append(
            {
                "id": category,
                "label": meta["label"],
                "description": meta["description"],
                "icon": meta["icon"],
                "env_key": meta["env_key"],
                "accepted_extensions": sorted(meta["accepted_extensions"]),
            }
        )
    return result
