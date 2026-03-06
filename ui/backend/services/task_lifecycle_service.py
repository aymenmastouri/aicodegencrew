"""Task Lifecycle Service — unified view of a task's journey through all SDLC phases."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Phase definitions in lifecycle order
_PHASES = ("triage", "plan", "implement", "verify", "deliver")

_knowledge = settings.knowledge_dir
_inputs_tasks = settings.project_root / "inputs" / "tasks"


def _safe_read_json(path: Path) -> dict | None:
    """Read a JSON file, returning None on any error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _file_mtime_iso(path: Path) -> str:
    """Return ISO-formatted mtime for a file."""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _discover_task_ids() -> set[str]:
    """Discover all known task IDs from input files and phase outputs."""
    ids: set[str] = set()

    # Source 1: input task files
    if _inputs_tasks.is_dir():
        for f in _inputs_tasks.iterdir():
            if f.is_file():
                ids.add(f.stem)

    # Source 2: triage outputs
    triage_dir = _knowledge / "triage"
    if triage_dir.is_dir():
        for f in triage_dir.glob("*_triage.json"):
            ids.add(f.stem.replace("_triage", ""))

    # Source 3: plan outputs
    plan_dir = _knowledge / "plan"
    if plan_dir.is_dir():
        for f in plan_dir.glob("*_plan.json"):
            ids.add(f.stem.replace("_plan", ""))

    # Source 4: implement outputs
    impl_dir = _knowledge / "implement"
    if impl_dir.is_dir():
        for f in impl_dir.glob("*_report.json"):
            ids.add(f.stem.replace("_report", ""))

    return ids


def _load_triage(task_id: str) -> dict:
    """Load triage phase data for a task."""
    triage_dir = _knowledge / "triage"
    main = triage_dir / f"{task_id}_triage.json"
    if not main.exists():
        return {"status": "not_started", "data": None}

    data = _safe_read_json(main) or {}
    result: dict = {"status": "completed", "data": data}

    # Attach markdown reports if available
    for suffix, key in [("_customer.md", "customer_md"), ("_developer.md", "developer_md")]:
        md_file = triage_dir / f"{task_id}{suffix}"
        if md_file.exists():
            try:
                result[key] = md_file.read_text(encoding="utf-8")
            except Exception:
                pass

    findings_file = triage_dir / f"{task_id}_findings.json"
    if findings_file.exists():
        result["findings"] = _safe_read_json(findings_file)

    return result


def _load_plan(task_id: str) -> dict:
    """Load plan phase data for a task."""
    plan_file = _knowledge / "plan" / f"{task_id}_plan.json"
    if not plan_file.exists():
        return {"status": "not_started", "data": None}
    return {"status": "completed", "data": _safe_read_json(plan_file) or {}}


def _load_implement(task_id: str) -> dict:
    """Load implement phase data for a task."""
    report_file = _knowledge / "implement" / f"{task_id}_report.json"
    if not report_file.exists():
        return {"status": "not_started", "data": None}
    return {"status": "completed", "data": _safe_read_json(report_file) or {}}


def _load_generic_phase(task_id: str, phase: str) -> dict:
    """Load verify or deliver phase data — look for any {task_id}_*.json in phase dir."""
    phase_dir = _knowledge / phase
    if not phase_dir.is_dir():
        return {"status": "not_started", "data": None}

    # Try canonical name first
    canonical = phase_dir / f"{task_id}_{phase}.json"
    if canonical.exists():
        return {"status": "completed", "data": _safe_read_json(canonical) or {}}

    # Fall back to any file matching the task_id
    for f in phase_dir.glob(f"{task_id}_*.json"):
        return {"status": "completed", "data": _safe_read_json(f) or {}}

    return {"status": "not_started", "data": None}


_PHASE_LOADERS = {
    "triage": _load_triage,
    "plan": _load_plan,
    "implement": _load_implement,
    "verify": lambda tid: _load_generic_phase(tid, "verify"),
    "deliver": lambda tid: _load_generic_phase(tid, "deliver"),
}


def _get_phase_status(task_id: str, phase: str) -> str:
    """Quick status check without loading full data."""
    phase_dir = _knowledge / phase
    if not phase_dir.is_dir():
        return "not_started"

    patterns = {
        "triage": f"{task_id}_triage.json",
        "plan": f"{task_id}_plan.json",
        "implement": f"{task_id}_report.json",
        "verify": f"{task_id}_*.json",
        "deliver": f"{task_id}_*.json",
    }
    pattern = patterns.get(phase, f"{task_id}_*.json")

    if "*" in pattern:
        return "completed" if any(phase_dir.glob(pattern)) else "not_started"
    return "completed" if (phase_dir / pattern).exists() else "not_started"


def _newest_mtime(task_id: str) -> str | None:
    """Find the newest mtime across all phase files for this task."""
    newest: float = 0
    for phase in _PHASES:
        phase_dir = _knowledge / phase
        if not phase_dir.is_dir():
            continue
        for f in phase_dir.glob(f"{task_id}_*"):
            try:
                mt = f.stat().st_mtime
                if mt > newest:
                    newest = mt
            except Exception:
                continue
    if newest == 0:
        return None
    return datetime.fromtimestamp(newest, tz=timezone.utc).isoformat()


def get_input_task_ids() -> list[str]:
    """Return task IDs from inputs/tasks/ directory."""
    if not _inputs_tasks.is_dir():
        return []
    return sorted(
        f.stem for f in _inputs_tasks.iterdir()
        if f.is_file() and not f.name.startswith(".") and _SAFE_ID_RE.match(f.stem)
    )


def list_tasks() -> list[dict]:
    """Discover all task IDs and return a summary for each."""
    task_ids = _discover_task_ids()
    tasks = []
    for task_id in sorted(task_ids):
        if not _SAFE_ID_RE.match(task_id):
            continue

        # Quick metadata from triage if available
        classification_type = None
        risk_level = None
        triage_file = _knowledge / "triage" / f"{task_id}_triage.json"
        if triage_file.exists():
            triage_data = _safe_read_json(triage_file)
            if triage_data:
                cls = triage_data.get("classification", {})
                classification_type = cls.get("type")
                findings = triage_data.get("findings", {})
                risk = findings.get("risk_assessment", {})
                risk_level = risk.get("risk_level")

        phase_status = {phase: _get_phase_status(task_id, phase) for phase in _PHASES}

        tasks.append({
            "task_id": task_id,
            "classification_type": classification_type,
            "risk_level": risk_level,
            "phase_status": phase_status,
            "last_activity": _newest_mtime(task_id),
        })

    return tasks


def get_task_lifecycle(task_id: str) -> dict:
    """Full lifecycle data for one task."""
    has_input = False
    if _inputs_tasks.is_dir():
        has_input = any(_inputs_tasks.glob(f"{task_id}.*"))

    phases = {}
    for phase in _PHASES:
        loader = _PHASE_LOADERS[phase]
        phases[phase] = loader(task_id)

    return {
        "task_id": task_id,
        "has_input": has_input,
        "phases": phases,
    }
