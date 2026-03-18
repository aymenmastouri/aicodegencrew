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
import re
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

    def check(self, text: str, min_ratio: float = 0.05) -> GroundingResult:
        """Check if text references enough real facts from the architecture.

        Args:
            text: The generated text to check.
            min_ratio: Minimum ratio of found / (found + hallucinated) names
                to pass (default 5%).

        Returns:
            GroundingResult with score, found/hallucinated sets, and pass/fail.
        """
        if not self._all_known or not text:
            return GroundingResult(score=100, passed=True)

        proper_nouns = self._extract_proper_nouns(text)
        if not proper_nouns:
            return GroundingResult(score=100, passed=True)

        found: set[str] = set()
        hallucinated: set[str] = set()
        all_known_lower = {n.lower() for n in self._all_known}

        for noun in proper_nouns:
            if noun.lower() in all_known_lower:
                found.add(noun)
            else:
                hallucinated.add(noun)

        total = len(found) + len(hallucinated)
        ratio = len(found) / max(1, total)
        score = int(ratio * 100)
        passed = ratio >= min_ratio

        if not passed:
            logger.warning(
                "[FactGrounder] Low grounding: %d/%d names found (score=%d, threshold=%.0f%%)",
                len(found), total, score, min_ratio * 100,
            )
        if hallucinated:
            logger.debug("[FactGrounder] Potentially hallucinated: %s", sorted(hallucinated)[:10])

        return GroundingResult(
            score=score,
            found=found,
            hallucinated=hallucinated,
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

    @staticmethod
    def _extract_proper_nouns(text: str) -> set[str]:
        """Extract likely proper nouns / technical names from text.

        Matches CamelCase words, capitalized multi-word names, and
        technical identifiers (with dots, hyphens, underscores).
        Filters out common English words and very short names.
        """
        _COMMON_WORDS = {
            "the", "this", "that", "with", "from", "into", "for", "and", "but",
            "not", "are", "was", "were", "been", "being", "have", "has", "had",
            "does", "did", "will", "would", "could", "should", "may", "might",
            "can", "shall", "must", "need", "each", "every", "all", "any",
            "both", "few", "more", "most", "other", "some", "such", "than",
            "too", "very", "just", "also", "only", "own", "same", "how",
            "what", "which", "who", "whom", "when", "where", "why",
            "note", "see", "use", "used", "using", "based", "like",
            "before", "after", "between", "through", "during", "about",
            "json", "yaml", "xml", "html", "http", "https", "api",
            "true", "false", "null", "none", "yes", "steps", "step",
            "example", "section", "chapter", "table", "figure", "list",
        }

        # Match CamelCase, PascalCase, UPPER_CASE, and dotted names (e.g. Spring.Boot)
        patterns = [
            r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b",  # CamelCase: ServiceBus, DataStore
            r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b",  # Multi-word: Spring Boot
            r"\b[A-Z][a-z]{2,}[.-][A-Za-z]{2,}\b",  # Dotted: Spring.Boot, Vue.js
            r"\b[a-z]+[-_][a-z]+[-_]?[a-z]*\b",  # kebab/snake: vue-router, my_service
        ]

        found: set[str] = set()
        for pattern in patterns:
            for match in re.findall(pattern, text):
                clean = match.strip()
                if len(clean) >= 3 and clean.lower() not in _COMMON_WORDS:
                    found.add(clean)

        return found
