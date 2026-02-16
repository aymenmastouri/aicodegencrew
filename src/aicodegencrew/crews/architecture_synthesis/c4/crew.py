"""
C4 Crew - Phase 3a: Mini-Crews Pattern
=======================================
Creates all 4 C4 diagrams: Context, Container, Component, Deployment

Architecture Fix:
- OLD: 1 Crew with 26 sequential tasks -> Context overflow after task ~10-15
- NEW: 5 Mini-Crews (2-3 tasks each) -> Fresh context per level, no overflow

Each Mini-Crew starts with a fresh LLM context window.
Data is passed via template variables (summaries), not inter-task context.
"""

import logging

from crewai import Task

from ..base_crew import MiniCrewBase
from .agents import C4_AGENT_CONFIG
from .tasks import (
    COMPONENT_DIAGRAM_DESCRIPTION,
    COMPONENT_DOC_DESCRIPTION,
    CONTAINER_DIAGRAM_DESCRIPTION,
    CONTAINER_DOC_DESCRIPTION,
    CONTEXT_DIAGRAM_DESCRIPTION,
    CONTEXT_DOC_DESCRIPTION,
    DEPLOYMENT_DIAGRAM_DESCRIPTION,
    DEPLOYMENT_DOC_DESCRIPTION,
    QUALITY_GATE_DESCRIPTION,
)

logger = logging.getLogger(__name__)


