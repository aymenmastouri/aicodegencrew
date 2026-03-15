"""Deterministic reader for original task sources from TASK_INPUT_DIR.

Primary use case: load real JIRA XML task content for Phase 5 agents, so
the development plan is guidance and not the only source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ....shared.utils.logger import setup_logger
from ....pipelines.plan.parsers.xml_parser import parse_xml

logger = setup_logger(__name__)


class TaskSourceReader:
    """Read original task content from TASK_INPUT_DIR (XML-first)."""

    def __init__(self, task_input_dir: str | None = None):
        self.task_input_dir = (task_input_dir or os.getenv("TASK_INPUT_DIR", "")).strip()

    def run(self, task_id: str) -> dict[str, Any]:
        """Resolve and parse the original task source for *task_id*.

        Returns a normalized dict with `found` flag and parsed task fields.
        """
        if not task_id:
            return {"found": False, "error": "task_id is required"}

        if not self.task_input_dir:
            return {"found": False, "error": "TASK_INPUT_DIR is not configured"}

        task_dir = Path(self.task_input_dir)
        if not task_dir.exists() or not task_dir.is_dir():
            return {"found": False, "error": f"TASK_INPUT_DIR not found: {task_dir}"}

        resolved = self._find_xml_file(task_dir, task_id)
        if not resolved:
            return {
                "found": False,
                "error": f"No XML task source found for {task_id} in {task_dir}",
            }

        file_path, task_payload = resolved
        summary = str(task_payload.get("summary", "") or "")
        description = str(task_payload.get("description", "") or "")
        notes = str(task_payload.get("technical_notes", "") or "")
        criteria = task_payload.get("acceptance_criteria", []) or []
        linked = task_payload.get("linked_tasks", []) or []
        labels = task_payload.get("labels", []) or []
        components = task_payload.get("components", []) or []

        excerpt = self._build_excerpt(summary, description, notes, criteria)

        return {
            "found": True,
            "task_id": str(task_payload.get("task_id", task_id) or task_id),
            "source_file": str(file_path),
            "summary": summary,
            "description": description,
            "priority": str(task_payload.get("priority", "") or ""),
            "jira_type": str(task_payload.get("jira_type", task_payload.get("type", "")) or ""),
            "labels": labels if isinstance(labels, list) else [],
            "components": components if isinstance(components, list) else [],
            "acceptance_criteria": criteria if isinstance(criteria, list) else [],
            "technical_notes": notes,
            "linked_tasks": linked if isinstance(linked, list) else [],
            "excerpt": excerpt,
        }

    def _find_xml_file(self, task_dir: Path, task_id: str) -> tuple[Path, dict[str, Any]] | None:
        task_upper = task_id.upper()

        # Fast path: filename contains task id
        for path in sorted(task_dir.glob("*.xml")):
            if task_upper in path.name.upper():
                task = self._extract_task_from_xml(path, task_id)
                if task is not None:
                    return path, task

        # Fallback: scan all XML files for matching item key
        for path in sorted(task_dir.glob("*.xml")):
            task = self._extract_task_from_xml(path, task_id)
            if task is not None:
                return path, task

        return None

    @staticmethod
    def _extract_task_from_xml(path: Path, task_id: str) -> dict[str, Any] | None:
        try:
            tasks = parse_xml(path)
        except Exception as e:
            logger.debug("[TaskSourceReader] Could not parse %s: %s", path, e)
            return None

        task_upper = task_id.upper()
        for task in tasks:
            current = str(task.get("task_id", "")).upper()
            if current == task_upper:
                return task

        # If file contains only one task and filename matched, we can still use it.
        if len(tasks) == 1:
            return tasks[0]
        return None

    @staticmethod
    def _build_excerpt(summary: str, description: str, notes: str, criteria: list[Any]) -> str:
        lines: list[str] = []
        if summary:
            lines.append(f"Summary: {summary}")
        if description:
            lines.append(f"Description: {description[:1200]}")
        if criteria:
            rendered = "; ".join(str(c) for c in criteria[:8])
            lines.append(f"Acceptance Criteria: {rendered}")
        if notes:
            lines.append(f"Technical Notes: {notes[:1200]}")
        return "\n".join(lines).strip()
