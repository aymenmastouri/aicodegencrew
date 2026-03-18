"""TemplateBuilder — creates deterministic markdown skeletons for document chapters.

Generates a structured template from chapter recipes and collected data,
with deterministic fact tables and LLM enrichment placeholders.

The template-first approach reduces hallucination by:
1. Inserting verified facts as structured tables (deterministic)
2. Limiting LLM generation to enrichment placeholders (controlled scope)
3. Preserving structure guarantees regardless of LLM output quality

Usage::

    builder = TemplateBuilder()
    template = builder.build_chapter_template(recipe, collected_data)
    # Then: LLM fills only the <!-- LLM_ENRICH --> placeholders
"""

import logging
from typing import Any

from .data_recipes import ChapterRecipe

logger = logging.getLogger(__name__)


class TemplateBuilder:
    """Creates deterministic document templates from recipes and architecture data."""

    # Placeholder marker that the LLM should fill
    ENRICH_MARKER = "<!-- LLM_ENRICH"
    ENRICH_END = "-->"

    def build_chapter_template(self, recipe: ChapterRecipe, collected_data: dict[str, Any]) -> str:
        """Build a deterministic markdown skeleton with fact tables and LLM placeholders.

        Args:
            recipe: Chapter recipe defining structure and data requirements.
            collected_data: Data collected by DataCollector for this chapter.

        Returns:
            Markdown template string with fact tables and enrichment placeholders.
        """
        parts: list[str] = []

        # Chapter title
        parts.append(f"# {recipe.title}")
        parts.append("")

        # Required sections from the recipe
        if recipe.sections:
            for section in recipe.sections:
                parts.append(section)
                parts.append("")

                # Insert relevant fact tables for this section
                section_facts = self._get_facts_for_section(section, collected_data)
                if section_facts:
                    parts.append(section_facts)
                    parts.append("")

                # LLM enrichment placeholder
                section_id = section.replace("#", "").strip().split()[0] if section.strip() else "general"
                parts.append(f"{self.ENRICH_MARKER}: {section_id} {self.ENRICH_END}")
                parts.append(f"<!-- Context: Analyze the facts above and provide architectural insights for this section. -->")
                parts.append("")
        else:
            # No predefined sections — build from collected data
            facts = collected_data.get("facts", {})
            if facts:
                parts.append(self._format_facts_overview(facts))
                parts.append("")

            parts.append(f"{self.ENRICH_MARKER}: main {self.ENRICH_END}")
            parts.append(f"<!-- Context: {recipe.context_hint or 'Provide comprehensive analysis.'} -->")
            parts.append("")

        template = "\n".join(parts)
        logger.info(
            "[TemplateBuilder] Built template for %s: %d chars, %d sections",
            recipe.id, len(template), len(recipe.sections),
        )
        return template

    def _get_facts_for_section(self, section: str, data: dict[str, Any]) -> str:
        """Extract and format facts relevant to a specific section."""
        section_lower = section.lower()
        facts = data.get("facts", {})
        parts: list[str] = []

        # Match facts to sections by keyword
        if any(kw in section_lower for kw in ["overview", "introduction", "requirement"]):
            parts.extend(self._format_system_info(facts))
        elif any(kw in section_lower for kw in ["context", "scope", "boundary"]):
            parts.extend(self._format_interfaces(facts))
        elif any(kw in section_lower for kw in ["building block", "component", "container"]):
            parts.extend(self._format_containers(facts))
            parts.extend(self._format_components_table(data))
        elif any(kw in section_lower for kw in ["runtime", "scenario", "process"]):
            parts.extend(self._format_relations(facts))
        elif any(kw in section_lower for kw in ["deployment", "infrastructure"]):
            parts.extend(self._format_deployment_info(facts))
        elif any(kw in section_lower for kw in ["quality", "stakeholder", "goal"]):
            parts.extend(self._format_quality_attributes(facts))
        elif any(kw in section_lower for kw in ["technology", "technical", "decision"]):
            parts.extend(self._format_technology_stack(facts))
        elif any(kw in section_lower for kw in ["risk", "constraint"]):
            parts.extend(self._format_risks(facts))

        return "\n".join(parts) if parts else ""

    def _format_system_info(self, facts: dict) -> list[str]:
        """Format system-level info as a summary block."""
        lines: list[str] = []
        sys_name = facts.get("system_name") or facts.get("project_name", "")
        if sys_name:
            lines.append(f"**System:** {sys_name}")
        arch_style = facts.get("architecture_style", "")
        if arch_style:
            lines.append(f"**Architecture Style:** {arch_style}")
        return lines

    def _format_interfaces(self, facts: dict) -> list[str]:
        """Format interfaces as a markdown table."""
        interfaces = facts.get("interfaces", [])
        if not isinstance(interfaces, list) or not interfaces:
            return []

        lines = [
            "| Interface | Type | Direction | Description |",
            "|-----------|------|-----------|-------------|",
        ]
        for iface in interfaces[:20]:
            if isinstance(iface, dict):
                name = iface.get("name", "")
                itype = iface.get("type", "")
                direction = iface.get("direction", "")
                desc = iface.get("description", "")
                lines.append(f"| {name} | {itype} | {direction} | {desc} |")
        return lines

    def _format_containers(self, facts: dict) -> list[str]:
        """Format containers as a markdown table."""
        containers = facts.get("containers", [])
        if not isinstance(containers, list) or not containers:
            return []

        lines = [
            "| Container | Technology | Description |",
            "|-----------|-----------|-------------|",
        ]
        for container in containers[:30]:
            if isinstance(container, dict):
                name = container.get("name", "")
                tech = container.get("technology", "")
                desc = container.get("description", "")[:100]
                lines.append(f"| {name} | {tech} | {desc} |")
        return lines

    def _format_components_table(self, data: dict) -> list[str]:
        """Format component data as a table."""
        components = data.get("components", [])
        if not isinstance(components, list) or not components:
            return []

        lines = [
            "",
            "| Component | Stereotype | Layer |",
            "|-----------|-----------|-------|",
        ]
        for comp in components[:30]:
            if isinstance(comp, dict):
                name = comp.get("name", "")
                stereotype = comp.get("stereotype", "")
                layer = comp.get("layer", "")
                lines.append(f"| {name} | {stereotype} | {layer} |")
        return lines

    def _format_relations(self, facts: dict) -> list[str]:
        """Format relations as a markdown table."""
        relations = facts.get("relations", [])
        if not isinstance(relations, list) or not relations:
            return []

        lines = [
            "| Source | Target | Type | Description |",
            "|--------|--------|------|-------------|",
        ]
        for rel in relations[:20]:
            if isinstance(rel, dict):
                source = rel.get("source", "")
                target = rel.get("target", "")
                rtype = rel.get("type", "")
                desc = rel.get("description", "")[:80]
                lines.append(f"| {source} | {target} | {rtype} | {desc} |")
        return lines

    def _format_deployment_info(self, facts: dict) -> list[str]:
        """Format deployment-related facts."""
        tech = facts.get("technology_stack", {})
        if isinstance(tech, dict):
            infra = tech.get("infrastructure", []) or tech.get("deployment", [])
        elif isinstance(tech, list):
            infra = [t for t in tech if isinstance(t, dict) and t.get("category") in ("infrastructure", "deployment")]
        else:
            infra = []

        if not infra:
            return []

        lines = ["**Deployment Technologies:**"]
        for item in infra[:10]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('name', '')} {item.get('version', '')}".strip())
            elif isinstance(item, str):
                lines.append(f"- {item}")
        return lines

    def _format_quality_attributes(self, facts: dict) -> list[str]:
        """Format quality attributes if available."""
        quality = facts.get("quality_attributes", [])
        if not isinstance(quality, list) or not quality:
            return []

        lines = [
            "| Quality Goal | Priority | Description |",
            "|-------------|----------|-------------|",
        ]
        for attr in quality[:10]:
            if isinstance(attr, dict):
                name = attr.get("name", "")
                priority = attr.get("priority", "")
                desc = attr.get("description", "")[:80]
                lines.append(f"| {name} | {priority} | {desc} |")
        return lines

    def _format_technology_stack(self, facts: dict) -> list[str]:
        """Format technology stack as a table."""
        tech = facts.get("technology_stack", {})
        if not tech:
            return []

        lines = [
            "| Technology | Version | Category |",
            "|-----------|---------|----------|",
        ]
        if isinstance(tech, dict):
            for category, items in tech.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("name", "")
                            version = item.get("version", "")
                            lines.append(f"| {name} | {version} | {category} |")
        elif isinstance(tech, list):
            for item in tech[:30]:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    version = item.get("version", "")
                    cat = item.get("category", "")
                    lines.append(f"| {name} | {version} | {cat} |")
        return lines

    def _format_risks(self, facts: dict) -> list[str]:
        """Format risks/constraints if available."""
        risks = facts.get("risks", []) or facts.get("constraints", [])
        if not isinstance(risks, list) or not risks:
            return []

        lines = ["**Known Risks/Constraints:**"]
        for risk in risks[:10]:
            if isinstance(risk, dict):
                lines.append(f"- **{risk.get('name', 'Risk')}**: {risk.get('description', '')}")
            elif isinstance(risk, str):
                lines.append(f"- {risk}")
        return lines

    @staticmethod
    def _format_facts_overview(facts: dict) -> str:
        """Format a general overview of available facts."""
        parts: list[str] = []
        for key, value in facts.items():
            if isinstance(value, list):
                parts.append(f"- **{key}**: {len(value)} items")
            elif isinstance(value, dict):
                parts.append(f"- **{key}**: {len(value)} entries")
            elif isinstance(value, str) and value:
                parts.append(f"- **{key}**: {value[:100]}")
        return "\n".join(parts) if parts else ""


def has_unfilled_placeholders(content: str) -> list[str]:
    """Check if template still has unfilled LLM_ENRICH placeholders.

    Returns list of unfilled placeholder IDs.
    """
    import re
    return re.findall(r"<!-- LLM_ENRICH:\s*(\S+)\s*-->", content)


def check_fact_tables_intact(template: str, generated: str) -> list[str]:
    """Check that deterministic fact tables from the template survive in the generated output.

    Returns list of issues if tables were removed or corrupted.
    """
    issues: list[str] = []

    # Count markdown tables in template vs generated
    template_tables = template.count("|---|")
    generated_tables = generated.count("|---|")

    if template_tables > 0 and generated_tables < template_tables:
        issues.append(
            f"Fact tables were removed: template had {template_tables} tables, "
            f"generated has {generated_tables}. Preserve all data tables from the template."
        )

    return issues