class C4Crew(MiniCrewBase):
    """
    C4 Crew - Creates all 4 C4 Model views using Mini-Crews pattern.

    Each C4 level runs in its own Mini-Crew with fresh LLM context.
    This prevents context overflow that occurred with 26 tasks in 1 Crew.

    Mini-Crews:
    1. Context Crew (2 tasks: doc + diagram)
    2. Container Crew (2 tasks: doc + diagram)
    3. Component Crew (2 tasks: doc + diagram)
    4. Deployment Crew (2 tasks: doc + diagram)
    5. Quality Crew (1 task: quality gate)
    """

    @property
    def crew_name(self) -> str:
        return "C4"

    @property
    def agent_config(self) -> dict[str, str]:
        return C4_AGENT_CONFIG

    def _summarize_facts(self) -> dict[str, str]:
        """Create evidence-first summaries for C4 diagram generation."""
        facts = self.facts
        analysis = self.analysis

        system_info = facts.get("system", {})
        system_name = system_info.get("name", "Unknown System")

        arch_info = analysis.get("architecture", {})
        macro_arch = analysis.get("macro_architecture", {})
        micro_arch = analysis.get("micro_architecture", {})

        # Support both legacy Phase 2 output (`architecture`/`patterns`) and the current
        # MapReduceAnalysisCrew output (`macro_architecture`/`micro_architecture`).
        style_name = arch_info.get("primary_style") or macro_arch.get("style") or "UNKNOWN"

        layers = arch_info.get("layers") or []
        if not layers and isinstance(micro_arch, dict):
            derived_layers: list[str] = []
            seen_layers: set[str] = set()
            for container_info in micro_arch.values():
                for layer in (container_info or {}).get("layer_structure", []) or []:
                    if layer not in seen_layers:
                        seen_layers.add(layer)
                        derived_layers.append(layer)
            layers = derived_layers

        patterns = analysis.get("patterns", []) or []
        if not patterns and isinstance(micro_arch, dict):
            derived_patterns: list[str] = []
            seen_patterns: set[str] = set()
            for container_info in micro_arch.values():
                pattern = (container_info or {}).get("primary_pattern")
                if pattern and pattern != "Unknown" and pattern not in seen_patterns:
                    seen_patterns.add(pattern)
                    derived_patterns.append(pattern)
            patterns = derived_patterns

        containers = facts.get("containers", [])
        components = facts.get("components", [])
        interfaces = facts.get("interfaces", [])
        relations = facts.get("relations", [])

        # System summary
        tech_stack = sorted({c.get("technology", "Unknown") for c in containers if c.get("technology")})
        container_list_lines = []
        for c in containers:
            cid = c.get("id", "?")
            cname = c.get("name", "?")
            ctype = c.get("type", "UNKNOWN")
            ctech = c.get("technology", "UNKNOWN")
            container_list_lines.append(f"- {cid}: {cname} | type={ctype} | tech={ctech}")

        system_summary = f"""SYSTEM: {system_name}
DOMAIN: {system_info.get("domain", "UNKNOWN")}
ARCHITECTURE STYLE: {style_name}
LAYERS: {", ".join(layers) if layers else "UNKNOWN"}
PATTERNS: {", ".join(str(p) for p in patterns) if patterns else "UNKNOWN"}

STATISTICS:
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGY: {", ".join(tech_stack) if tech_stack else "UNKNOWN"}

CONTAINERS:
{chr(10).join(container_list_lines) if container_list_lines else "- NONE"}"""

        # Container details
        container_details = []
        for c in containers:
            container_details.append(
                f"CONTAINER: {c.get('name', '?')} (id={c.get('id', '?')})\n"
                f"  Type: {c.get('type', 'UNKNOWN')}\n"
                f"  Technology: {c.get('technology', 'UNKNOWN')}\n"
                f"  Root Path: {c.get('root_path', 'UNKNOWN')}"
            )

        containers_summary = f"""CONTAINER DETAILS
Total: {len(containers)} containers

{"".join(container_details)}"""

        # Component statistics
        by_stereotype: dict[str, list] = {}
        for comp in components:
            stereo = comp.get("stereotype", "component")
            if stereo not in by_stereotype:
                by_stereotype[stereo] = []
            by_stereotype[stereo].append(comp.get("name", "?"))

        component_sections = []
        for stereo, names in sorted(by_stereotype.items()):
            component_sections.append(
                f"{stereo.upper()}: {len(names)} components "
                f"(examples: {', '.join(names[:5])}{'...' if len(names) > 5 else ''})"
            )

        components_summary = f"""COMPONENT ANALYSIS
Total: {len(components)} components

{chr(10).join(component_sections) if component_sections else "UNKNOWN"}"""

        # Interface summary
        by_method: dict[str, int] = {}
        for iface in interfaces:
            method = iface.get("method", "GET")
            by_method[method] = by_method.get(method, 0) + 1

        interfaces_summary = f"""REST API: {len(interfaces)} endpoints
By method: {", ".join(f"{m}:{c}" for m, c in sorted(by_method.items()))}"""

        # Relations summary
        rel_by_type: dict[str, int] = {}
        for rel in relations:
            rtype = rel.get("type", "unknown")
            rel_by_type[rtype] = rel_by_type.get(rtype, 0) + 1

        relations_summary = f"""DEPENDENCIES: {len(relations)} relations
By type: {", ".join(f"{t}:{c}" for t, c in sorted(rel_by_type.items()))}"""

        return {
            "system_summary": self.escape_braces(system_summary),
            "containers_summary": self.escape_braces(containers_summary),
            "components_summary": self.escape_braces(components_summary),
            "relations_summary": self.escape_braces(relations_summary),
            "interfaces_summary": self.escape_braces(interfaces_summary),
        }

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def run(self) -> str:
        """
        Execute all 5 Mini-Crews sequentially with resume support.

        On failure, completed mini-crews are checkpointed. Re-running
        skips already-completed mini-crews automatically.
        """
        completed = self._load_checkpoint()
        results = []

        mini_crews = [
            (
                "context",
                CONTEXT_DOC_DESCRIPTION,
                "Complete C4 Context document (6-8 pages)",
                CONTEXT_DIAGRAM_DESCRIPTION,
                "C4 Context DrawIO diagram created",
                ["c4/c4-context.md", "c4/c4-context.drawio"],
            ),
            (
                "container",
                CONTAINER_DOC_DESCRIPTION,
                "Complete C4 Container document (6-8 pages)",
                CONTAINER_DIAGRAM_DESCRIPTION,
                "C4 Container DrawIO diagram created",
                ["c4/c4-container.md", "c4/c4-container.drawio"],
            ),
            (
                "component",
                COMPONENT_DOC_DESCRIPTION,
                "Complete C4 Component document (6-8 pages)",
                COMPONENT_DIAGRAM_DESCRIPTION,
                "C4 Component DrawIO diagram created",
                ["c4/c4-component.md", "c4/c4-component.drawio"],
            ),
            (
                "deployment",
                DEPLOYMENT_DOC_DESCRIPTION,
                "Complete C4 Deployment document (4-6 pages)",
                DEPLOYMENT_DIAGRAM_DESCRIPTION,
                "C4 Deployment DrawIO diagram created",
                ["c4/c4-deployment.md", "c4/c4-deployment.drawio"],
            ),
        ]

        # Get template data for filling {system_summary} placeholders
        template_data = self._summarize_facts()

        for name, doc_desc, doc_output, diag_desc, diag_output, expected_files in mini_crews:
            if not self.should_skip(name, completed):
                try:
                    agent = self._create_agent()
                    self._run_mini_crew(
                        name,
                        [
                            Task(description=doc_desc.format(**template_data), expected_output=doc_output, agent=agent),
                            Task(
                                description=diag_desc.format(**template_data), expected_output=diag_output, agent=agent
                            ),
                        ],
                        expected_files=expected_files,
                    )
                except Exception as e:
                    logger.error(f"[C4] Mini-crew {name} failed, continuing: {e}")
            results.append(f"{name.title()}: Done")

        # Quality Gate
        if not self.should_skip("quality", completed):
            try:
                agent = self._create_agent()
                self._run_mini_crew(
                    "quality",
                    [
                        Task(
                            description=QUALITY_GATE_DESCRIPTION,
                            expected_output="C4 Quality report written to quality/c4-report.md",
                            agent=agent,
                        ),
                    ],
                )
            except Exception as e:
                logger.error(f"[C4] Quality gate failed, continuing: {e}")
        results.append("Quality Gate: Done")

        self._clear_checkpoint()
        summary = "\n".join(results)
        logger.info(f"[C4] All Mini-Crews completed:\n{summary}")
        return summary
