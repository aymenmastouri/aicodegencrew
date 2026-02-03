"""
C4 Crew - Phase 2 Subcrew
==========================
Erstellt alle 4 C4 Diagramme: Context, Container, Component, Deployment

CrewAI Best Practices Applied:
- Strategy 3: Hierarchical task dependencies (Context -> Container -> Component -> Deployment)
- Strategy 6: FactsQueryTool for RAG-based facts retrieval
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
    FileReadTool,  # Safe version with size limits
)


@CrewBase
class C4Crew:
    """
    C4 Crew - Creates all 4 C4 Model views.
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
        """Create evidence-first summaries for C4 diagram generation.

        IMPORTANT:
        - Phase 2 must not invent architecture.
        - Any statement not backed by Phase 1 facts/evidence must be marked UNKNOWN.
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

        def fmt_evidence(evidence_ids: list[str] | None) -> str:
            if not evidence_ids:
                return "[]"
            parts: list[str] = []
            for ev_id in evidence_ids:
                ev = evidence_map.get(ev_id)
                if isinstance(ev, dict):
                    path = ev.get("path", "?")
                    lines = ev.get("lines", "?")
                    reason = ev.get("reason", "?")
                    parts.append(f"{ev_id} ({path}:{lines}) - {reason}")
                else:
                    parts.append(str(ev_id))
            return "\n".join([f"- {p}" for p in parts])
        
        # =====================================================================
        # DETAILED SYSTEM SUMMARY FOR C4 CONTEXT
        # =====================================================================
        tech_stack = sorted({c.get("technology", "Unknown") for c in containers if c.get("technology")})
        container_list_lines: list[str] = []
        for c in containers:
            cid = c.get("id", "?")
            cname = c.get("name", "?")
            ctype = c.get("type", "UNKNOWN")
            ctech = c.get("technology", "UNKNOWN")
            ev_ids = c.get("evidence", [])
            container_list_lines.append(
                f"- {cid}: {cname} | type={ctype} | tech={ctech}" + (f" | evidence={ev_ids}" if ev_ids else "")
            )

        system_summary = f"""SYSTEM: {system_name}
DOMAIN: {system_info.get('domain', 'UNKNOWN')}
ARCHITECTURE STYLE: {style_name}
LAYERS (from facts): {', '.join(layers) if layers else 'UNKNOWN'}
PATTERNS (from facts): {', '.join(patterns) if patterns else 'UNKNOWN'}

STATISTICS (Phase 1):
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGY (from containers):
{chr(10).join([f'- {t}' for t in tech_stack]) if tech_stack else '- UNKNOWN'}

CONTAINERS (from facts):
{chr(10).join(container_list_lines) if container_list_lines else '- NONE'}

EXTERNAL ACTORS / EXTERNAL SYSTEMS:
- UNKNOWN (not extracted in Phase 1)"""

        # =====================================================================
        # DETAILED CONTAINERS FOR C4 CONTAINER DIAGRAM
        # =====================================================================
        container_details: list[str] = []
        for c in containers:
            cid = c.get("id", "?")
            name = c.get('name', '?')
            ctype = c.get('type', 'UNKNOWN')
            tech = c.get('technology', 'Unknown')
            root_path = c.get('root_path', 'UNKNOWN')
            ev_ids = c.get("evidence", [])
            container_details.append(
                f"""CONTAINER: {name} (id={cid})
  Type: {ctype}
  Technology: {tech}
  Root Path: {root_path}
  Evidence IDs: {ev_ids if ev_ids else '[]'}
  Evidence Details:\n{fmt_evidence(ev_ids) if ev_ids else '- NONE'}\n"""
            )

        containers_summary = f"""CONTAINER ANALYSIS (facts + evidence)
Total: {len(containers)} containers

{''.join(container_details)}

