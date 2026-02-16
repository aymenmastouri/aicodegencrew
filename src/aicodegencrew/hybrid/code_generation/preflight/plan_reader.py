"""Preflight: Plan reader for Phase 4 development plan JSON.

Reads and validates plan files, resolves component file paths
from architecture_facts.json. No strategy dependency — agents
decide approach themselves based on task_type in the plan.

Duration: <1s (deterministic)
"""

import json
from pathlib import Path

from ....shared.utils.logger import setup_logger
from ..schemas import CodegenPlanInput, ComponentTarget

logger = setup_logger(__name__)


class PlanReader:
    """Read Phase 4 plan and prepare codegen input."""

    def __init__(
        self,
        plans_dir: str = "knowledge/plan",
        facts_path: str = "knowledge/extract/architecture_facts.json",
    ):
        self.plans_dir = Path(plans_dir)
        self.facts_path = Path(facts_path)
        self._facts_components: dict | None = None
        self._container_roots: dict[str, str] = {}

    def run(
        self,
        task_id: str | None = None,
        plan_path: str | None = None,
    ) -> CodegenPlanInput:
        """Read and validate a Phase 4 plan.

        Args:
            task_id: Task ID to look up plan file (e.g., PROJ-123).
            plan_path: Direct path to plan JSON (overrides task_id).

        Returns:
            Validated CodegenPlanInput.
        """
        if plan_path:
            path = Path(plan_path)
        elif task_id:
            path = self.plans_dir / f"{task_id}_plan.json"
        else:
            raise ValueError("Either task_id or plan_path must be provided")

        if not path.exists():
            raise FileNotFoundError(f"Plan not found: {path}")

        logger.info("[PlanReader] Reading plan: %s", path)

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        plan_input = self._parse_plan(raw, path)

        logger.info(
            "[PlanReader] Plan loaded: task_id=%s, type=%s, components=%d",
            plan_input.task_id, plan_input.task_type, len(plan_input.affected_components),
        )

        return plan_input

    def _parse_plan(self, raw: dict, source_path: Path) -> CodegenPlanInput:
        task_id = raw.get("task_id", source_path.stem.replace("_plan", ""))

        dev_plan = raw.get("development_plan", {})
        understanding = raw.get("understanding", {})
        summary = understanding.get("summary", "")
        description = understanding.get("description", "")

        task_type = self._detect_task_type(raw, dev_plan)
        components = self._parse_components(dev_plan.get("affected_components", []))
        steps = dev_plan.get("implementation_steps", [])
        upgrade_plan = dev_plan.get("upgrade_plan")

        patterns = {
            "test_strategy": dev_plan.get("test_strategy", {}),
            "security_considerations": dev_plan.get("security_considerations", []),
            "validation_strategy": dev_plan.get("validation_strategy", []),
            "error_handling": dev_plan.get("error_handling", []),
        }

        arch_ctx = dev_plan.get("architecture_context", {})

        return CodegenPlanInput(
            task_id=task_id,
            task_type=task_type,
            summary=summary,
            description=description,
            affected_components=components,
            implementation_steps=steps,
            upgrade_plan=upgrade_plan,
            patterns=patterns,
            architecture_context=arch_ctx,
        )

    @staticmethod
    def _detect_task_type(raw: dict, dev_plan: dict) -> str:
        if dev_plan.get("upgrade_plan"):
            return "upgrade"

        understanding = raw.get("understanding", {})
        summary = (understanding.get("summary", "") or "").lower()

        if any(kw in summary for kw in ("upgrade", "migration", "update version")):
            return "upgrade"
        if any(kw in summary for kw in ("bug", "fix", "defect", "error")):
            return "bugfix"
        if any(kw in summary for kw in ("refactor", "restructure", "clean up")):
            return "refactoring"

        reasoning = dev_plan.get("complexity_reasoning", "").lower()
        if "upgrade" in reasoning or "migration" in reasoning:
            return "upgrade"

        return "feature"

    def _parse_components(self, raw_components: list) -> list[ComponentTarget]:
        components = []
        for comp in raw_components:
            try:
                if isinstance(comp, str):
                    file_path = self._resolve_file_path("", comp)
                    if not file_path:
                        continue
                    components.append(ComponentTarget(
                        id="", name=comp, file_path=file_path, change_type="modify",
                    ))
                elif isinstance(comp, dict):
                    file_path = comp.get("file_path", "")
                    if not file_path:
                        file_path = self._resolve_file_path(comp.get("id", ""), comp.get("name", ""))

                    components.append(ComponentTarget(
                        id=comp.get("id", ""),
                        name=comp.get("name", ""),
                        file_path=file_path,
                        stereotype=comp.get("stereotype", "unknown"),
                        layer=comp.get("layer", "unknown"),
                        change_type=comp.get("change_type", "modify"),
                        relevance_score=float(comp.get("relevance_score", 0)),
                    ))
            except Exception:
                continue
        return components

    def _resolve_file_path(self, component_id: str, component_name: str) -> str:
        index = self._get_facts_index()
        if not index:
            return ""

        def _full_path(entry: dict) -> str:
            paths = entry.get("file_paths", [])
            if not paths:
                return ""
            rel_path = paths[0]
            container_root = self._container_roots.get(entry.get("container", ""), "")
            if container_root:
                return str(Path(container_root) / rel_path)
            return rel_path

        entry = index.get(component_id)
        if entry:
            fp = _full_path(entry)
            if fp:
                return fp

        name_lower = component_name.lower()
        for comp in index.values():
            if comp.get("name", "").lower() == name_lower:
                fp = _full_path(comp)
                if fp:
                    return fp

        return ""

    def _get_facts_index(self) -> dict:
        if self._facts_components is not None:
            return self._facts_components

        self._facts_components = {}
        self._container_roots = {}

        if not self.facts_path.exists():
            return self._facts_components

        try:
            with open(self.facts_path, encoding="utf-8") as f:
                facts = json.load(f)

            for container in facts.get("containers", []):
                cid = container.get("id", "")
                root = container.get("root_path", "")
                if cid and root:
                    self._container_roots[cid] = root

            for comp in facts.get("components", []):
                cid = comp.get("id", "")
                if cid:
                    self._facts_components[cid] = comp
        except Exception as e:
            logger.warning("[PlanReader] Could not load facts: %s", e)

        return self._facts_components
