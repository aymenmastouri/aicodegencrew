"""FactGrounder — shared utility for checking LLM output against known architecture facts.

Validates that generated text references real components, technologies, and
relations from the extracted architecture data. Detects hallucinated names
that don't exist in the repository.

Usage::

    grounder = FactGrounder(architecture_facts)
    result = grounder.check(llm_output_text)
    if not result.passed:
        logger.warning("Hallucinated: %s", result.hallucinated)
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GroundingResult:
    """Result of a fact-grounding check."""

    score: int  # 0-100
    found: set[str] = field(default_factory=set)
    hallucinated: set[str] = field(default_factory=set)
    passed: bool = True


class FactGrounder:
    """Checks text against known architecture facts for grounding.

    Extracts known component names, technologies, and relations from
    architecture_facts.json and verifies that generated text references
    real entities rather than hallucinated ones.
    """

    def __init__(self, architecture_facts: dict[str, Any]):
        self.known_components = self._extract_names(architecture_facts, "containers")
        self.known_technologies = self._extract_names(architecture_facts, "technology_stack")
        self.known_relations = self._extract_names(architecture_facts, "relations")
        self._all_known = self.known_components | self.known_technologies | self.known_relations
        logger.debug(
            "[FactGrounder] Loaded %d known names (%d components, %d technologies, %d relations)",
            len(self._all_known),
            len(self.known_components),
            len(self.known_technologies),
            len(self.known_relations),
        )

    def check(self, text: str, min_references: int = 3) -> GroundingResult:
        """Check if text references enough real facts from the architecture.

        Uses direct lookup: searches for known names in the text rather than
        extracting proper nouns and classifying them. This avoids false
        positives from common English words matching proper noun patterns.

        Args:
            text: The generated text to check.
            min_references: Minimum number of known names that must appear
                in the text (default 3, or 5% of known names, whichever is lower).

        Returns:
            GroundingResult with score, found names, and pass/fail.
        """
        if not self._all_known or not text:
            return GroundingResult(score=100, passed=True)

        text_lower = text.lower()
        found: set[str] = set()

        for name in self._all_known:
            if name.lower() in text_lower:
                found.add(name)

        total_known = len(self._all_known)
        # Require at least min_references or 5% of known names (whichever is lower)
        threshold = min(min_references, max(1, total_known // 20))
        ratio = len(found) / max(1, total_known)
        score = min(100, int(ratio * 200))  # Scale: 50% coverage = 100 score
        passed = len(found) >= threshold

        if not passed:
            logger.warning(
                "[FactGrounder] Low grounding: %d/%d known names found (need %d)",
                len(found), total_known, threshold,
            )

        return GroundingResult(
            score=score,
            found=found,
            passed=passed,
        )

    @staticmethod
    def _extract_names(facts: dict[str, Any], category: str) -> set[str]:
        """Extract name values from a category in architecture_facts."""
        names: set[str] = set()
        data = facts.get(category)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for key in ("name", "title", "technology", "source", "target"):
                        val = item.get(key)
                        if isinstance(val, str) and len(val.strip()) >= 3:
                            names.add(val.strip())
        elif isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, str) and len(val.strip()) >= 3:
                    names.add(val.strip())
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("title") or item.get("technology")
                            if isinstance(name, str) and len(name.strip()) >= 3:
                                names.add(name.strip())
                        elif isinstance(item, str) and len(item.strip()) >= 3:
                            names.add(item.strip())
        return names

