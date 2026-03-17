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

    # Phrases that indicate hallucination or placeholder content.
    # Note: "UNKNOWN" removed — the LLM legitimately uses it when data is
    # genuinely absent (e.g., "the deployment target is unknown based on
    # available evidence"). The remaining phrases catch actual hallucinations.
    BANNED_PHRASES = [
        "placeholder text",
        "placeholder content",
        "insert here",
        "fill in later",
        "TODO:",
        "TBD",
        "as an AI",
        "I cannot",
        "I don't have",
        "auto-generated as a stub",
        "information is not available",
        "would need to be",
        "could not be determined",
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
        # No max_length check — longer chapters are better than truncated ones.
        # The LLM output is bounded by MAX_LLM_OUTPUT_TOKENS (65536).
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
        # Strip code blocks before checking — TODO:/FIXME: in code citations are legitimate
        import re
        text_without_code = re.sub(r"```[\s\S]*?```", "", content)
        text_without_inline = re.sub(r"`[^`]+`", "", text_without_code)
        text_lower = text_without_inline.lower()

        found = [phrase for phrase in self.BANNED_PHRASES if phrase.lower() in text_lower]
        if found:
            return ValidationCheck(
                "banned_phrases",
                False,
                f"Remove placeholder/hallucination phrases: {found}. Replace with concrete data from the architecture.",
            )
        return ValidationCheck("banned_phrases", True)

    def _check_fact_grounding(self, content: str, data: dict[str, Any]) -> ValidationCheck:
        """Check that the content references real names from the architecture data.

        Collects names from all data sources (system, containers, components,
        interfaces, technologies) and checks case-insensitively. Short generic
        names (< 4 chars) are excluded to avoid false positives.
        """
        all_names: set[str] = set()

        # Extract names recursively from any data structure
        self._extract_names(data.get("facts", {}), all_names)
        self._extract_names(data.get("components", {}), all_names)
        self._extract_names(data.get("analyzed", {}), all_names)

        # Filter out names too short to be meaningful (e.g., "id", "db")
        all_names = {n for n in all_names if len(n) >= 3}

        if not all_names:
            return ValidationCheck("fact_grounding", True)

        # Case-insensitive matching
        content_lower = content.lower()
        found = sum(1 for name in all_names if name.lower() in content_lower)

        # Require at least 3 real names or 5% of known names (whichever is lower)
        min_required = min(3, max(1, len(all_names) // 20))
        if found < min_required:
            # Pick examples that are most likely to appear in this chapter type
            examples = sorted(all_names, key=lambda n: len(n), reverse=True)[:5]
            return ValidationCheck(
                "fact_grounding",
                False,
                f"Low fact grounding: only {found} known names referenced (need {min_required}). "
                f"Use real names from the data, e.g.: {examples}",
            )
        return ValidationCheck("fact_grounding", True)

    @staticmethod
    def _extract_names(data: Any, names: set[str], depth: int = 0) -> None:
        """Recursively extract 'name', 'title', 'technology' values from nested data."""
        if depth > 5:
            return
        name_keys = {"name", "title", "technology", "system_name", "architecture_style"}
        if isinstance(data, dict):
            for key, val in data.items():
                if key in name_keys and isinstance(val, str) and val.strip():
                    names.add(val.strip())
                elif isinstance(val, (dict, list)):
                    ChapterValidator._extract_names(val, names, depth + 1)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    ChapterValidator._extract_names(item, names, depth + 1)

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
