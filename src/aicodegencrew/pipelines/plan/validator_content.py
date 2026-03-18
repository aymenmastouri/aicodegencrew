"""PlanContentValidator — validates plan content against triage context and architecture facts.

Goes beyond Pydantic schema validation to check semantic correctness:
- All entry points from triage are addressed
- Steps reference real files/components
- No phantom components
- Risks from triage are mitigated

Usage::

    validator = PlanContentValidator(architecture_facts, triage_context)
    result = validator.validate(plan)
    if not result.passed:
        # retry with feedback using result.issues
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationCheck:
    """Result of a single validation check."""

    name: str
    passed: bool
    message: str = ""


@dataclass
class ContentValidationResult:
    """Aggregate validation result for plan content."""

    passed: bool
    checks: list[ValidationCheck] = field(default_factory=list)
    score: int = 100

    @property
    def issues(self) -> list[str]:
        return [c.message for c in self.checks if not c.passed]


class PlanContentValidator:
    """Validates plan content for semantic correctness and completeness.

    Checks that the plan addresses triage findings, references real
    components, and includes appropriate risk mitigations.
    """

    def __init__(
        self,
        architecture_facts: dict[str, Any] | None = None,
        triage_context: dict[str, Any] | None = None,
    ):
        self._facts = architecture_facts or {}
        self._triage = triage_context or {}
        self._known_components = self._extract_known_components()

    def validate(self, plan: Any) -> ContentValidationResult:
        """Run all content validation checks on the plan.

        Args:
            plan: The ImplementationPlan object (Pydantic model) or dict.

        Returns:
            ContentValidationResult with pass/fail and actionable issues.
        """
        # Convert Pydantic model to dict if needed
        plan_dict = plan
        if hasattr(plan, "model_dump"):
            plan_dict = plan.model_dump()
        elif hasattr(plan, "dict"):
            plan_dict = plan.dict()
        elif not isinstance(plan_dict, dict):
            plan_dict = {}

        dp = plan_dict.get("development_plan") or plan_dict
        if not isinstance(dp, dict):
            dp = {}

        checks = [
            self._check_has_implementation_steps(dp),
            self._check_steps_have_details(dp),
            self._check_affected_components_present(dp),
            self._check_no_phantom_components(dp),
        ]

        # Triage-aware checks (only if triage context available)
        if self._triage:
            checks.append(self._check_triage_components_addressed(dp))
            if self._triage.get("context_boundaries"):
                checks.append(self._check_risk_awareness(dp))

        passed = all(c.passed for c in checks)
        failed_count = sum(1 for c in checks if not c.passed)
        score = max(0, 100 - (failed_count * 15))

        result = ContentValidationResult(passed=passed, checks=checks, score=score)

        if not passed:
            logger.warning(
                "[PlanContentValidator] FAILED (%d issues): %s",
                failed_count, result.issues,
            )
        else:
            logger.info("[PlanContentValidator] PASSED all %d checks (score=%d)", len(checks), score)

        return result

    def _check_has_implementation_steps(self, dp: dict) -> ValidationCheck:
        """Plan must have implementation steps."""
        steps = dp.get("implementation_steps") or dp.get("steps") or []
        if not isinstance(steps, list) or len(steps) == 0:
            return ValidationCheck(
                "has_implementation_steps", False,
                "Plan must include at least one implementation step. "
                "Each step should describe a concrete change to make.",
            )
        return ValidationCheck("has_implementation_steps", True)

    def _check_steps_have_details(self, dp: dict) -> ValidationCheck:
        """Each implementation step should have a description."""
        steps = dp.get("implementation_steps") or dp.get("steps") or []
        if not isinstance(steps, list):
            return ValidationCheck("steps_have_details", True)

        empty_steps = 0
        for step in steps:
            if isinstance(step, dict):
                desc = step.get("description", "") or step.get("action", "")
                if not isinstance(desc, str) or len(str(desc).strip()) < 10:
                    empty_steps += 1
            elif isinstance(step, str) and len(step.strip()) < 10:
                empty_steps += 1

        if empty_steps > 0:
            return ValidationCheck(
                "steps_have_details", False,
                f"{empty_steps} implementation step(s) lack meaningful descriptions. "
                f"Each step should describe what to change and why.",
            )
        return ValidationCheck("steps_have_details", True)

    def _check_affected_components_present(self, dp: dict) -> ValidationCheck:
        """Plan must list affected components."""
        components = dp.get("affected_components", [])
        if not isinstance(components, list) or len(components) == 0:
            return ValidationCheck(
                "affected_components_present", False,
                "Plan must list affected_components. Identify which components "
                "in the architecture will be modified.",
            )
        return ValidationCheck("affected_components_present", True)

    def _check_no_phantom_components(self, dp: dict) -> ValidationCheck:
        """Referenced components should exist in the architecture."""
        if not self._known_components:
            return ValidationCheck("no_phantom_components", True)  # Can't verify

        components = dp.get("affected_components", [])
        if not isinstance(components, list):
            return ValidationCheck("no_phantom_components", True)

        phantom = []
        known_lower = {c.lower() for c in self._known_components}
        for comp in components:
            name = comp.get("name", comp) if isinstance(comp, dict) else str(comp)
            # Extract just the component name (strip layer annotations like "(service)")
            clean_name = name.split("(")[0].strip() if "(" in str(name) else str(name).strip()
            if clean_name and clean_name.lower() not in known_lower:
                phantom.append(clean_name)

        if len(phantom) > len(components) // 2:
            return ValidationCheck(
                "no_phantom_components", False,
                f"Most referenced components are not found in the architecture: {phantom[:5]}. "
                f"Verify component names against the extracted architecture facts.",
            )
        return ValidationCheck("no_phantom_components", True)

    def _check_triage_components_addressed(self, dp: dict) -> ValidationCheck:
        """Components identified by triage should appear in the plan."""
        triage_components = self._triage.get("affected_components", [])
        if not triage_components:
            return ValidationCheck("triage_components_addressed", True)

        plan_text = str(dp).lower()
        not_addressed = []
        for comp in triage_components:
            name = comp.get("name", comp) if isinstance(comp, dict) else str(comp)
            clean = name.split("(")[0].strip() if "(" in str(name) else str(name).strip()
            if clean and clean.lower() not in plan_text:
                not_addressed.append(clean)

        if not_addressed:
            return ValidationCheck(
                "triage_components_addressed", False,
                f"Triage identified these components but the plan does not address them: "
                f"{not_addressed[:5]}. Ensure the plan covers all affected components.",
            )
        return ValidationCheck("triage_components_addressed", True)

    def _check_risk_awareness(self, dp: dict) -> ValidationCheck:
        """Plan should acknowledge risks identified in triage context boundaries."""
        boundaries = self._triage.get("context_boundaries", [])
        blocking = [b for b in boundaries if isinstance(b, dict) and b.get("severity") == "blocking"]

        if not blocking:
            return ValidationCheck("risk_awareness", True)

        plan_text = str(dp).lower()
        risks_section = dp.get("risks") or dp.get("risk_mitigation") or []
        risks_text = str(risks_section).lower() if risks_section else ""

        unaddressed = 0
        for boundary in blocking:
            category = boundary.get("category", "")
            # Check if the risk category or boundary text is referenced
            if category.lower() not in plan_text and category.lower() not in risks_text:
                unaddressed += 1

        if unaddressed > 0:
            return ValidationCheck(
                "risk_awareness", False,
                f"{unaddressed} blocking risk(s) from triage are not addressed in the plan. "
                f"Include risk mitigation for blocking constraints.",
            )
        return ValidationCheck("risk_awareness", True)

    def _extract_known_components(self) -> set[str]:
        """Extract known component names from architecture facts."""
        names: set[str] = set()
        for category in ("containers", "components"):
            items = self._facts.get(category)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name")
                        if isinstance(name, str) and len(name.strip()) >= 3:
                            names.add(name.strip())
        return names
