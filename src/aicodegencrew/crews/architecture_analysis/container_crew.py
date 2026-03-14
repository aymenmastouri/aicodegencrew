"""
Container Analysis Crew - Full LLM-based analysis for a single container.

This crew analyzes ONE container with 4 AI agents (same as ArchitectureAnalysisCrew):
1. Tech Architect: Patterns, layers, tech stack
2. Functional Analyst: Domain, capabilities, use cases
3. Quality Analyst: Coupling, cohesion, debt, risks
4. Synthesis Lead: Merges all into container analysis

Used by MapReduceAnalysisCrew for parallel container analysis.
Each container gets its own full analysis - results merged in REDUCE phase.
"""

import json
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool

from ...shared.utils.crew_callbacks import step_callback, task_callback
from ...shared.utils.embedder_config import get_crew_embedder
from ...shared.utils.llm_factory import create_llm
from ...shared.utils.logger import logger
from ...shared.utils.tool_guardrails import install_guardrails, uninstall_guardrails


class ContainerFactsTool(BaseTool):
    """Query facts for a specific container."""

    name: str = "container_facts"
    description: str = (
        "Get components, relations, interfaces for this container. Use this FIRST to understand the container."
    )

    container_facts: dict[str, Any] = {}

    def _run(self, query: str = "") -> str:
        """Return container facts summary."""
        comps = self.container_facts.get("components", [])
        rels = self.container_facts.get("relations", [])
        ifaces = self.container_facts.get("interfaces", [])

        # Build summary
        lines = [
            f"=== CONTAINER: {self.container_facts.get('container', 'unknown')} ===",
            f"Components: {len(comps)}",
            f"Relations: {len(rels)}",
            f"Interfaces: {len(ifaces)}",
            "",
            "== COMPONENTS BY STEREOTYPE ==",
        ]

        # Group by stereotype
        by_stereo: dict[str, list[str]] = {}
        for c in comps:
            stereo = c.get("stereotype", "unknown")
            name = c.get("name", "?")
            by_stereo.setdefault(stereo, []).append(name)

        for stereo, names in sorted(by_stereo.items()):
            lines.append(f"\n{stereo.upper()} ({len(names)}):")
            for n in names[:15]:
                lines.append(f"  - {n}")
            if len(names) > 15:
                lines.append(f"  ... and {len(names) - 15} more")

        # Show relations
        if rels:
            lines.append("\n== KEY RELATIONS ==")
            for r in rels[:15]:
                from_name = r.get("from", "?")
                to_name = r.get("to", "?")
                rel_type = r.get("type", "uses")
                lines.append(f"  {from_name} --{rel_type}--> {to_name}")
            if len(rels) > 15:
                lines.append(f"  ... and {len(rels) - 15} more")

        # Show interfaces
        if ifaces:
            lines.append("\n== INTERFACES ==")
            for i in ifaces[:15]:
                method = i.get("method", "?")
                path = i.get("endpoint", i.get("path", "?"))
                lines.append(f"  {method} {path}")
            if len(ifaces) > 15:
                lines.append(f"  ... and {len(ifaces) - 15} more")

        return "\n".join(lines)


