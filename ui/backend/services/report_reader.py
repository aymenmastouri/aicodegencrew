"""Service for reading development plans and codegen reports."""

import json
from pathlib import Path

from ..config import settings
from ..schemas import ReportList


def list_reports() -> ReportList:
    """List all development plans and codegen reports."""
    plans = _read_json_dir(settings.knowledge_dir / "development", "*_plan.json")
    reports = _read_json_dir(settings.knowledge_dir / "codegen", "*_report.json")
    return ReportList(plans=plans, codegen_reports=reports)


def read_report(report_type: str, task_id: str) -> dict:
    """Read a specific plan or report by task_id."""
    if report_type == "plan":
        path = settings.knowledge_dir / "development" / f"{task_id}_plan.json"
    elif report_type == "report":
        path = settings.knowledge_dir / "codegen" / f"{task_id}_report.json"
    else:
        raise ValueError(f"Unknown report type: {report_type}")

    if not path.exists():
        raise FileNotFoundError(f"Not found: {path.name}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_json_dir(directory: Path, pattern: str) -> list[dict]:
    """Read all JSON files matching pattern in a directory."""
    if not directory.exists():
        return []
    results = []
    for path in sorted(directory.glob(pattern)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = path.name
                results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results
