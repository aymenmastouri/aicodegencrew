"""DocumentReviewer — content review of generated chapters against source data.

After structural validation passes (length, heading, sections, banned phrases),
this reviewer performs a deeper content check via a second LLM call:

- Missing topics that the source data contains but the chapter ignores
- Unsupported claims not grounded in the architecture facts
- Internal contradictions within the chapter
- Weak sections with vague analysis instead of concrete evidence

Returns a ReviewResult with specific feedback for retry.

Usage (called internally by DocumentPipeline)::

    reviewer = DocumentReviewer()
    result = reviewer.review(content, recipe, data)
    if result.rewrite_needed:
        content = generator.retry_with_feedback_text(messages, content, result.feedback)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from ...shared import LLMGenerator
from .data_recipes import ChapterRecipe

logger = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 12000  # Chapter content in review prompt
_MAX_DATA_CHARS = 8000  # Source data in review prompt


@dataclass
class ReviewResult:
    """Result of a chapter content review."""

    quality_score: int  # 0-100
    rewrite_needed: bool
    missing_topics: list[str]
    unsupported_claims: list[str]
    contradictions: list[str]
    weak_sections: list[str]
    raw_review: str = ""

    @property
    def feedback(self) -> list[str]:
        """Compile all issues into a feedback list for retry."""
        items: list[str] = []
        for topic in self.missing_topics:
            items.append(f"Missing topic: {topic}")
        for claim in self.unsupported_claims:
            items.append(f"Unsupported claim: {claim}")
        for contradiction in self.contradictions:
            items.append(f"Contradiction: {contradiction}")
        for weak in self.weak_sections:
            items.append(f"Weak section: {weak}")
        return items


_REVIEW_SYSTEM = (
    "You are a senior architecture reviewer checking a generated documentation chapter "
    "for CONTENT QUALITY. You have access to the original source data.\n\n"
    "Your job is to find:\n"
    "1. MISSING TOPICS — important data in the source that the chapter doesn't cover\n"
    "2. UNSUPPORTED CLAIMS — statements in the chapter not backed by the source data\n"
    "3. CONTRADICTIONS — statements that conflict with the source data or within the chapter\n"
    "4. WEAK SECTIONS — paragraphs that use vague language instead of citing real "
    "component names, actual counts, or concrete evidence from the data\n\n"
    "Be specific. Cite the exact data that is missing or the exact claim that is wrong.\n"
    "Output ONLY valid JSON matching the exact schema. No markdown fences."
)

_REVIEW_SCHEMA = """{
  "quality_score": <0-100>,
  "rewrite_needed": true|false,
  "missing_topics": ["specific topic from source data not covered"],
  "unsupported_claims": ["exact claim in chapter + why it's unsupported"],
  "contradictions": ["exact contradiction + what source data says"],
  "weak_sections": ["section heading + what concrete data should replace vague language"],
  "summary": "1-2 sentence overall assessment"
}"""


class DocumentReviewer:
    """Reviews generated chapter content against source data."""

    def __init__(self, generator: LLMGenerator | None = None):
        self._generator = generator or LLMGenerator()

    def review(
        self,
        content: str,
        recipe: ChapterRecipe,
        data: dict[str, Any],
    ) -> ReviewResult:
        """Review chapter content against source data.

        Args:
            content: Generated markdown chapter content.
            recipe: Chapter recipe with title, sections, context hints.
            data: Collected architecture data (facts, RAG, components, analyzed).

        Returns:
            ReviewResult with quality score, issues, and rewrite decision.
        """
        messages = self._build_review_prompt(content, recipe, data)
        logger.info("[DocumentReviewer] Reviewing chapter %s — %s", recipe.id, recipe.title)

        try:
            raw = self._generator.generate(messages)
            return self._parse_review(raw, recipe.id)
        except Exception as exc:
            logger.error("[DocumentReviewer] Review failed for %s: %s", recipe.id, exc, exc_info=True)
            # Non-fatal: chapter proceeds without content review
            return ReviewResult(
                quality_score=-1,
                rewrite_needed=False,
                missing_topics=[],
                unsupported_claims=[],
                contradictions=[],
                weak_sections=[],
                raw_review=f"ERROR: {exc}",
            )

    def _build_review_prompt(
        self,
        content: str,
        recipe: ChapterRecipe,
        data: dict[str, Any],
    ) -> list[dict]:
        """Build the review prompt with chapter content + source data."""
        # Truncate chapter content
        content_text = content[:_MAX_CONTENT_CHARS]
        if len(content) > _MAX_CONTENT_CHARS:
            content_text += "\n... [truncated]"

        # Build source data summary
        source_summary = self._format_source_data(data)

        user_content = (
            f"## Task: Review Chapter '{recipe.title}' ({recipe.id})\n\n"
            f"## Review Schema\n```json\n{_REVIEW_SCHEMA}\n```\n\n"
            "## Review Instructions\n"
            f"This chapter should cover: {', '.join(recipe.sections) if recipe.sections else 'see context hint'}\n"
            f"Context hint: {recipe.context_hint[:500] if recipe.context_hint else 'none'}\n\n"
            "Check:\n"
            "1. Does the chapter use REAL component names, counts, and technologies from the source data?\n"
            "2. Are there important patterns/components in the source data that the chapter ignores?\n"
            "3. Does any claim contradict what the source data shows?\n"
            "4. Are there sections that say 'the system uses...' without citing which specific component?\n"
            "5. Score quality 0-100:\n"
            "   - 90+: Well-grounded, comprehensive, no significant gaps\n"
            "   - 70-89: Good but missing some data or has minor vague sections\n"
            "   - 50-69: Multiple gaps or unsupported claims\n"
            "   - <50: Major quality issues\n"
            "6. Set rewrite_needed=true only if score < 65\n\n"
            f"## Source Data\n{source_summary}\n\n"
            f"## Generated Chapter\n{content_text}\n\n"
            "Output ONLY valid JSON. No markdown fences."
        )

        return [
            {"role": "system", "content": _REVIEW_SYSTEM},
            {"role": "user", "content": user_content},
        ]

    def _format_source_data(self, data: dict[str, Any]) -> str:
        """Format source data compactly for the review prompt."""
        parts: list[str] = []

        # Facts summary
        facts = data.get("facts", {})
        if facts:
            facts_str = json.dumps(facts, indent=1, ensure_ascii=False, default=str)
            if len(facts_str) > _MAX_DATA_CHARS // 2:
                facts_str = facts_str[: _MAX_DATA_CHARS // 2] + "\n... [truncated]"
            parts.append(f"### Architecture Facts\n```json\n{facts_str}\n```")

        # Components summary
        components = data.get("components", {})
        if components:
            comp_lines: list[str] = []
            for stereotype, comp_list in components.items():
                if isinstance(comp_list, list):
                    names = [c.get("name", "?") if isinstance(c, dict) else str(c) for c in comp_list[:15]]
                    comp_lines.append(f"**{stereotype}** ({len(comp_list)}): {', '.join(names)}")
            if comp_lines:
                parts.append("### Components\n" + "\n".join(comp_lines))

        # Analyzed data summary
        analyzed = data.get("analyzed", {})
        if analyzed:
            analyzed_str = json.dumps(analyzed, indent=1, ensure_ascii=False, default=str)
            if len(analyzed_str) > _MAX_DATA_CHARS // 3:
                analyzed_str = analyzed_str[: _MAX_DATA_CHARS // 3] + "\n... [truncated]"
            parts.append(f"### Analysis Results\n```json\n{analyzed_str}\n```")

        # RAG results summary
        rag_results = data.get("rag_results", [])
        if rag_results:
            rag_lines: list[str] = []
            for rq in rag_results[:5]:
                if isinstance(rq, dict):
                    query = rq.get("query", "?")
                    results = rq.get("results", [])
                    rag_lines.append(f"- **{query}**: {len(results)} results")
            if rag_lines:
                parts.append("### RAG Evidence\n" + "\n".join(rag_lines))

        return "\n\n".join(parts) if parts else "No source data available."

    def _parse_review(self, raw: str, chapter_id: str) -> ReviewResult:
        """Parse the LLM review output into a ReviewResult."""
        text = raw.strip()
        for prefix in ("```json", "```"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        if text.endswith("```"):
            text = text[:-3].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("[DocumentReviewer] Could not parse review JSON for %s", chapter_id)
            return ReviewResult(
                quality_score=-1,
                rewrite_needed=False,
                missing_topics=[],
                unsupported_claims=[],
                contradictions=[],
                weak_sections=[],
                raw_review=raw,
            )

        quality_score = data.get("quality_score", -1)
        rewrite_needed = data.get("rewrite_needed", False)
        missing_topics = [str(t) for t in data.get("missing_topics", [])]
        unsupported_claims = [str(c) for c in data.get("unsupported_claims", [])]
        contradictions = [str(c) for c in data.get("contradictions", [])]
        weak_sections = [str(s) for s in data.get("weak_sections", [])]

        logger.info(
            "[DocumentReviewer] %s: score=%d, rewrite=%s, issues=%d",
            chapter_id,
            quality_score,
            rewrite_needed,
            len(missing_topics) + len(unsupported_claims) + len(contradictions) + len(weak_sections),
        )

        return ReviewResult(
            quality_score=quality_score,
            rewrite_needed=rewrite_needed,
            missing_topics=missing_topics,
            unsupported_claims=unsupported_claims,
            contradictions=contradictions,
            weak_sections=weak_sections,
            raw_review=raw,
        )