class ContainerAnalysisCrew:
    """
    Full Crew for analyzing a single container with 4 LLM agents.

    Same structure as ArchitectureAnalysisCrew but focused on one container:
    1. Tech Architect - patterns, layers, technologies
    2. Functional Analyst - domain concepts, capabilities
    3. Quality Analyst - coupling, cohesion, debt
    4. Synthesis Lead - merges into container analysis
    """

    def __init__(
        self,
        container_name: str,
        container_facts: dict[str, Any],
        output_dir: Path,
    ):
        self.container_name = container_name
        self.container_facts = container_facts
        self.output_dir = Path(output_dir)

        # Tool with container-specific facts
        self._facts_tool = ContainerFactsTool()
        self._facts_tool.container_facts = container_facts

    def run(self) -> dict[str, Any]:
        """Run full 4-agent container analysis."""
        logger.info(f"[ContainerCrew] Analyzing: {self.container_name} with 4 agents")

        comp_count = len(self.container_facts.get("components", []))
        if comp_count == 0:
            logger.info(f"[ContainerCrew] {self.container_name}: No components, skipping")
            return self._empty_analysis()

        # === AGENT 1: Tech Architect ===
        tech_agent = Agent(
            role="Technical Architect",
            goal=f"Analyze technical architecture of container '{self.container_name}'",
            backstory="Expert in software architecture patterns and enterprise systems across any technology stack.",
            llm=create_llm(),
            tools=[self._facts_tool],
            verbose=False,
            allow_delegation=False,
            inject_date=True,
        )

        # === AGENT 2: Functional Analyst ===
        func_agent = Agent(
            role="Functional Analyst",
            goal=f"Analyze domain and capabilities of container '{self.container_name}'",
            backstory="Expert in domain-driven design, business capabilities, and functional decomposition.",
            llm=create_llm(),
            tools=[self._facts_tool],
            verbose=False,
            allow_delegation=False,
            inject_date=True,
        )

        # === AGENT 3: Quality Analyst ===
        quality_agent = Agent(
            role="Quality Analyst",
            goal=f"Assess architecture quality of container '{self.container_name}'",
            backstory="Expert in software quality, code metrics, technical debt, and architecture anti-patterns.",
            llm=create_llm(),
            tools=[self._facts_tool],
            verbose=False,
            allow_delegation=False,
            inject_date=True,
        )

        # === AGENT 4: Synthesis Lead ===
        synthesis_agent = Agent(
            role="Synthesis Lead",
            goal=f"Merge all analyses for container '{self.container_name}' into unified result",
            backstory="Senior architect who synthesizes technical, functional, and quality perspectives.",
            llm=create_llm(),
            verbose=False,
            allow_delegation=False,
            inject_date=True,
        )

        # === TASKS ===
        tech_task = Task(
            description=f"""Analyze technical architecture of container '{self.container_name}'.

Use container_facts tool to get components.

Determine:
1. Primary pattern (Layered, Hexagonal, Component-Based, MVC, etc.)
2. Layer structure (what layers exist and their responsibilities)
3. Key technologies and frameworks
4. Integration style (REST, Events, etc.)

Output as JSON:
{{
    "primary_pattern": "Layered|Hexagonal|Component-Based|...",
    "layers": ["Presentation", "Service", "Repository"],
    "technologies": ["<detected frameworks>", "..."],
    "integration_style": "REST API"
}}""",
            expected_output="JSON with pattern, layers, technologies",
            agent=tech_agent,
        )

        func_task = Task(
            description=f"""Analyze functional domain of container '{self.container_name}'.

Use container_facts tool to understand components.

Identify:
1. Main domain concepts (from entity/component names)
2. Key capabilities (what can this container do?)
3. Bounded context (what domain does it serve?)
4. External integrations

Output as JSON:
{{
    "domain_concepts": ["Workflow", "Document", "User"],
    "capabilities": ["Manage workflows", "Process documents"],
    "bounded_context": "Document Processing",
    "integrations": ["External API X", "Database Y"]
}}""",
            expected_output="JSON with domain analysis",
            agent=func_agent,
        )

        quality_task = Task(
            description=f"""Assess architecture quality of container '{self.container_name}'.

Use container_facts tool to analyze relationships.

Evaluate:
1. Separation of concerns (are layers properly separated?)
2. Coupling level (tight/moderate/loose)
3. Cohesion (are related things grouped together?)
4. Technical debt indicators
5. Overall grade (A/B/C/D)

Output as JSON:
{{
    "separation_of_concerns": "good|moderate|poor",
    "coupling": "loose|moderate|tight",
    "cohesion": "high|moderate|low",
    "debt_indicators": ["Large controllers", "Missing abstractions"],
    "grade": "A|B|C|D",
    "recommendations": ["Split large service", "Add interface layer"]
}}""",
            expected_output="JSON with quality assessment",
            agent=quality_agent,
        )

        synthesis_task = Task(
            description=f"""Synthesize all analyses for container '{self.container_name}'.

Combine the technical, functional, and quality analyses into one unified result.

Create final container analysis JSON:
{{
    "container": "{self.container_name}",
    "summary": "One paragraph executive summary",
    "technical": {{ ... from tech analysis ... }},
    "functional": {{ ... from func analysis ... }},
    "quality": {{ ... from quality analysis ... }},
    "overall_assessment": "Brief overall assessment",
    "top_recommendations": ["rec1", "rec2", "rec3"]
}}""",
            expected_output="Unified container analysis JSON",
            agent=synthesis_agent,
            context=[tech_task, func_task, quality_task],
        )

        # Run crew
        log_dir = self.output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crew = Crew(
            agents=[tech_agent, func_agent, quality_agent, synthesis_agent],
            tasks=[tech_task, func_task, quality_task, synthesis_task],
            process=Process.sequential,
            verbose=False,
            memory=False,
            max_rpm=30,
            step_callback=step_callback,
            task_callback=task_callback,
            output_log_file=str(log_dir / f"container_{self.container_name}.json"),
            embedder=get_crew_embedder(),
        )

        tracker = None
        try:
            from ...shared.utils.crew_timeout import kickoff_with_timeout
            tracker = install_guardrails()
            kickoff_with_timeout(crew)

            # Parse synthesis result
            synthesis_output = self._parse_json_output(synthesis_task.output.raw if synthesis_task.output else "{}")

            # Build final analysis
            analysis = {
                "container": self.container_name,
                "component_count": comp_count,
                "relation_count": len(self.container_facts.get("relations", [])),
                "interface_count": len(self.container_facts.get("interfaces", [])),
                "summary": synthesis_output.get("summary", f"Analysis of {self.container_name}"),
                "technical": synthesis_output.get(
                    "technical", self._parse_json_output(tech_task.output.raw if tech_task.output else "{}")
                ),
                "functional": synthesis_output.get(
                    "functional", self._parse_json_output(func_task.output.raw if func_task.output else "{}")
                ),
                "quality": synthesis_output.get(
                    "quality", self._parse_json_output(quality_task.output.raw if quality_task.output else "{}")
                ),
                "overall_assessment": synthesis_output.get("overall_assessment", ""),
                "top_recommendations": synthesis_output.get("top_recommendations", []),
                "analysis": {
                    "primary_pattern": synthesis_output.get("technical", {}).get("primary_pattern", "Unknown"),
                    "layers": synthesis_output.get("technical", {}).get("layers", []),
                    "stereotype_distribution": self._count_stereotypes(),
                    "total_components": comp_count,
                    "total_relations": len(self.container_facts.get("relations", [])),
                    "total_interfaces": len(self.container_facts.get("interfaces", [])),
                },
            }

            # Save result
            output_file = self.output_dir / f"container_{self.container_name}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)

            logger.info(f"[ContainerCrew] {self.container_name}: {comp_count} components analyzed by 4 agents")
            return analysis

        except Exception as e:
            logger.error(f"[ContainerCrew] {self.container_name} failed: {e}")
            return self._fallback_analysis()

        finally:
            uninstall_guardrails(tracker)

    def _empty_analysis(self) -> dict[str, Any]:
        """Return empty analysis for containers with no components."""
        return {
            "container": self.container_name,
            "component_count": 0,
            "relation_count": 0,
            "interface_count": 0,
            "summary": f"Container {self.container_name} has no analyzed components",
            "technical": {},
            "functional": {},
            "quality": {},
            "analysis": {
                "primary_pattern": "N/A",
                "layers": [],
                "stereotype_distribution": {},
                "total_components": 0,
                "total_relations": 0,
                "total_interfaces": 0,
            },
        }

    def _count_stereotypes(self) -> dict[str, int]:
        """Count components by stereotype."""
        counts: dict[str, int] = {}
        for c in self.container_facts.get("components", []):
            stereo = c.get("stereotype", "unknown")
            counts[stereo] = counts.get(stereo, 0) + 1
        return counts

    @staticmethod
    def _parse_json_output(text: str) -> dict[str, Any]:
        """Extract JSON from agent output using robust repair logic."""
        from .crew import ArchitectureAnalysisCrew

        try:
            return ArchitectureAnalysisCrew._extract_json_from_raw(text)
        except (ValueError, Exception):
            return {}

    def _fallback_analysis(self) -> dict[str, Any]:
        """Deterministic fallback if LLM fails."""
        stereotypes = self._count_stereotypes()
        comp_count = len(self.container_facts.get("components", []))

        # Detect pattern
        has_controllers = stereotypes.get("controller", 0) > 0
        has_services = stereotypes.get("service", 0) > 0
        has_repos = stereotypes.get("repository", 0) > 0
        has_components = stereotypes.get("component", 0) > 0

        if has_controllers and has_services and has_repos:
            pattern = "Layered"
            layers = ["Controller", "Service", "Repository"]
        elif has_components and has_services:
            pattern = "Component-Based"
            layers = ["Component", "Service", "Module"]
        elif has_services:
            pattern = "Service-Oriented"
            layers = ["Service"]
        else:
            pattern = "Unknown"
            layers = list(stereotypes.keys())[:3]

        return {
            "container": self.container_name,
            "component_count": comp_count,
            "relation_count": len(self.container_facts.get("relations", [])),
            "interface_count": len(self.container_facts.get("interfaces", [])),
            "summary": f"Fallback analysis for {self.container_name} ({comp_count} components)",
            "technical": {
                "primary_pattern": pattern,
                "layers": layers,
                "technologies": [],
                "integration_style": "Unknown",
            },
            "functional": {
                "domain_concepts": [],
                "capabilities": [],
                "bounded_context": "Unknown",
            },
            "quality": {
                "grade": "B",
                "coupling": "moderate",
                "cohesion": "moderate",
                "separation_of_concerns": "moderate",
            },
            "analysis": {
                "primary_pattern": pattern,
                "layers": layers,
                "stereotype_distribution": stereotypes,
                "total_components": comp_count,
                "total_relations": len(self.container_facts.get("relations", [])),
                "total_interfaces": len(self.container_facts.get("interfaces", [])),
            },
        }
