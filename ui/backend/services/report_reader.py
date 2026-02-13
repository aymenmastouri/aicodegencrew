"""Service for reading development plans and codegen reports."""

import json
import os
import re
import subprocess
from pathlib import Path

from ..config import settings
from ..schemas import BranchInfo, BranchList, ReportList


def list_reports() -> ReportList:
    """List all development plans and codegen reports."""
    plans = _read_json_dir(settings.knowledge_dir / "plan", "*_plan.json")
    reports = _read_json_dir(settings.knowledge_dir / "implement", "*_report.json")
    return ReportList(plans=plans, codegen_reports=reports)


def read_report(report_type: str, task_id: str) -> dict:
    """Read a specific plan or report by task_id."""
    if report_type == "plan":
        path = settings.knowledge_dir / "plan" / f"{task_id}_plan.json"
    elif report_type == "report":
        path = settings.knowledge_dir / "implement" / f"{task_id}_report.json"
    else:
        raise ValueError(f"Unknown report type: {report_type}")

    if not path.exists():
        raise FileNotFoundError(f"Not found: {path.name}")

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_codegen_branches() -> BranchList:
    """List all codegen/* branches from the target project repo."""
    project_path = os.getenv("PROJECT_PATH", "")
    if not project_path or not Path(project_path).is_dir():
        return BranchList()

    try:
        result = subprocess.run(
            ["git", "branch", "--list", "codegen/*"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return BranchList(repo_path=project_path)

    if result.returncode != 0:
        return BranchList(repo_path=project_path)

    branches: list[BranchInfo] = []
    for line in result.stdout.strip().splitlines():
        name = line.strip().lstrip("* ")
        if not name.startswith("codegen/"):
            continue
        task_id = name[len("codegen/") :]

        # Count files changed vs main
        file_count = 0
        try:
            diff_result = subprocess.run(
                ["git", "diff", "--name-only", f"main...{name}"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if diff_result.returncode == 0 and diff_result.stdout.strip():
                file_count = len(diff_result.stdout.strip().splitlines())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check if codegen report exists
        report_path = settings.knowledge_dir / "implement" / f"{task_id}_report.json"
        has_report = report_path.exists()

        branches.append(
            BranchInfo(
                name=name,
                task_id=task_id,
                file_count=file_count,
                has_report=has_report,
            )
        )

    return BranchList(branches=branches, repo_path=project_path)


def delete_codegen_branch(task_id: str) -> dict:
    """Delete a codegen branch by task_id."""
    if not re.match(r"^[A-Za-z0-9_-]+$", task_id):
        raise ValueError(f"Invalid task_id: {task_id}")

    project_path = os.getenv("PROJECT_PATH", "")
    if not project_path or not Path(project_path).is_dir():
        raise ValueError("PROJECT_PATH not set or not a directory")

    branch_name = f"codegen/{task_id}"
    result = subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to delete branch {branch_name}: {result.stderr.strip()}")

    return {"status": "deleted", "branch": branch_name}


def _read_json_dir(directory: Path, pattern: str) -> list[dict]:
    """Read all JSON files matching pattern in a directory."""
    if not directory.exists():
        return []
    results = []
    for path in sorted(directory.glob(pattern)):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = path.name
                results.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return results
