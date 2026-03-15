"""Plan reader tool for manager agent."""

from __future__ import annotations

import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.token_budget import truncate_response
from ..preflight.plan_reader import PlanReader


class PlanReaderInput(BaseModel):
    """Input schema for plan reader tool."""

    task_id: str | None = Field(default=None, description="Task ID (e.g. BNUVZ-12529)")
    plan_path: str | None = Field(default=None, description="Explicit path to *_plan.json")


class PlanReaderTool(BaseTool):
    """Read and normalize Phase 4 plan data for crew context."""

    name: str = "read_plan"
    description: str = "Read a development plan JSON and return normalized task context."
    args_schema: type[BaseModel] = PlanReaderInput

    plans_dir: str = "knowledge/plan"
    facts_path: str = "knowledge/extract/architecture_facts.json"

    def __init__(
        self, plans_dir: str = "knowledge/plan", facts_path: str = "knowledge/extract/architecture_facts.json", **kwargs
    ):
        super().__init__(**kwargs)
        self.plans_dir = plans_dir
        self.facts_path = facts_path

    def _run(self, task_id: str | None = None, plan_path: str | None = None) -> str:
        reader = PlanReader(plans_dir=self.plans_dir, facts_path=self.facts_path)
        plan_input = reader.run(task_id=task_id, plan_path=plan_path)

        result = {
            "task_id": plan_input.task_id,
            "task_type": plan_input.task_type,
            "summary": plan_input.summary,
            "description": plan_input.description,
            "affected_components": [c.model_dump() for c in plan_input.affected_components],
            "implementation_steps": plan_input.implementation_steps,
            "upgrade_plan": plan_input.upgrade_plan,
        }
        return truncate_response(json.dumps(result, ensure_ascii=False), hint="plan context truncated")
