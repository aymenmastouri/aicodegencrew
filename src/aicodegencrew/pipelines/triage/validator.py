"""TriageValidator — validates triage LLM output structure and content quality.

Checks structural integrity, content quality, and fact grounding before scoring.
Returns actionable feedback for retry if validation fails.
"""

import json
import logging
import re
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
class ValidationResult:
    """Aggregate validation result."""

    passed: bool
    checks: list[ValidationCheck] = field(default_factory=list)
    score: int = 100

    @property
    def issues(self) -> list[str]:
        return [c.message for c in self.checks if not c.passed]


class TriageValidator:
    """Validates triage LLM output against structural and content criteria.

    Runs before the scoring function to ensure the output meets minimum
    quality standards. Failed checks produce actionable feedback for retry.
    """

    def validate(self, result: dict[str, Any], context: dict[str, Any] | None = None) -> ValidationResult:
        """Run all validation checks on triage LLM output.

        Args:
            result: Parsed JSON from LLM with customer_summary and developer_context.
            context: Optional context with architecture facts for grounding.

        Returns:
            ValidationResult with pass/fail and actionable issues.
        """
        context = context or {}
        checks = [
            self._check_developer_context_structure(result),
            self._check_customer_summary_structure(result),
            self._check_big_picture_length(result),
            self._check_scope_boundaries_present(result),
            self._check_context_boundaries_count(result),
            self._check_no_action_steps_leaked(result),
            self._check_anticipated_questions(result),
            self._check_no_file_paths(result),
        ]

        # Optional fact-grounding check if architecture facts are available
        facts = context.get("architecture_facts") or context.get("facts")
        if facts:
            checks.append(self._check_source_facts_referenced(result, facts))

        passed = all(c.passed for c in checks)
        failed_count = sum(1 for c in checks if not c.passed)
        score = max(0, 100 - (failed_count * 12))

        result_obj = ValidationResult(passed=passed, checks=checks, score=score)

        if not passed:
            logger.warning(
                "[TriageValidator] FAILED (%d issues): %s",
                failed_count, result_obj.issues,
            )
        else:
            logger.info("[TriageValidator] PASSED all %d checks", len(checks))

        return result_obj

    def _check_developer_context_structure(self, result: dict) -> ValidationCheck:
        """Developer context must be a dict with required keys."""
        dev = result.get("developer_context")
        if not isinstance(dev, dict):
            return ValidationCheck(
                "developer_context_structure", False,
                "developer_context must be a JSON object with keys: big_picture, scope_boundary, "
                "context_boundaries, architecture_notes, anticipated_questions",
            )

        required_keys = {"big_picture", "scope_boundary", "context_boundaries", "anticipated_questions"}
        missing = required_keys - set(dev.keys())
        if missing:
            return ValidationCheck(
                "developer_context_structure", False,
                f"developer_context is missing required keys: {sorted(missing)}",
            )
        return ValidationCheck("developer_context_structure", True)

    def _check_customer_summary_structure(self, result: dict) -> ValidationCheck:
        """Customer summary must be a dict with required keys."""
        cust = result.get("customer_summary")
        if not isinstance(cust, dict):
            return ValidationCheck(
                "customer_summary_structure", False,
                "customer_summary must be a JSON object with keys: summary, impact_level, is_bug",
            )

        required_keys = {"summary", "impact_level"}
        missing = required_keys - set(cust.keys())
        if missing:
            return ValidationCheck(
                "customer_summary_structure", False,
                f"customer_summary is missing required keys: {sorted(missing)}",
            )
        return ValidationCheck("customer_summary_structure", True)

    def _check_big_picture_length(self, result: dict, min_chars: int = 80) -> ValidationCheck:
        """Big picture must have meaningful content (at least 80 chars)."""
        dev = result.get("developer_context", {})
        if not isinstance(dev, dict):
            return ValidationCheck("big_picture_length", False, "developer_context is not a dict")

        bp = dev.get("big_picture", "")
        if not isinstance(bp, str):
            bp = json.dumps(bp, ensure_ascii=False)
        if len(bp.strip()) < min_chars:
            return ValidationCheck(
                "big_picture_length", False,
                f"big_picture is too short ({len(bp.strip())} chars, minimum {min_chars}). "
                f"Explain: What is this project? Who uses it? What problem does this task solve? "
                f"Why is it needed now?",
            )
        return ValidationCheck("big_picture_length", True)

    def _check_scope_boundaries_present(self, result: dict) -> ValidationCheck:
        """Scope boundary must explicitly define IN and OUT scope."""
        dev = result.get("developer_context", {})
        if not isinstance(dev, dict):
            return ValidationCheck("scope_boundaries", False, "developer_context is not a dict")

        sb = dev.get("scope_boundary", "")
        if not isinstance(sb, str):
            sb = json.dumps(sb, ensure_ascii=False)
        sb_lower = sb.lower()

        has_in = any(kw in sb_lower for kw in ["in scope", "in-scope", "within scope", "includes"])
        has_out = any(kw in sb_lower for kw in ["out of scope", "out-of-scope", "excludes", "not in scope"])

        if not has_in and not has_out:
            return ValidationCheck(
                "scope_boundaries", False,
                "scope_boundary must explicitly mention what is IN scope and what is OUT of scope. "
                "Use phrases like 'In scope: ...' and 'Out of scope: ...'",
            )
        return ValidationCheck("scope_boundaries", True)

    def _check_context_boundaries_count(self, result: dict, min_count: int = 2) -> ValidationCheck:
        """Must have at least 2 context boundaries with analysis."""
        dev = result.get("developer_context", {})
        if not isinstance(dev, dict):
            return ValidationCheck("context_boundaries_count", False, "developer_context is not a dict")

        boundaries = dev.get("context_boundaries", [])
        if not isinstance(boundaries, list) or len(boundaries) < min_count:
            return ValidationCheck(
                "context_boundaries_count", False,
                f"context_boundaries must contain at least {min_count} entries "
                f"(found {len(boundaries) if isinstance(boundaries, list) else 0}). "
                f"Analyze relevant constraints: integration boundaries, technology constraints, "
                f"dependency risks, security boundaries.",
            )
        return ValidationCheck("context_boundaries_count", True)

    def _check_no_action_steps_leaked(self, result: dict) -> ValidationCheck:
        """Analytical fields must not contain imperative action steps."""
        dev = result.get("developer_context", {})
        if not isinstance(dev, dict):
            return ValidationCheck("no_action_steps", True)  # Can't check

        action_pattern = re.compile(
            r"(?:^|[.!?;]\s+|[-•*]\s+)"
            r"(implement|modify|change the|update the|add a|create a|fix the|remove the)\b",
            re.IGNORECASE,
        )

        check_fields = {
            "scope_boundary": dev.get("scope_boundary", ""),
            "architecture_notes": dev.get("architecture_notes", ""),
        }
        boundaries = dev.get("context_boundaries", [])
        if isinstance(boundaries, list):
            check_fields["context_boundaries"] = json.dumps(boundaries, ensure_ascii=False)

        leaked = []
        for field_name, text in check_fields.items():
            if not isinstance(text, str):
                text = json.dumps(text, ensure_ascii=False)
            matches = action_pattern.findall(text)
            for match in matches:
                leaked.append(f"'{match}' in {field_name}")

        if leaked:
            return ValidationCheck(
                "no_action_steps", False,
                f"Triage output must not contain action steps (that is the Plan phase's job). "
                f"Found: {leaked[:3]}. Replace with analytical observations.",
            )
        return ValidationCheck("no_action_steps", True)

    def _check_anticipated_questions(self, result: dict, min_count: int = 2) -> ValidationCheck:
        """Must have at least 2 anticipated questions."""
        dev = result.get("developer_context", {})
        if not isinstance(dev, dict):
            return ValidationCheck("anticipated_questions", False, "developer_context is not a dict")

        questions = dev.get("anticipated_questions", [])
        if not isinstance(questions, list) or len(questions) < min_count:
            return ValidationCheck(
                "anticipated_questions", False,
                f"anticipated_questions must contain at least {min_count} questions "
                f"(found {len(questions) if isinstance(questions, list) else 0}). "
                f"Think like a developer seeing this task for the first time.",
            )
        return ValidationCheck("anticipated_questions", True)

    def _check_no_file_paths(self, result: dict) -> ValidationCheck:
        """Developer context should not contain raw file paths."""
        dev = result.get("developer_context", {})
        if not isinstance(dev, dict):
            return ValidationCheck("no_file_paths", True)

        dev_text = json.dumps(dev, ensure_ascii=False)
        if re.search(r"[/\\]\w+\.\w{2,4}", dev_text):
            return ValidationCheck(
                "no_file_paths", False,
                "developer_context should not contain raw file paths. "
                "Reference components by name, not by file path.",
            )
        return ValidationCheck("no_file_paths", True)

    def _check_source_facts_referenced(self, result: dict, facts: dict) -> ValidationCheck:
        """Context boundaries should reference source facts from the architecture."""
        dev = result.get("developer_context", {})
        if not isinstance(dev, dict):
            return ValidationCheck("source_facts_referenced", True)

        boundaries = dev.get("context_boundaries", [])
        if not isinstance(boundaries, list):
            return ValidationCheck("source_facts_referenced", True)

        missing_sources = 0
        for boundary in boundaries:
            if isinstance(boundary, dict) and not boundary.get("source_facts"):
                missing_sources += 1

        if missing_sources > len(boundaries) // 2:
            return ValidationCheck(
                "source_facts_referenced", False,
                f"{missing_sources}/{len(boundaries)} context boundaries lack source_facts. "
                f"Every boundary should cite which extract data supports it "
                f"(e.g., 'tech_versions.json: LibX 6.4').",
            )
        return ValidationCheck("source_facts_referenced", True)
