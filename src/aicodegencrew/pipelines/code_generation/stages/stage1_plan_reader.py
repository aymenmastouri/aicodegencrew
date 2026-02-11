"""
Stage 1: Plan Reader

Reads and validates Phase 4 development plan JSON.
Selects the appropriate code generation strategy.
Resolves component file paths from architecture_facts.json when missing.

Duration: <1s (deterministic)
"""

import json
from pathlib import Path
from typing import Optional

from ..schemas import CodegenPlanInput, ComponentTarget
from ..strategies import STRATEGY_MAP, BaseStrategy
from ....shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class PlanReaderStage:
    """Read Phase 4 plan and prepare codegen input."""

    def __init__(
        self,
        plans_dir: str = "knowledge/development",
        facts_path: str = "knowledge/architecture/architecture_facts.json",
    ):
        self.plans_dir = Path(plans_dir)
        self.facts_path = Path(facts_path)
        self._facts_components: dict | None = None  # Lazy-loaded

    def run(
        self,
        task_id: Optional[str] = None,
        plan_path: Optional[str] = None,
    ) -> tuple[CodegenPlanInput, BaseStrategy]:
        """
        Read and validate a Phase 4 plan.

        Args:
            task_id: Task ID to look up plan file (e.g., BNUVZ-12529).
            plan_path: Direct path to plan JSON (overrides task_id).

        Returns:
            Tuple of (CodegenPlanInput, BaseStrategy)
        """
        # Resolve plan file
        if plan_path:
            path = Path(plan_path)
        elif task_id:
            path = self.plans_dir / f"{task_id}_plan.json"
        else:
            raise ValueError("Either task_id or plan_path must be provided")

        if not path.exists():
            raise FileNotFoundError(f"Plan not found: {path}")

        logger.info(f"[Stage1] Reading plan: {path}")

        # Load JSON
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        # Extract fields from Phase 4 output structure
        plan_input = self._parse_plan(raw, path)

        # Select strategy
        strategy_cls = STRATEGY_MAP.get(plan_input.task_type)
        if not strategy_cls:
            raise ValueError(f"Unknown task_type: {plan_input.task_type}")

        strategy = strategy_cls()

        logger.info(
            f"[Stage1] Plan loaded: task_id={plan_input.task_id}, "
            f"type={plan_input.task_type}, "
            f"components={len(plan_input.affected_components)}, "
            f"strategy={strategy.__class__.__name__}"
        )

        return plan_input, strategy

    def _parse_plan(self, raw: dict, source_path: Path) -> CodegenPlanInput:
        """Parse Phase 4 plan JSON into CodegenPlanInput."""
        task_id = raw.get("task_id", source_path.stem.replace("_plan", ""))

        # Phase 4 nests everything under development_plan
        dev_plan = raw.get("development_plan", {})

        # Extract understanding for summary/description
        understanding = raw.get("understanding", {})
        summary = understanding.get("summary", "")
        description = understanding.get("description", "")

        # Task type detection
        task_type = self._detect_task_type(raw, dev_plan)

        # Extract affected components
        components = self._parse_components(dev_plan.get("affected_components", []))

        # Implementation steps
        steps = dev_plan.get("implementation_steps", [])

        # Upgrade plan (for upgrade tasks)
        upgrade_plan = dev_plan.get("upgrade_plan")

        # Patterns
        patterns = {
            "test_strategy": dev_plan.get("test_strategy", {}),
            "security_considerations": dev_plan.get("security_considerations", []),
            "validation_strategy": dev_plan.get("validation_strategy", []),
            "error_handling": dev_plan.get("error_handling", []),
        }

        # Architecture context
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

    def _detect_task_type(self, raw: dict, dev_plan: dict) -> str:
        """Detect task type from plan data."""
        # Check if upgrade plan is present
        if dev_plan.get("upgrade_plan"):
            return "upgrade"

        # Check understanding
        understanding = raw.get("understanding", {})
        summary = (understanding.get("summary", "") or "").lower()

        if any(kw in summary for kw in ("upgrade", "migration", "update version")):
            return "upgrade"
        if any(kw in summary for kw in ("bug", "fix", "defect", "error")):
            return "bugfix"
        if any(kw in summary for kw in ("refactor", "restructure", "clean up")):
            return "refactoring"

        # Check complexity reasoning
        reasoning = dev_plan.get("complexity_reasoning", "").lower()
        if "upgrade" in reasoning or "migration" in reasoning:
            return "upgrade"

        return "feature"

    def _parse_components(self, raw_components: list) -> list[ComponentTarget]:
        """Parse component dicts into ComponentTarget models.

        Resolves missing file_path from architecture_facts.json when needed.
        """
        components = []
        for comp in raw_components:
            if not isinstance(comp, dict):
                continue
            try:
                file_path = comp.get("file_path", "")

                # Resolve from facts if file_path is missing
                if not file_path:
                    file_path = self._resolve_file_path(
                        comp.get("id", ""), comp.get("name", "")
                    )

                components.append(
                    ComponentTarget(
                        id=comp.get("id", ""),
                        name=comp.get("name", ""),
                        file_path=file_path,
                        stereotype=comp.get("stereotype", "unknown"),
                        layer=comp.get("layer", "unknown"),
                        change_type=comp.get("change_type", "modify"),
                        relevance_score=float(comp.get("relevance_score", 0)),
                    )
                )
            except Exception:
                continue
        return components

    def _resolve_file_path(self, component_id: str, component_name: str) -> str:
        """Resolve a component's file path from architecture_facts.json.

        Lookup order:
        1. Exact component ID match → file_paths[0]
        2. Component name match → file_paths[0]
        3. Empty string (unresolved)
        """
        index = self._get_facts_index()
        if not index:
            return ""

        # Try by ID
        entry = index.get(component_id)
        if entry:
            paths = entry.get("file_paths", [])
            if paths:
                return paths[0]

        # Try by name (case-insensitive)
        name_lower = component_name.lower()
        for comp in index.values():
            if comp.get("name", "").lower() == name_lower:
                paths = comp.get("file_paths", [])
                if paths:
                    return paths[0]

        return ""

    def _get_facts_index(self) -> dict:
        """Lazy-load component index from architecture_facts.json.

        Returns dict keyed by component ID for O(1) lookup.
        """
        if self._facts_components is not None:
            return self._facts_components

        self._facts_components = {}

        if not self.facts_path.exists():
            logger.debug(f"[Stage1] Facts not found at {self.facts_path}, skipping file_path resolution")
            return self._facts_components

        try:
            with open(self.facts_path, "r", encoding="utf-8") as f:
                facts = json.load(f)
            for comp in facts.get("components", []):
                cid = comp.get("id", "")
                if cid:
                    self._facts_components[cid] = comp
            logger.debug(f"[Stage1] Loaded {len(self._facts_components)} components from facts")
        except Exception as e:
            logger.warning(f"[Stage1] Could not load facts: {e}")

        return self._facts_components
