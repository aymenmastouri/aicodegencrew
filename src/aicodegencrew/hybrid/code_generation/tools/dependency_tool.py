"""Dependency lookup tool for Phase 5 agents."""

from __future__ import annotations

import json
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.token_budget import truncate_response
from ..schemas import GenerationOrder


class DependencyLookupInput(BaseModel):
    """Input schema for dependency lookup."""

    file_path: str = Field(..., description="File path to inspect")


class DependencyLookupTool(BaseTool):
    """Return dependency metadata for a file from precomputed generation order."""

    name: str = "lookup_dependencies"
    description: str = (
        "Return depends_on, depended_by and generation tier for a file. "
        "Data comes from deterministic preflight dependency graphing."
    )
    args_schema: type[BaseModel] = DependencyLookupInput

    _order: GenerationOrder = GenerationOrder()

    def __init__(self, generation_order: GenerationOrder | None = None, **kwargs):
        super().__init__(**kwargs)
        if generation_order is not None:
            self._order = generation_order

    def _run(self, file_path: str) -> str:
        norm = file_path.replace("\\", "/")
        basename = Path(norm).name

        entry = None
        for candidate in self._order.ordered_files:
            cpath = candidate.file_path.replace("\\", "/")
            if cpath == norm or Path(cpath).name == basename:
                entry = candidate
                break

        if entry is None:
            return json.dumps(
                {
                    "file_path": file_path,
                    "found": False,
                    "depends_on": [],
                    "depended_by": [],
                    "generation_tier": 0,
                },
                ensure_ascii=False,
            )

        result = {
            "file_path": entry.file_path,
            "found": True,
            "depends_on": entry.depends_on,
            "depended_by": entry.depended_by,
            "generation_tier": entry.generation_tier,
        }
        return truncate_response(json.dumps(result, ensure_ascii=False), hint="dependency lookup truncated")
