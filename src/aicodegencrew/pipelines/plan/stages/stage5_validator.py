"""
Stage 5: Validator

Validates plan completeness and quality using Pydantic and custom rules.

Duration: <1 second (deterministic)
NO LLM REQUIRED
"""

from ....shared.utils.logger import setup_logger
from ..schemas import ImplementationPlan, ValidationResult

logger = setup_logger(__name__)


class ValidatorStage:
    """
    Validate implementation plan.
    """

    def __init__(self, analyzed_architecture: dict = None):
        """
        Initialize validator.

        Args:
            analyzed_architecture: analyzed_architecture.json (from Phase 2)
        """
        self.analyzed_architecture = analyzed_architecture or {}

    def run(self, plan: ImplementationPlan) -> ValidationResult:
        """
        Validate plan completeness and quality.

        Args:
            plan: Implementation plan from Stage 4

        Returns:
            ValidationResult with is_valid, missing_fields, warnings, errors
        """
        logger.info(f"[Stage5] Validating plan for task: {plan.task_id}")

        missing_fields = []
        warnings = []
        errors = []

        dev_plan = plan.development_plan

        # Check required fields
        required_fields = {
            "affected_components": "at least 1 component",
            "implementation_steps": "at least 1 step",
            "test_strategy": "test strategy",
            "estimated_complexity": "complexity estimate",
            "estimated_files_changed": "file count estimate",
        }

        for field, description in required_fields.items():
            if field not in dev_plan:
                missing_fields.append(f"{field} ({description})")
            elif field == "affected_components":
                if not dev_plan[field] or len(dev_plan[field]) == 0:
                    errors.append("No affected components identified")
            elif field == "implementation_steps":
                if not dev_plan[field] or len(dev_plan[field]) == 0:
                    errors.append("No implementation steps provided")
            elif field == "test_strategy":
                if not dev_plan[field]:
                    warnings.append("Test strategy is empty")
                else:
                    # Check test strategy structure
                    test_strategy = dev_plan[field]
                    if "unit_tests" not in test_strategy:
                        warnings.append("No unit tests specified")
                    if "integration_tests" not in test_strategy:
                        warnings.append("No integration tests specified")

        # Check recommended fields
        recommended_fields = [
            "security_considerations",
            "validation_strategy",
            "error_handling",
            "architecture_context",
            "risks",
        ]

        for field in recommended_fields:
            if field not in dev_plan:
                warnings.append(f"Recommended field missing: {field}")
            elif isinstance(dev_plan[field], list) and len(dev_plan[field]) == 0:
                warnings.append(f"Recommended field is empty: {field}")

        # Validate layer compliance (if architecture context available)
        if self.analyzed_architecture:
            layer_warnings = self._validate_layer_compliance(dev_plan)
            warnings.extend(layer_warnings)

        # Validate component references (skip for upgrade tasks — steps are framework-level)
        if "upgrade_plan" not in dev_plan:
            component_warnings = self._validate_component_references(dev_plan)
            warnings.extend(component_warnings)

        # Validate upgrade plan (if upgrade task)
        if "upgrade_plan" in dev_plan:
            upgrade_errors, upgrade_warnings = self._validate_upgrade_plan(dev_plan)
            errors.extend(upgrade_errors)
            warnings.extend(upgrade_warnings)

        # Determine if valid
        is_valid = len(errors) == 0 and len(missing_fields) == 0

        result = ValidationResult(
            is_valid=is_valid,
            missing_fields=missing_fields,
            warnings=warnings,
            errors=errors,
        )

        if is_valid:
            logger.info(f"[Stage5] Plan is valid (warnings: {len(warnings)})")
        else:
            logger.warning(
                f"[Stage5] Plan validation failed: {len(errors)} errors, {len(missing_fields)} missing fields"
            )

        return result

    def _validate_layer_compliance(self, dev_plan: dict) -> list[str]:
        """Check if changes follow architecture layer rules."""
        warnings = []

        arch_context = dev_plan.get("architecture_context", {})

        if "layer_compliance" not in arch_context:
            warnings.append("Layer compliance not checked")

        return warnings

    def _validate_component_references(self, dev_plan: dict) -> list[str]:
        """Validate that implementation steps reference actual components (soft check)."""
        warnings = []

        affected_components = dev_plan.get("affected_components", [])
        impl_steps = dev_plan.get("implementation_steps", [])

        if not affected_components:
            return warnings

        # Extract all identifiers: name, id, file_path stem (case-insensitive)
        identifiers: set[str] = set()
        for comp in affected_components:
            if isinstance(comp, dict):
                for key in ("name", "id", "file_path"):
                    val = comp.get(key, "")
                    if val:
                        identifiers.add(val.lower())
                        # Also add file stem for paths (e.g. "foo.component" from "src/app/foo.component.ts")
                        if "/" in val or "\\" in val:
                            from pathlib import PurePosixPath

                            identifiers.add(PurePosixPath(val).stem.lower())
            elif isinstance(comp, str):
                identifiers.add(comp.lower())
                if "/" in comp or "\\" in comp:
                    from pathlib import PurePosixPath

                    identifiers.add(PurePosixPath(comp).stem.lower())

        # Normalize steps to text and check if at least one identifier appears (case-insensitive)
        normalized_steps = []
        for step in impl_steps:
            if isinstance(step, str):
                normalized_steps.append(step)
            elif isinstance(step, dict):
                # Flatten common fields to string for matching
                parts = []
                for key in ("title", "description", "summary", "step"):
                    if step.get(key):
                        parts.append(str(step[key]))
                if not parts:
                    parts.append(str(step))
                normalized_steps.append(" ".join(parts))
            else:
                normalized_steps.append(str(step))

        steps_text = " ".join(normalized_steps).lower()
        mentioned = any(ident in steps_text for ident in identifiers if ident)

        if not mentioned and identifiers:
            warnings.append(
                "Implementation steps do not explicitly reference any affected components. "
                "Consider specifying which component to modify in each step."
            )

        return warnings

    @staticmethod
    def _validate_upgrade_plan(dev_plan: dict) -> tuple:
        """Validate upgrade-specific plan fields."""
        errors = []
        warnings = []

        upgrade_plan = dev_plan.get("upgrade_plan", {})

        migration_seq = upgrade_plan.get("migration_sequence", [])
        if not migration_seq:
            errors.append("Upgrade plan has no migration_sequence")
        else:
            for i, step in enumerate(migration_seq):
                if not step.get("migration_steps"):
                    warnings.append(f"Migration step {i + 1} ({step.get('title', '?')}) has no migration_steps")

        if not upgrade_plan.get("verification_commands"):
            warnings.append("Upgrade plan has no verification_commands")

        if not upgrade_plan.get("total_estimated_effort_hours"):
            warnings.append("Upgrade plan has no effort estimate")

        return errors, warnings
