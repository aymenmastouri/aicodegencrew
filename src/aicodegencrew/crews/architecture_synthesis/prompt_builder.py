"""PromptBuilder — constructs structured prompts for chapter generation.

Uses XML tags (Claude best practice), Chain-of-Thought, and Few-Shot examples
to produce high-quality architecture documentation in a single LLM call.
"""

import json
import logging
from typing import Any

from .data_recipes import ChapterRecipe

logger = logging.getLogger(__name__)

# Maximum chars of data to include in prompt (prevent context overflow)
_MAX_FACTS_CHARS = 40000
_MAX_RAG_CHARS = 15000
_MAX_COMPONENTS_CHARS = 20000


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text with indicator."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def _format_facts(facts: dict[str, Any]) -> str:
    """Format collected facts as structured text for the prompt."""
    parts = []
    for category, data in facts.items():
        if not data:
            continue
        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        parts.append(f"### {category}\n```json\n{json_str}\n```")
    return _truncate("\n\n".join(parts), _MAX_FACTS_CHARS)


def _format_rag_results(rag_results: list[dict]) -> str:
    """Format RAG search results as structured text."""
    if not rag_results:
        return "No code evidence available."

    parts = []
    for entry in rag_results:
        query = entry.get("query", "")
        results = entry.get("results", [])
        if not results:
            parts.append(f"### Query: \"{query}\"\nNo results found.")
            continue

        lines = [f"### Query: \"{query}\""]
        for r in results[:5]:  # Max 5 results per query
            fp = r.get("file_path", "unknown")
            score = r.get("relevance_score", 0)
            content = r.get("content", "")[:500]
            lines.append(f"**{fp}** (relevance: {score})\n```\n{content}\n```")
        parts.append("\n".join(lines))

    return _truncate("\n\n".join(parts), _MAX_RAG_CHARS)


def _format_components(components: dict[str, list]) -> str:
    """Format component lists as tables."""
    if not components:
        return "No component data available."

    parts = []
    for stereotype, comp_list in components.items():
        if not comp_list:
            continue
        lines = [f"### {stereotype} ({len(comp_list)} total)"]
        lines.append("| Name | Module | Layer | File |")
        lines.append("|------|--------|-------|------|")
        for c in comp_list[:30]:
            name = c.get("name", "?")
            module = c.get("module", "")
            layer = c.get("layer", "")
            fp = c.get("file_path", "")
            lines.append(f"| {name} | {module} | {layer} | {fp} |")
        if len(comp_list) > 30:
            lines.append(f"| ... | ({len(comp_list) - 30} more) | | |")
        parts.append("\n".join(lines))

    return _truncate("\n\n".join(parts), _MAX_COMPONENTS_CHARS)


class PromptBuilder:
    """Builds structured prompts for architecture documentation generation."""

    def build(self, recipe: ChapterRecipe, data: dict[str, Any]) -> list[dict[str, str]]:
        """Build a chat-format prompt (system + user messages).

        Returns:
            List of message dicts: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        system_msg = self._build_system_message()
        user_msg = self._build_user_message(recipe, data)
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

    def _build_system_message(self) -> str:
        return (
            "You are a senior software architect writing professional architecture documentation. "
            "You write in the same language as the input data (German if the data is German, English if English). "
            "You are specific, precise, and always reference real component names, patterns, and technologies "
            "from the provided data. You never invent components or patterns that are not in the data. "
            "You add interpretation and analysis: not just WHAT exists, but WHY it matters and what it means "
            "for maintainability, scalability, and quality. "
            "You use Mermaid diagrams for architecture flows where appropriate."
        )

    def _build_user_message(self, recipe: ChapterRecipe, data: dict[str, Any]) -> str:
        """Build the user message with structured sections."""
        system_summary = data.get("system_summary", "")
        facts_text = _format_facts(data.get("facts", {}))
        rag_text = _format_rag_results(data.get("rag_results", []))
        components_text = _format_components(data.get("components", {}))

        # Build expected sections list
        sections_list = "\n".join(f"- {s}" for s in recipe.sections)

        prompt = f"""<task>
Write arc42/C4 chapter: **{recipe.title}**

Output file: {recipe.output_file}
</task>

<instructions>
Think step by step before writing:

1. ANALYZE: Study the architecture data below. Identify the key patterns, technologies, and architectural decisions.
2. INTERPRET: Think about what these choices mean for the system's quality attributes (maintainability, performance, security, reliability).
3. CONNECT: Find relationships between components, identify risks, and note architectural strengths and weaknesses.
4. WRITE: Produce the complete chapter in Markdown with the required sections.

Quality criteria:
- Every claim MUST reference a real component, pattern, or technology from the data
- Include tables for inventories (components, interfaces, decisions)
- Add interpretation and analysis — not just listing facts
- Use Mermaid diagrams (```mermaid) for flows and relationships where helpful
- Minimum {recipe.min_length} characters, maximum {recipe.max_length} characters
- Start with: # {recipe.title}

Required sections:
{sections_list}
</instructions>

<context>
System summary: {system_summary}

{recipe.context_hint}
</context>

<architecture_facts>
{facts_text}
</architecture_facts>

<code_evidence>
{rag_text}
</code_evidence>

<component_inventory>
{components_text}
</component_inventory>

<output_format>
Write the complete chapter in Markdown. Include all required sections.
Do NOT wrap the output in code fences — write raw Markdown directly.
Do NOT include any preamble or explanation — start directly with the # heading.
</output_format>"""

        return prompt
