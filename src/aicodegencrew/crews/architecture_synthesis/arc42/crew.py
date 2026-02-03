"""
Arc42 Crew - Phase 2 Subcrew
=============================
Erstellt alle 12 arc42 Kapitel + Quality Gate

CrewAI Best Practices Applied:
- Strategy 2: Building Blocks split into 4 sub-tasks (Controllers, Services, Entities, Repositories)
- Strategy 3: Hierarchical task dependencies with context
- Strategy 6: FactsQueryTool for RAG-based facts retrieval
- Strategy 7: ChunkedWriterTool for large document generation
"""
import json
import os
from pathlib import Path
from typing import List

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, llm, task, tool
from crewai.agents.agent_builder.base_agent import BaseAgent
# Use our safe FileReadTool instead of crewai_tools.FileReadTool (prevents token overflow)
from crewai_tools import DirectoryReadTool

from ..tools import (
    DrawioDiagramTool, 
    DocWriterTool,
    FactsQueryTool,
    ChunkedWriterTool,
    StereotypeListTool,
    FileReadTool,  # Safe version with size limits
)


@CrewBase
class Arc42Crew:
    """
    Arc42 Crew - Creates all 12 arc42 chapters.
    """
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    agents: List[BaseAgent]
    tasks: List[Task]
    
    def __init__(self, facts_path: str = "knowledge/architecture/architecture_facts.json"):
        """Initialize crew with architecture facts."""
        self.facts_path = Path(facts_path)
        self.facts = self._load_facts()
        self.evidence_map = self._load_evidence_map()
        self.summaries = self._summarize_facts()
    
    def _load_facts(self) -> dict:
        """Load architecture facts from JSON file."""
        if self.facts_path.exists():
            with open(self.facts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_evidence_map(self) -> dict:
        """Load evidence map (Phase 1 output) if available."""
        evidence_path = self.facts_path.parent / "evidence_map.json"
        if evidence_path.exists():
            try:
                with open(evidence_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _summarize_facts(self) -> dict[str, str]:
        """Create compact, evidence-first summaries for arc42.

                IMPORTANT:
                - Arc42 chapters are large; injecting huge lists can exceed model context.
                - Provide only high-signal facts here and instruct the agent to use tools
                    (query_architecture_facts / stereotype_list_tool / file_read_tool)
                    to pull details on demand.
                - Phase 2 must not invent anything not present in Phase 1 facts/evidence.
        """
        facts = self.facts
        evidence_map = self.evidence_map or {}

        system_info = facts.get("system", {})
        system_name = system_info.get("name", "Unknown System")

        style = facts.get("architecture_style", {})
        style_name = style.get("primary_style", "Layered Architecture")
        layers = style.get("layers", ["controller", "service", "repository", "entity"])
        patterns = style.get("patterns", [])

        containers = facts.get("containers", [])
        components = facts.get("components", [])
        interfaces = facts.get("interfaces", [])
        relations = facts.get("relations", [])

        def summarize_evidence_ids(evidence_ids: list[str] | None, max_items: int = 3) -> str:
            if not evidence_ids:
                return "[]"
            ids = evidence_ids[:max_items]
            return "[" + ", ".join(ids) + ("]" if len(evidence_ids) <= max_items else f", ... +{len(evidence_ids) - max_items}]")
        
        # =====================================================================
        # DETAILED SYSTEM SUMMARY
        # =====================================================================
        tech_stack = sorted({c.get("technology", "Unknown") for c in containers if c.get("technology")})

        system_summary = f"""SYSTEM ANALYSIS FOR: {system_name}

ARCHITECTURE STYLE: {style_name}
DETECTED LAYERS: {', '.join(layers) if layers else 'controller, service, repository, entity'}
DETECTED PATTERNS: {', '.join(patterns) if patterns else 'Repository, Factory, Layered'}

STATISTICS:
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGY (from containers):
{chr(10).join([f'- {t}' for t in tech_stack]) if tech_stack else '- UNKNOWN'}

NOTE:
- Do not assume messaging/ports/runtime unless backed by evidence."""

        # =====================================================================
        # CONTAINERS (compact)
        # =====================================================================
        container_lines: list[str] = []
        for c in containers:
            cid = c.get("id", "?")
            name = c.get("name", "?")
            ctype = c.get("type", "UNKNOWN")
            tech = c.get("technology", "UNKNOWN")
            root_path = c.get("root_path", "UNKNOWN")
            ev_ids = c.get("evidence", [])
            container_lines.append(
                f"- {cid}: {name} | type={ctype} | tech={tech} | root={root_path} | evidence={summarize_evidence_ids(ev_ids)}"
            )

        containers_summary = f"""CONTAINER ANALYSIS (from facts)
Total Containers: {len(containers)}

{chr(10).join(container_lines) if container_lines else '- NONE'}

NOTE:
- For details, read evidence_map.json for the referenced evidence IDs."""

        # =====================================================================
        # COMPONENTS (counts only to avoid context overflow)
        # =====================================================================
        by_stereotype_count: dict[str, int] = {}
        for comp in components:
            stereo = comp.get("stereotype", "component")
            by_stereotype_count[stereo] = by_stereotype_count.get(stereo, 0) + 1

        stereo_lines = [f"- {k}: {v}" for k, v in sorted(by_stereotype_count.items())]

        components_summary = f"""COMPONENT ANALYSIS (from facts)
Total Components: {len(components)}

Counts by stereotype:
{chr(10).join(stereo_lines) if stereo_lines else '- NONE'}

NOTE:
- Do NOT list all components here.
- Use tools instead:
  - stereotype_list_tool for full lists per stereotype
  - query_architecture_facts for focused queries"""

        # =====================================================================
        # INTERFACES (compact)
        # =====================================================================
        by_method: dict[str, int] = {}
        for iface in interfaces:
            method = iface.get("method", "GET")
            by_method[method] = by_method.get(method, 0) + 1
        method_lines = [f"- {m}: {c}" for m, c in sorted(by_method.items())]

        sample_iface_lines: list[str] = []
        for iface in interfaces[:15]:
            method = iface.get("method", "GET")
            path = iface.get("path", "/unknown")
            impl = iface.get("implemented_by", "UNKNOWN")
            ev_ids = iface.get("evidence_ids", [])
            sample_iface_lines.append(f"- {method} {path} (impl={impl}, evidence={summarize_evidence_ids(ev_ids)})")

        interfaces_summary = f"""REST API ANALYSIS (from facts)
Total Interfaces: {len(interfaces)}

By HTTP method:
{chr(10).join(method_lines) if method_lines else '- UNKNOWN'}

Sample endpoints (with evidence IDs):
{chr(10).join(sample_iface_lines) if sample_iface_lines else '- NONE'}"""

        # =====================================================================
        # RELATIONS (compact, correct field names: from/to)
        # =====================================================================
        rel_by_type_count: dict[str, int] = {}
        for rel in relations:
            rtype = rel.get("type", "unknown")
            rel_by_type_count[rtype] = rel_by_type_count.get(rtype, 0) + 1

        rel_type_lines = [f"- {t}: {c}" for t, c in sorted(rel_by_type_count.items())]

        sample_rel_lines: list[str] = []
        for rel in relations[:15]:
            r_from = rel.get("from", "?")
            r_to = rel.get("to", "?")
            r_type = rel.get("type", "unknown")
            ev_ids = rel.get("evidence_ids", [])
            sample_rel_lines.append(f"- {r_from} -> {r_to} ({r_type}, evidence={summarize_evidence_ids(ev_ids)})")

        relations_summary = f"""DEPENDENCY ANALYSIS (from facts)
Total Relations: {len(relations)}

Counts by type:
{chr(10).join(rel_type_lines) if rel_type_lines else '- NONE'}

Sample relations (with evidence IDs):
{chr(10).join(sample_rel_lines) if sample_rel_lines else '- NONE'}"""

        # =====================================================================
        # BUILDING BLOCKS (tiny seed list; full lists must be queried)
        # =====================================================================
        def top_names(stereo: str, max_items: int = 20) -> list[str]:
            return [c.get("name", "?") for c in components if c.get("stereotype") == stereo][:max_items]

        building_blocks_data = f"""BUILDING BLOCKS (seed data)

    NOTE:
    - This list is intentionally truncated to avoid token overflow.
    - Use stereotype_list_tool to retrieve full lists per stereotype.

    Controllers (top 20):
    {chr(10).join(['- ' + n for n in top_names('controller')]) if top_names('controller') else '- NONE'}

    Services (top 20):
    {chr(10).join(['- ' + n for n in top_names('service')]) if top_names('service') else '- NONE'}

    Repositories (top 20):
    {chr(10).join(['- ' + n for n in top_names('repository')]) if top_names('repository') else '- NONE'}

    Entities (top 20):
    {chr(10).join(['- ' + n for n in top_names('entity')]) if top_names('entity') else '- NONE'}"""

        def escape_braces(text: str) -> str:
            return text.replace("{", "{{").replace("}", "}}")
        
        return {
            "system_name": system_name,
            "system_summary": escape_braces(system_summary),
            "containers_summary": escape_braces(containers_summary),
            "components_summary": escape_braces(components_summary),
            "relations_summary": escape_braces(relations_summary),
            "interfaces_summary": escape_braces(interfaces_summary),
            "building_blocks_data": escape_braces(building_blocks_data),
        }
    
    @llm
    def default_llm(self) -> LLM:
        """Default LLM from environment variables."""
        model = os.getenv("MODEL", "gpt-oss-120b")
        api_base = os.getenv("API_BASE", "http://sov-ai-platform.nue.local.vm:4000/v1")

        raw_max_tokens = os.getenv("MAX_LLM_OUTPUT_TOKENS", "800")
        try:
            max_tokens = int(raw_max_tokens)
        except Exception:
            max_tokens = 800

        num_retries = int(os.getenv("LLM_NUM_RETRIES", "10"))

        # Some providers reject max_tokens<=0. Also guards against internal
        # calculations producing negative values when prompts are large.
        if max_tokens < 1:
            max_tokens = 800
        
        return LLM(
            model=model,
            base_url=api_base,
            temperature=0.1,
            max_tokens=max_tokens,
            timeout=300,  # 5 min timeout for large contexts
            num_retries=num_retries,
        )
    
    @tool
    def drawio_tool(self) -> DrawioDiagramTool:
        """Tool for creating DrawIO diagrams."""
        return DrawioDiagramTool()
    
    @tool
    def doc_writer_tool(self) -> DocWriterTool:
        """Tool for writing documentation."""
        return DocWriterTool()
    
    @tool
    def file_read_tool(self) -> FileReadTool:
        """Tool for reading files."""
        return FileReadTool()
    
    @tool
    def facts_query_tool(self) -> FactsQueryTool:
        """RAG-based tool for querying architecture facts (Strategy 6)."""
        return FactsQueryTool(facts_path=str(self.facts_path))
    
    @tool
    def chunked_writer_tool(self) -> ChunkedWriterTool:
        """Tool for chunked document generation (Strategy 7)."""
        return ChunkedWriterTool()
    
    @tool
    def stereotype_list_tool(self) -> StereotypeListTool:
        """Tool for listing components by stereotype (Strategy 2)."""
        return StereotypeListTool(facts_path=str(self.facts_path))
    
    @agent
    def arc42_architect(self) -> Agent:
        """Arc42 Architect agent from YAML config."""
        return Agent(
            config=self.agents_config['arc42_architect'],  # type: ignore[index]
            tools=[
                self.drawio_tool(),
                self.doc_writer_tool(),
                self.file_read_tool(),
                self.facts_query_tool(),
                self.chunked_writer_tool(),
                self.stereotype_list_tool(),
            ],
            verbose=True,
            max_iter=30,          # Allow more iterations before forcing final answer
            max_retry_limit=10,   # Retry more on LLM empty responses
        )
    
    # -------------------------------------------------------------------------
    # ARC42 TASKS - All 12 Chapters
    # -------------------------------------------------------------------------
    
    @task
    def arc42_introduction(self) -> Task:
        """arc42 Chapter 1: Introduction and Goals."""
        return Task(config=self.tasks_config['arc42_introduction'])  # type: ignore[index]
    
    @task
    def arc42_constraints(self) -> Task:
        """arc42 Chapter 2: Architecture Constraints."""
        return Task(config=self.tasks_config['arc42_constraints'])  # type: ignore[index]
    
    @task
    def arc42_context(self) -> Task:
        """arc42 Chapter 3: System Scope and Context."""
        return Task(config=self.tasks_config['arc42_context'])  # type: ignore[index]
    
    @task
    def arc42_solution_strategy(self) -> Task:
        """arc42 Chapter 4: Solution Strategy."""
        return Task(config=self.tasks_config['arc42_solution_strategy'])  # type: ignore[index]
    
    @task
    def arc42_building_blocks(self) -> Task:
        """arc42 Chapter 5: Building Block View."""
        return Task(config=self.tasks_config['arc42_building_blocks'])  # type: ignore[index]
    
    @task
    def arc42_runtime(self) -> Task:
        """arc42 Chapter 6: Runtime View."""
        return Task(config=self.tasks_config['arc42_runtime'])  # type: ignore[index]
    
    @task
    def arc42_deployment(self) -> Task:
        """arc42 Chapter 7: Deployment View."""
        return Task(config=self.tasks_config['arc42_deployment'])  # type: ignore[index]
    
    @task
    def arc42_crosscutting(self) -> Task:
        """arc42 Chapter 8: Cross-cutting Concepts."""
        return Task(config=self.tasks_config['arc42_crosscutting'])  # type: ignore[index]
    
    @task
    def arc42_decisions(self) -> Task:
        """arc42 Chapter 9: Architecture Decisions (ADRs)."""
        return Task(config=self.tasks_config['arc42_decisions'])  # type: ignore[index]
    
    @task
    def arc42_quality(self) -> Task:
        """arc42 Chapter 10: Quality Requirements."""
        return Task(config=self.tasks_config['arc42_quality'])  # type: ignore[index]
    
    @task
    def arc42_risks(self) -> Task:
        """arc42 Chapter 11: Risks and Technical Debt."""
        return Task(config=self.tasks_config['arc42_risks'])  # type: ignore[index]
    
    @task
    def arc42_glossary(self) -> Task:
        """arc42 Chapter 12: Glossary."""
        return Task(config=self.tasks_config['arc42_glossary'])  # type: ignore[index]
    
    @crew
    def crew(self) -> Crew:
        """Build the Arc42 crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,  # Disable memory to prevent context overflow
        )
    
    def run(self) -> str:
        """Execute the crew with summaries as inputs."""
        result = self.crew().kickoff(inputs=self.summaries)
        return str(result)
