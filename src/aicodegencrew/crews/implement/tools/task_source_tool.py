"""Tool for reading original JIRA task source from TASK_INPUT_DIR."""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.token_budget import truncate_response
from ..preflight.task_source_reader import TaskSourceReader


class TaskSourceInput(BaseModel):
    """Input schema for TaskSourceTool."""

    task_id: str = Field(..., description="Task ID (e.g. BNUVZ-12529)")


class TaskSourceTool(BaseTool):
    """Read the actual task source (JIRA XML) from TASK_INPUT_DIR."""

    name: str = "read_task_source"
    description: str = (
        "Read the original task source from TASK_INPUT_DIR (JIRA XML). "
        "Use this as primary intent source; treat development plan as guidance."
    )
    args_schema: type[BaseModel] = TaskSourceInput

    task_input_dir: str = ""

    def __init__(self, task_input_dir: str = "", **kwargs):
        super().__init__(**kwargs)
        self.task_input_dir = task_input_dir

    def _run(self, task_id: str) -> str:
        reader = TaskSourceReader(task_input_dir=self.task_input_dir)
        result = reader.run(task_id=task_id)
        return truncate_response(json.dumps(result, ensure_ascii=False), hint="task source context truncated")
