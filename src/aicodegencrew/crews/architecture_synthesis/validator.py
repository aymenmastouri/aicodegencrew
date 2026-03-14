"""ChapterValidator — validates LLM output before writing to disk.

Checks structure, length, fact grounding, banned phrases, and markdown quality.
Returns actionable feedback for retry if validation fails.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from .data_recipes import ChapterRecipe

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

    @property
    def issues(self) -> list[str]:
        return [c.message for c in self.checks if not c.passed]


class ChapterValidator:
    """Validates generated chapter content against quality criteria."""

    # Phrases that indicate hallucination or placeholder content
    BANNED_PHRASES = [
        "UNKNOWN",
        "placeholder",
        "TODO:",
        "TBD",
        "as an AI",
        "I cannot",
        "I don't have",
        "auto-generated as a stub",
        "information is not available",
        "would need to be",
        "could not be determined",
        "no evidence",
    ]

    def validate(self, content: str, recipe: ChapterRecipe, data: dict[str, Any]) -> ValidationResult:
        """Run all validation checks on generated content.

        Args:
            content: Generated markdown content.
            recipe: Chapter recipe with expected sections and bounds.
            data: Collected architecture data (for fact grounding check).

        Returns:
            ValidationResult with pass/fail and actionable issues.
        """
        checks = [
            self._check_not_empty(content),
            self._check_length(content, recipe),
            self._check_starts_with_heading(content, recipe),
            self._check_sections(content, recipe),
            self._check_banned_phrases(content),
            self._check_fact_grounding(content, data),
            self._check_no_code_fence_wrapper(content),
        ]

        passed = all(c.passed for c in checks)
        result = ValidationResult(passed=passed, checks=checks)

        if not passed:
            logger.warning(
                "[Validator] %s FAILED: %s",
                recipe.id,
                result.issues,
            )
        else:
            logger.info("[Validator] %s PASSED all checks", recipe.id)

        return result

    def _check_not_empty(self, content: str) -> ValidationCheck:
        if not content or not content.strip():
            return ValidationCheck("not_empty", False, "Content is empty")
        return ValidationCheck("not_empty", True)

    def _check_length(self, content: str, recipe: ChapterRecipe) -> ValidationCheck:
        length = len(content)
        if length < recipe.min_length:
            return ValidationCheck(
                "length",
                False,
                f"Content too short: {length} chars (minimum: {recipe.min_length}). Add more detail and analysis.",
            )
        if length > recipe.max_length:
            return ValidationCheck(
                "length",
                False,
                f"Content too long: {length} chars (maximum: {recipe.max_length}). Be more concise.",
            )
        return ValidationCheck("length", True)

    def _check_starts_with_heading(self, content: str, recipe: ChapterRecipe) -> ValidationCheck:
        stripped = content.strip()
        if not stripped.startswith("#"):
            return ValidationCheck(
                "heading",
                False,
                f"Content must start with a # heading (e.g., '# {recipe.title}')",
            )
        return ValidationCheck("heading", True)

    def _check_sections(self, content: str, recipe: ChapterRecipe) -> ValidationCheck:
        if not recipe.sections:
            return ValidationCheck("sections", True)

        missing = []
        for section in recipe.sections:
            # Flexible match: check if the section number and key words appear
            # "## 3.1 Business Context" → look for "3.1" AND "Business" or "Context"
            section_parts = section.replace("#", "").strip().split()
            if section_parts:
                # At minimum the section number must appear
                number = section_parts[0]
                if number not in content:
                    missing.append(section)

        if missing:
            return ValidationCheck(
                "sections",
                False,
                f"Missing sections: {missing}. Include all required sections.",
            )
        return ValidationCheck("sections", True)

    def _check_banned_phrases(self, content: str) -> ValidationCheck:
        content_lower = content.lower()
        found = [phrase for phrase in self.BANNED_PHRASES if phrase.lower() in content_lower]
        if found:
            return ValidationCheck(
                "banned_phrases",
                False,
                f"Remove placeholder/hallucination phrases: {found}. Replace with concrete data from the architecture.",
            )
        return ValidationCheck("banned_phrases", True)

    def _check_fact_grounding(self, content: str, data: dict[str, Any]) -> ValidationCheck:
        """Check that the content references real component names from the data."""
        # Collect all component names from the data
        all_names: set[str] = set()
        for _stereotype, comp_list in data.get("components", {}).items():
            for comp in comp_list:
                if isinstance(comp, dict) and comp.get("name"):
                    all_names.add(comp["name"])

        if not all_names:
            # No component data to ground against — skip check
            return ValidationCheck("fact_grounding", True)

        found = sum(1 for name in all_names if name in content)
        ratio = found / len(all_names)

        if ratio < 0.1:  # At least 10% of known components should be referenced
            return ValidationCheck(
                "fact_grounding",
                False,
                f"Low fact grounding: only {found}/{len(all_names)} ({ratio:.0%}) known components referenced. "
                f"Use real component names from the data, e.g.: {list(all_names)[:5]}",
            )
        return ValidationCheck("fact_grounding", True)

    def _check_no_code_fence_wrapper(self, content: str) -> ValidationCheck:
        """Check that the entire content is not wrapped in a code fence."""
        stripped = content.strip()
        if stripped.startswith("```") and stripped.endswith("```"):
            return ValidationCheck(
                "code_fence",
                False,
                "Content is wrapped in code fences. Output raw Markdown without wrapping.",
            )
        return ValidationCheck("code_fence", True)
