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
        """Create MINIMAL summaries - Agent must discover everything else!

        IMPORTANT:
        - Only provide RAW STATISTICS here
        - NO interpretations, NO assumptions about architecture style
        - Agent MUST use tools to discover architecture styles, patterns, etc.
        - This prevents hallucination and ensures evidence-based documentation
        """
        facts = self.facts

        system_info = facts.get("system", {})
        system_name = system_info.get("name", "Unknown System")

        containers = facts.get("containers", [])
        components = facts.get("components", [])
        interfaces = facts.get("interfaces", [])
        relations = facts.get("relations", [])

        # =====================================================================
        # MINIMAL SYSTEM SUMMARY - Only statistics, no interpretations!
        # =====================================================================
        tech_stack = sorted({c.get("technology", "Unknown") for c in containers if c.get("technology")})
        
        # Count by stereotype (raw data for agent)
        by_stereotype: dict[str, int] = {}
        for comp in components:
            stereo = comp.get("stereotype", "unknown")
            by_stereotype[stereo] = by_stereotype.get(stereo, 0) + 1

        system_summary = f"""SYSTEM: {system_name}

RAW STATISTICS (from architecture_facts.json):
- Containers: {len(containers)}
- Components: {len(components)}
- Interfaces: {len(interfaces)}
- Relations: {len(relations)}

TECHNOLOGIES (from containers):
{chr(10).join([f'- {t}' for t in tech_stack]) if tech_stack else '- Use tools to discover'}

COMPONENT COUNTS BY STEREOTYPE:
{chr(10).join([f'- {k}: {v}' for k, v in sorted(by_stereotype.items())]) if by_stereotype else '- Use tools to discover'}

IMPORTANT: 
- Use list_components_by_stereotype with stereotype="architecture_style" to find the architecture!
- Use list_components_by_stereotype with stereotype="design_pattern" to find patterns!
- Do NOT assume - DISCOVER from facts!"""

        # =====================================================================
        # CONTAINERS (minimal - just list for reference)
        # =====================================================================
        container_lines = [
            f"- {c.get('name', '?')}: {c.get('technology', '?')}"
            for c in containers
        ]
        
        containers_summary = f"""CONTAINERS (raw data):
{chr(10).join(container_lines) if container_lines else '- Use query_architecture_facts to discover'}"""

        # Components summary already in system_summary via by_stereotype
        components_summary = "Use list_components_by_stereotype tool to query components by type."
        
        # Interfaces - just count
        interfaces_summary = f"Total interfaces: {len(interfaces)}. Use query_architecture_facts with category='interfaces' for details."
        
        # Relations - just count  
        relations_summary = f"Total relations: {len(relations)}. Use query_architecture_facts with category='relations' for details."
        
        # Building blocks - agent must discover
        building_blocks_data = "Use list_components_by_stereotype for each layer (controller, service, repository, entity)."

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
    def analyze_system(self) -> Task:
        """System analysis task (think before writing)."""
        return Task(config=self.tasks_config['analyze_system'])  # type: ignore[index]
    
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
    
    # -------------------------------------------------------------------------
    # BUILDING BLOCKS - Split into Sub-Tasks (Strategy 2)
    # -------------------------------------------------------------------------
    
    @task
    def bb_intro(self) -> Task:
        """Building Blocks Chapter 5 - Intro and Level 1."""
        return Task(config=self.tasks_config['bb_intro'])  # type: ignore[index]
    
    @task
    def bb_controllers(self) -> Task:
        """Building Blocks - Controllers section."""
        return Task(config=self.tasks_config['bb_controllers'])  # type: ignore[index]
    
    @task
    def bb_services(self) -> Task:
        """Building Blocks - Services section."""
        return Task(config=self.tasks_config['bb_services'])  # type: ignore[index]
    
    @task
    def bb_entities(self) -> Task:
        """Building Blocks - Entities section."""
        return Task(config=self.tasks_config['bb_entities'])  # type: ignore[index]
    
    @task
    def bb_repositories(self) -> Task:
        """Building Blocks - Repositories section."""
        return Task(config=self.tasks_config['bb_repositories'])  # type: ignore[index]
    
    @task
    def bb_merge(self) -> Task:
        """Building Blocks - Merge all sections."""
        return Task(config=self.tasks_config['bb_merge'])  # type: ignore[index]
    
    @task
    def arc42_runtime_view(self) -> Task:
        """arc42 Chapter 6: Runtime View."""
        return Task(config=self.tasks_config['arc42_runtime_view'])  # type: ignore[index]
    
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
