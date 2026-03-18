"""AnalysisReviewer — content review of the 16 analysis sections before synthesis.

Runs a single LLM call that receives all section outputs + original facts,
identifies gaps, contradictions, and weak analyses, and produces a structured
ReviewResult. Sections flagged for improvement are re-generated with specific
feedback injected into the prompt.

Usage (called internally by AnalysisPipeline)::

    reviewer = AnalysisReviewer(collector, generator)
    result = reviewer.review(section_outputs)
    # result.sections_to_redo = {"04": ["Missing circular dependency count ..."], ...}
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ...shared import LLMGenerator
from .data_collector import DataCollector

logger = logging.getLogger(__name__)

_MAX_SECTION_CHARS = 3000  # Per section in review prompt (keep total manageable)


@dataclass
class ReviewResult:
    """Result of the cross-section review."""

    quality_score: int  # 0-100
    sections_to_redo: dict[str, list[str]]  # section_id → list of specific issues
    gaps: list[str]  # Cross-cutting gaps (not tied to one section)
    contradictions: list[str]  # Contradictions between sections
    raw_review: str = ""  # Full LLM review output for logging


_REVIEW_SYSTEM = (
    "You are a JSON API. You receive architecture analysis sections and return "
    "a quality review as a single JSON object. No explanation, no markdown, no "
    "text before or after the JSON. Your response must start with { and end with }.\n\n"
    "Review criteria:\n"
    "1. GAPS — topics in source data but missing from analysis\n"
    "2. CONTRADICTIONS — conflicting statements between sections\n"
    "3. WEAK SECTIONS — vague reasoning or invented data\n"
    "4. NUMBER INCONSISTENCIES — different counts for the same metric"
)

_REVIEW_SCHEMA = """{
  "quality_score": <0-100>,
  "sections_to_redo": {
    "<section_id>": ["specific issue 1", "specific issue 2"]
  },
  "gaps": ["cross-cutting gap not tied to one section"],
  "contradictions": ["section X says A but section Y says B"],
  "summary": "2-3 sentence overall assessment"
}"""


class AnalysisReviewer:
    """Reviews all 16 analysis sections for quality before synthesis."""

    def __init__(
        self,
        collector: DataCollector,
        generator: LLMGenerator | None = None,
    ):
        self._collector = collector
        self._generator = generator or LLMGenerator()

    def review(self, section_outputs: dict[str, str]) -> ReviewResult:
        """Review all section outputs against source data.

        Args:
            section_outputs: Mapping of section_id (e.g. "01") to JSON content string.

        Returns:
            ReviewResult with quality score, sections to redo, gaps, contradictions.
        """
        if not section_outputs:
            logger.warning("[AnalysisReviewer] No sections to review")
            return ReviewResult(quality_score=0, sections_to_redo={}, gaps=[], contradictions=[])

        messages = self._build_review_prompt(section_outputs)
        logger.info("[AnalysisReviewer] Reviewing %d sections...", len(section_outputs))

        try:
            raw = self._generator.generate(messages)
            return self._parse_review(raw)
        except Exception as exc:
            logger.error("[AnalysisReviewer] Review LLM call failed: %s", exc, exc_info=True)
            # Non-fatal: pipeline continues without review
            return ReviewResult(
                quality_score=-1,
                sections_to_redo={},
                gaps=[],
                contradictions=[],
                raw_review=f"ERROR: {exc}",
            )

    def _build_review_prompt(self, section_outputs: dict[str, str]) -> list[dict]:
        """Build the review prompt with section outputs + source data summary."""
        # Format section outputs
        sections_text_parts: list[str] = []
        for sid in sorted(section_outputs.keys()):
            content = section_outputs[sid]
            truncated = content[:_MAX_SECTION_CHARS]
            if len(content) > _MAX_SECTION_CHARS:
                truncated += "\n... [truncated]"
            sections_text_parts.append(f"### Section {sid}\n```json\n{truncated}\n```")
        sections_text = "\n\n".join(sections_text_parts)

        # Source data summary for cross-referencing
        source_summary = self._build_source_summary()

        user_content = (
            "## Task: Review Architecture Analysis Sections\n\n"
            "Review the following 16 analysis sections for quality, completeness, and consistency.\n"
            "Compare them against the source data summary to find gaps.\n\n"
            f"## Review Schema\n```json\n{_REVIEW_SCHEMA}\n```\n\n"
            "## Review Instructions\n"
            "1. Check each section's reasoning — is it evidence-based or vague?\n"
            "2. Cross-check numbers (component counts, relation counts, endpoints) across sections\n"
            "3. Identify topics in the source data that NO section covers\n"
            "4. Find contradictions between sections\n"
            "5. Score quality 0-100:\n"
            "   - 90+: All sections well-grounded, consistent, no major gaps\n"
            "   - 70-89: Minor gaps or inconsistencies\n"
            "   - 50-69: Multiple sections need improvement\n"
            "   - <50: Fundamental issues requiring major rework\n"
            "6. Only flag sections_to_redo for sections scoring <70 quality\n"
            "7. Be specific in feedback — cite the exact data/numbers that are wrong or missing\n\n"
            f"## Source Data Summary\n{source_summary}\n\n"
            f"## Analysis Sections\n{sections_text}\n\n"
            "Output ONLY valid JSON. No markdown fences."
        )

        return [
            {"role": "system", "content": _REVIEW_SYSTEM},
            {"role": "user", "content": user_content},
        ]

    def _build_source_summary(self) -> str:
        """Build a compact summary of source data for cross-reference."""
        parts: list[str] = []

        stats = self._collector.get_statistics()
        if stats:
            parts.append(f"**Statistics:** {json.dumps(stats, ensure_ascii=False)}")

        containers = self._collector.get_containers()
        if containers:
            names = [c.get("name", "?") for c in containers[:20]]
            parts.append(f"**Containers ({len(containers)}):** {', '.join(names)}")

        interfaces = self._collector.get_interfaces(limit=30)
        if interfaces:
            parts.append(f"**Interfaces:** {len(interfaces)} endpoints")

        relations = self._collector.get_relations(limit=50)
        if relations:
            parts.append(f"**Relations:** {len(relations)} dependencies (capped at 50)")

        # Stereotypes breakdown
        if stats and "stereotypes" in stats:
            parts.append(f"**Stereotypes:** {json.dumps(stats['stereotypes'], ensure_ascii=False)}")

        return "\n".join(parts) if parts else "No source data summary available."

    @staticmethod
    def _extract_json(raw: str) -> dict | None:
        """Try to extract valid JSON from LLM output."""
        import re

        text = raw.strip()
        for prefix in ("```json", "```"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        last_brace = text.rfind("}")
        if last_brace > 0:
            try:
                return json.loads(text[: last_brace + 1])
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    def _parse_review(self, raw: str) -> ReviewResult:
        """Parse the LLM review output into a ReviewResult."""
        data = self._extract_json(raw)
        if data is None:
            logger.warning("[AnalysisReviewer] Could not parse review JSON, using raw output")
            return ReviewResult(
                quality_score=-1,
                sections_to_redo={},
                gaps=[],
                contradictions=[],
                raw_review=raw,
            )

        quality_score = data.get("quality_score", -1)
        sections_to_redo = data.get("sections_to_redo", {})
        gaps = data.get("gaps", [])
        contradictions = data.get("contradictions", [])

        # Ensure section IDs are zero-padded strings (strip "Section " prefix if LLM adds it)
        normalized: dict[str, list[str]] = {}
        for sid, issues in sections_to_redo.items():
            key = str(sid).strip()
            # Strip common LLM prefixes: "Section 04" → "04", "section_04" → "04"
            for prefix in ("Section ", "section ", "Section_", "section_"):
                if key.startswith(prefix):
                    key = key[len(prefix):]
                    break
            key = key.zfill(2)
            if isinstance(issues, list) and issues:
                normalized[key] = [str(i) for i in issues]
        sections_to_redo = normalized

        logger.info(
            "[AnalysisReviewer] Score=%d, redo=%d sections, gaps=%d, contradictions=%d",
            quality_score,
            len(sections_to_redo),
            len(gaps),
            len(contradictions),
        )

        return ReviewResult(
            quality_score=quality_score,
            sections_to_redo=sections_to_redo,
            gaps=gaps,
            contradictions=contradictions,
            raw_review=raw,
        )
