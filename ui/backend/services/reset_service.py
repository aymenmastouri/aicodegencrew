"""Pipeline reset service — archive + delete phase outputs with cascade."""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ..config import settings
from .history_service import append_run_to_history

logger = logging.getLogger(__name__)

# Phase -> primary output path used for status detection (matches phase_runner.py)
OUTPUT_MAP: dict[str, str] = {
    "phase0_indexing": ".cache/.chroma",
    "phase1_architecture_facts": "knowledge/architecture/architecture_facts.json",
    "phase2_architecture_analysis": "knowledge/architecture/analyzed_architecture.json",
    "phase3_architecture_synthesis": "knowledge/architecture/c4/c4-context.md",
    "phase4_development_planning": "knowledge/development",
    "phase5_code_generation": "knowledge/codegen",
}

# Phase -> all paths to delete on reset
CLEANUP_TARGETS: dict[str, list[str]] = {
    "phase0_indexing": [
        ".cache/.chroma",
        ".cache",
    ],
    "phase1_architecture_facts": [
        "knowledge/architecture/architecture_facts.json",
        "knowledge/architecture/evidence_map.json",
    ],
    "phase2_architecture_analysis": [
        "knowledge/architecture/analyzed_architecture.json",
        ".checkpoint_analysis.json",
    ],
    "phase3_architecture_synthesis": [
        "knowledge/architecture/c4",
        "knowledge/architecture/arc42",
        "knowledge/architecture/runtime",
        "knowledge/architecture/evidence",
        ".checkpoint_c4.json",
        ".checkpoint_arc42.json",
    ],
    "phase4_development_planning": [
        "knowledge/development",
    ],
    "phase5_code_generation": [
        "knowledge/codegen",
    ],
}


def _load_dependencies() -> dict[str, list[str]]:
    """Load phase dependency graph from phases_config.yaml."""
    if not settings.phases_config.exists():
        return {}
    with open(settings.phases_config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    deps: dict[str, list[str]] = {}
    for phase_id, phase_cfg in cfg.get("phases", {}).items():
        deps[phase_id] = phase_cfg.get("dependencies", [])
    return deps


def compute_cascade(phase_ids: list[str]) -> list[str]:
    """Compute the full set of phases to reset via forward propagation.

    If phase A is being reset and phase B depends (directly or transitively)
    on A, then B must also be reset.
    """
    deps = _load_dependencies()

    # Build reverse map: phase -> set of phases that depend on it
    dependents: dict[str, set[str]] = {}
    for pid, dep_list in deps.items():
        for dep in dep_list:
            dependents.setdefault(dep, set()).add(pid)

    to_reset = set(phase_ids)
    queue = list(phase_ids)
    while queue:
        current = queue.pop(0)
        for child in dependents.get(current, set()):
            if child not in to_reset:
                to_reset.add(child)
                queue.append(child)

    # Sort by order (phase number embedded in id)
    all_phases = list(deps.keys())
    return sorted(to_reset, key=lambda p: all_phases.index(p) if p in all_phases else 99)


def _resolve_paths(phase_id: str) -> list[Path]:
    """Return absolute paths for a phase's cleanup targets."""
    targets = CLEANUP_TARGETS.get(phase_id, [])
    paths: list[Path] = []
    for rel in targets:
        p = settings.project_root / rel
        if p.exists():
            paths.append(p)
    return paths


def preview_reset(
    phase_ids: list[str],
    cascade: bool = True,
) -> dict:
    """Dry-run: returns which phases and files would be affected."""
    phases_to_reset = compute_cascade(phase_ids) if cascade else list(phase_ids)
    files: list[str] = []
    for pid in phases_to_reset:
        for p in _resolve_paths(pid):
            if p.is_dir():
                files.extend(str(f) for f in p.rglob("*") if f.is_file())
            else:
                files.append(str(p))

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive_path = str(settings.knowledge_dir / "archive" / f"reset_{ts}")

    return {
        "phases_to_reset": phases_to_reset,
        "files_to_delete": files,
        "archive_path": archive_path,
    }


def execute_reset(
    phase_ids: list[str],
    cascade: bool = True,
    archive: bool = True,
) -> dict:
    """Execute reset: archive, delete, recreate empty dirs, log event."""
    phases_to_reset = compute_cascade(phase_ids) if cascade else list(phase_ids)

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive_dir = settings.knowledge_dir / "archive" / f"reset_{ts}" if archive else None
    deleted_count = 0

    for pid in phases_to_reset:
        paths = _resolve_paths(pid)
        for p in paths:
            if not p.exists():
                continue

            # Archive
            if archive_dir:
                archive_dir.mkdir(parents=True, exist_ok=True)
                dest = archive_dir / pid / p.relative_to(settings.project_root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    if p.is_dir():
                        shutil.copytree(p, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(p, dest)
                except OSError as exc:
                    logger.warning("Archive failed for %s: %s", p, exc)

            # Delete
            try:
                if p.is_dir():
                    count = sum(1 for _ in p.rglob("*") if _.is_file())
                    shutil.rmtree(p)
                    deleted_count += count
                else:
                    p.unlink()
                    deleted_count += 1
            except OSError as exc:
                logger.error("Delete failed for %s: %s", p, exc)

    # Recreate empty dirs for directory-based phases
    for pid in phases_to_reset:
        for rel in CLEANUP_TARGETS.get(pid, []):
            p = settings.project_root / rel
            if not p.suffix and not p.exists():
                p.mkdir(parents=True, exist_ok=True)

    result_ts = datetime.now(UTC).isoformat()

    # Append reset event to run history
    append_run_to_history({
        "run_id": f"reset_{ts}",
        "status": "reset",
        "trigger": "reset",
        "phases": phases_to_reset,
        "started_at": result_ts,
        "completed_at": result_ts,
        "duration_seconds": 0,
        "deleted_count": deleted_count,
        "archive_path": str(archive_dir) if archive_dir else None,
    })

    return {
        "reset_phases": phases_to_reset,
        "deleted_count": deleted_count,
        "archive_path": str(archive_dir) if archive_dir else None,
        "timestamp": result_ts,
    }
