"""Pipeline reset service — delete phase outputs with cascade."""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aicodegencrew.shared.utils.logger import archive_metrics, cleanup_old_archives

from ..config import settings
from .history_service import append_run_to_history
from .phase_outputs import PHASE_OUTPUTS, get_cleanup_targets

logger = logging.getLogger(__name__)


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


def _clear_phase_state(phase_ids: list[str]) -> None:
    """Remove phase entries from logs/phase_state.json after reset."""
    import json

    state_path = settings.project_root / "logs" / "phase_state.json"
    if not state_path.exists():
        return
    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        phases = data.get("phases", {})
        for pid in phase_ids:
            phases.pop(pid, None)
        data["updated_at"] = datetime.now(UTC).isoformat()
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to clear phase state: %s", exc)


def _resolve_paths(phase_id: str) -> list[Path]:
    """Return absolute paths for a phase's cleanup targets."""
    targets = get_cleanup_targets(phase_id)
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

    return {
        "phases_to_reset": phases_to_reset,
        "files_to_delete": files,
    }


def _archive_phase_outputs(phases_to_reset: list[str], timestamp: str) -> Path | None:
    """Copy phase outputs to knowledge/archive/reset_{timestamp}/ before deletion."""
    archive_root = settings.project_root / "knowledge" / "archive" / f"reset_{timestamp}"
    archived_anything = False

    for pid in phases_to_reset:
        for p in _resolve_paths(pid):
            dest = archive_root / pid / p.name
            try:
                if p.is_dir():
                    shutil.copytree(p, dest)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)
                archived_anything = True
            except OSError as exc:
                logger.warning("Archive failed for %s: %s", p, exc)

    return archive_root if archived_anything else None


def _cleanup_reset_archives(max_keep: int = 5) -> int:
    """Remove oldest reset archives beyond max_keep."""
    archive_dir = settings.project_root / "knowledge" / "archive"
    if not archive_dir.exists():
        return 0

    dirs = sorted(
        [d for d in archive_dir.iterdir() if d.is_dir() and d.name.startswith("reset_")],
        reverse=True,
    )
    removed = 0
    for old_dir in dirs[max_keep:]:
        shutil.rmtree(old_dir, ignore_errors=True)
        removed += 1
    return removed


def execute_reset(
    phase_ids: list[str],
    cascade: bool = True,
) -> dict:
    """Execute reset: archive phase outputs, delete them, recreate empty dirs, log event."""
    phases_to_reset = compute_cascade(phase_ids) if cascade else list(phase_ids)

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    deleted_count = 0

    # Archive phase outputs before deletion
    archive_path = _archive_phase_outputs(phases_to_reset, ts)

    for pid in phases_to_reset:
        paths = _resolve_paths(pid)
        for p in paths:
            if not p.exists():
                continue

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
        for rel in get_cleanup_targets(pid):
            p = settings.project_root / rel
            if not p.suffix and not p.exists():
                p.mkdir(parents=True, exist_ok=True)

    # Clear phase state entries for reset phases
    _clear_phase_state(phases_to_reset)

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
        "archive_path": str(archive_path) if archive_path else None,
    })

    # Rotate metrics and clean up old archives
    archive_metrics()
    cleanup_old_archives()
    _cleanup_reset_archives()

    return {
        "reset_phases": phases_to_reset,
        "deleted_count": deleted_count,
        "timestamp": result_ts,
        "archive_path": str(archive_path) if archive_path else None,
    }