CONTAINER RELATIONSHIPS:
- UNKNOWN at container-level (Phase 1 primarily extracts code-level relations)."""

        # =====================================================================
        # COMPONENT STATISTICS FOR C4 COMPONENT DIAGRAM
        # =====================================================================
        by_stereotype: dict[str, list] = {}
        for comp in components:
            stereo = comp.get("stereotype", "component")
            if stereo not in by_stereotype:
                by_stereotype[stereo] = []
            by_stereotype[stereo].append(comp.get("name", "?"))
        
        component_sections = []
        for stereo, names in sorted(by_stereotype.items()):
            component_sections.append(f"""
{stereo.upper()} LAYER: {len(names)} components
  Examples: {', '.join(names[:10])}{'...' if len(names) > 10 else ''}""")
        
        components_summary = f"""COMPONENT ANALYSIS (from facts)
    Total: {len(components)} components

    {''.join(component_sections)}

    LAYER / STEREOTYPE NOTES:
    - If a "layer" field is missing in facts, treat it as UNKNOWN.
    - Do not assume strict layering unless evidence exists."""

        # =====================================================================
        # INTERFACE SUMMARY FOR C4 DIAGRAMS
        # =====================================================================
        by_method: dict[str, int] = {}
        for iface in interfaces:
            method = iface.get("method", "GET")
            by_method[method] = by_method.get(method, 0) + 1
        
        method_lines = [f"  - {method}: {count}" for method, count in sorted(by_method.items())]
        
        # Sample endpoints
        sample_endpoints: list[str] = []
        for iface in interfaces[:20]:
            method = iface.get("method", "GET")
            path = iface.get("path", "/unknown")
            impl = iface.get("implemented_by", "UNKNOWN")
            ev_ids = iface.get("evidence_ids", [])
            ev_hint = ev_ids[0] if ev_ids else "UNKNOWN"
            sample_endpoints.append(f"  - {method} {path} (impl={impl}, evidence={ev_hint})")
        
        interfaces_summary = f"""REST API ANALYSIS (from facts)
    Total: {len(interfaces)} endpoints

    By HTTP Method:
    {chr(10).join(method_lines) if method_lines else '  - UNKNOWN'}

    Sample Endpoints (with evidence IDs):
    {chr(10).join(sample_endpoints) if sample_endpoints else '  - NONE'}
    {'  ... and ' + str(len(interfaces) - 20) + ' more' if len(interfaces) > 20 else ''}"""

        # =====================================================================
        # RELATIONS FOR DEPENDENCY ANALYSIS
        # =====================================================================
        rel_by_type: dict[str, int] = {}
        for rel in relations:
            rtype = rel.get("type", "unknown")
            rel_by_type[rtype] = rel_by_type.get(rtype, 0) + 1
        
        rel_lines = [f"  - {rtype}: {count}" for rtype, count in sorted(rel_by_type.items())]
        
        sample_rel_lines: list[str] = []
        for rel in relations[:20]:
            r_from = rel.get("from", "?")
            r_to = rel.get("to", "?")
            r_type = rel.get("type", "unknown")
            ev_ids = rel.get("evidence_ids", [])
            ev_hint = ev_ids[0] if ev_ids else "UNKNOWN"
            sample_rel_lines.append(f"  - {r_from} -> {r_to} ({r_type}, evidence={ev_hint})")

        relations_summary = f"""DEPENDENCY ANALYSIS (from facts)
    Total: {len(relations)} relations

    By Type:
    {chr(10).join(rel_lines) if rel_lines else '  - UNKNOWN'}

    Sample Relations (with evidence IDs):
    {chr(10).join(sample_rel_lines) if sample_rel_lines else '  - NONE'}"""

        def escape_braces(text: str) -> str:
            return text.replace("{", "{{").replace("}", "}}")
        
        return {
            "system_summary": escape_braces(system_summary),
            "containers_summary": escape_braces(containers_summary),
            "components_summary": escape_braces(components_summary),
            "relations_summary": escape_braces(relations_summary),
            "interfaces_summary": escape_braces(interfaces_summary),
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
    
    @agent
    def c4_architect(self) -> Agent:
        """C4 Architect agent from YAML config."""
        return Agent(
            config=self.agents_config['c4_architect'],  # type: ignore[index]
            tools=[
                self.drawio_tool(),
                self.doc_writer_tool(),
                self.file_read_tool(),
                self.facts_query_tool(),
            ],
            verbose=True,
            max_iter=30,          # Allow more iterations before forcing final answer
            max_retry_limit=10,   # Retry more on LLM empty responses
        )
    
    @task
    def c4_context(self) -> Task:
        """C4 Context diagram task (Level 1)."""
        return Task(config=self.tasks_config['c4_context'])  # type: ignore[index]
    
    @task
    def c4_container(self) -> Task:
        """C4 Container diagram task (Level 2)."""
        return Task(config=self.tasks_config['c4_container'])  # type: ignore[index]
    
    @task
    def c4_component(self) -> Task:
        """C4 Component diagram task (Level 3)."""
        return Task(config=self.tasks_config['c4_component'])  # type: ignore[index]
    
    @task
    def c4_deployment(self) -> Task:
        """C4 Deployment diagram task (Level 4)."""
        return Task(config=self.tasks_config['c4_deployment'])  # type: ignore[index]
    
    @crew
    def crew(self) -> Crew:
        """Build the C4 crew."""
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
