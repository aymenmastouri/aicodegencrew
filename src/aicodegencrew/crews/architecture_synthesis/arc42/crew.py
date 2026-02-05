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
from ...architecture_analysis.tools import RAGQueryTool


@CrewBase
class Arc42Crew:
    """
    Arc42 Crew - Creates all 12 arc42 chapters.
    
    Data Sources:
    - architecture_facts.json (Phase 1): Exact component names, relations
    - analyzed_architecture.json (Phase 2): Architecture styles, patterns, quality
    """
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    agents: List[BaseAgent]
    tasks: List[Task]
    
    def __init__(
        self, 
        facts_path: str = "knowledge/architecture/architecture_facts.json",
        analyzed_path: str = None,
        chroma_dir: str = None
    ):
        """Initialize crew with architecture facts, analysis, and ChromaDB."""
        self.facts_path = Path(facts_path)
        self.analyzed_path = Path(analyzed_path) if analyzed_path else self.facts_path.parent / "analyzed_architecture.json"
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", ".cache/.chroma")
        self.facts = self._load_facts()
        self.analysis = self._load_analysis()
        self.evidence_map = self._load_evidence_map()
        self.summaries = self._summarize_facts()
    
    def _load_facts(self) -> dict:
        """Load architecture facts from JSON file (Phase 1)."""
        if self.facts_path.exists():
            with open(self.facts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_analysis(self) -> dict:
        """Load architecture analysis from JSON file (Phase 2)."""
        if self.analyzed_path.exists():
            with open(self.analyzed_path, 'r', encoding='utf-8') as f:
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
        """Create summaries combining Phase 1 facts and Phase 2 analysis.

        IMPORTANT:
        - Use Phase 1 facts for exact names and counts
        - Use Phase 2 analysis for architecture interpretation
        - If Phase 2 analysis is empty, use tools to discover
        """
        facts = self.facts
        analysis = self.analysis

        system_info = facts.get("system", {})
        system_name = system_info.get("name", "Unknown System")
        
        # Phase 2 analysis data
        arch_info = analysis.get("architecture", {})
        quality_info = analysis.get("quality_attributes", {})
        capabilities = analysis.get("capabilities", [])
        risks = analysis.get("risks", [])

        containers = facts.get("containers", [])
        components = facts.get("components", [])
        interfaces = facts.get("interfaces", [])
        relations = facts.get("relations", [])

        # =====================================================================
        # COMBINED SUMMARY - Facts + Analysis
        # =====================================================================
        tech_stack = sorted({c.get("technology", "Unknown") for c in containers if c.get("technology")})
        
        # Count by stereotype (raw data for agent)
        by_stereotype: dict[str, int] = {}
        for comp in components:
            stereo = comp.get("stereotype", "unknown")
            by_stereotype[stereo] = by_stereotype.get(stereo, 0) + 1
        
        # Architecture style from Phase 2
        arch_style = arch_info.get("primary_style", "UNKNOWN - use tools to discover")
        patterns = analysis.get("patterns", [])

        system_summary = f"""SYSTEM: {system_name}

ARCHITECTURE (from Phase 2 analysis):
- Primary Style: {arch_style}
- Patterns: {', '.join([p.get('name', 'unknown') for p in patterns]) if patterns else 'Use tools to discover'}

STATISTICS (from Phase 1 facts):
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
        model = os.getenv("MODEL", "gpt-4o-mini")
        api_base = os.getenv("API_BASE", "")

        raw_max_tokens = os.getenv("MAX_LLM_OUTPUT_TOKENS", "4000")
        try:
            max_tokens = int(raw_max_tokens)
        except Exception:
            max_tokens = 4000

        num_retries = int(os.getenv("LLM_NUM_RETRIES", "10"))

        # Some providers reject max_tokens<=0. Also guards against internal
        # calculations producing negative values when prompts are large.
        if max_tokens < 1:
            max_tokens = 4000
        
        # Context window for the model - prevents sending too large prompts
        # IMPORTANT: Reserve space for output tokens to prevent vllm/litellm from
        # calculating negative max_tokens when input approaches context limit.
        # The effective context for input = context_window - max_tokens (output reserve)
        raw_context_window = int(os.getenv("LLM_CONTEXT_WINDOW", "120000"))
        # Reserve output space: effective context window = total - output reserve
        # This ensures litellm never calculates negative available tokens
        output_reserve = max(max_tokens, 8000)  # Reserve at least 8k for output
        context_window = raw_context_window - output_reserve
        
        return LLM(
            model=model,
            base_url=api_base,
            temperature=0.1,
            max_tokens=max_tokens,
            context_window=context_window,  # Limit prompt size (output space reserved)
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
    
    @tool
    def rag_query_tool(self) -> RAGQueryTool:
        """ChromaDB semantic search for code context."""
        return RAGQueryTool(chroma_dir=self.chroma_dir)
    
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
                self.rag_query_tool(),
            ],
            verbose=True,
            max_iter=30,          # Allow more iterations before forcing final answer
            max_retry_limit=10,   # Retry more on LLM empty responses
        )
    
    # -------------------------------------------------------------------------
    # ARC42 TASKS - All Subtasks matching tasks.yaml
    # -------------------------------------------------------------------------
    
    # ANALYZE SYSTEM SUBTASKS
    @task
    def analyze_system_datasources(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_datasources'])
    
    @task
    def analyze_system_identity(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_identity'])
    
    @task
    def analyze_system_architecture(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_architecture'])
    
    @task
    def analyze_system_technology(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_technology'])
    
    @task
    def analyze_system_components(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_components'])
    
    @task
    def analyze_system_dependencies(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_dependencies'])
    
    @task
    def analyze_system_integration(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_integration'])
    
    @task
    def analyze_system_quality(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_quality'])
    
    @task
    def analyze_system_risks(self) -> Task:
        return Task(config=self.tasks_config['analyze_system_risks'])
    
    # CHAPTER 1: INTRODUCTION SUBTASKS
    @task
    def intro_requirements(self) -> Task:
        return Task(config=self.tasks_config['intro_requirements'])
    
    @task
    def intro_quality_goals(self) -> Task:
        return Task(config=self.tasks_config['intro_quality_goals'])
    
    @task
    def intro_stakeholders(self) -> Task:
        return Task(config=self.tasks_config['intro_stakeholders'])
    
    @task
    def intro_merge(self) -> Task:
        return Task(config=self.tasks_config['intro_merge'])
    
    # CHAPTER 2: CONSTRAINTS SUBTASKS
    @task
    def constraints_technical(self) -> Task:
        return Task(config=self.tasks_config['constraints_technical'])
    
    @task
    def constraints_organizational(self) -> Task:
        return Task(config=self.tasks_config['constraints_organizational'])
    
    @task
    def constraints_conventions(self) -> Task:
        return Task(config=self.tasks_config['constraints_conventions'])
    
    @task
    def constraints_merge(self) -> Task:
        return Task(config=self.tasks_config['constraints_merge'])
    
    # CHAPTER 3: CONTEXT SUBTASKS
    @task
    def context_business(self) -> Task:
        return Task(config=self.tasks_config['context_business'])
    
    @task
    def context_technical(self) -> Task:
        return Task(config=self.tasks_config['context_technical'])
    
    @task
    def context_dependencies(self) -> Task:
        return Task(config=self.tasks_config['context_dependencies'])
    
    @task
    def context_merge(self) -> Task:
        return Task(config=self.tasks_config['context_merge'])
    
    # CHAPTER 4: SOLUTION STRATEGY SUBTASKS
    @task
    def strategy_technology(self) -> Task:
        return Task(config=self.tasks_config['strategy_technology'])
    
    @task
    def strategy_patterns(self) -> Task:
        return Task(config=self.tasks_config['strategy_patterns'])
    
    @task
    def strategy_quality(self) -> Task:
        return Task(config=self.tasks_config['strategy_quality'])
    
    @task
    def strategy_merge(self) -> Task:
        return Task(config=self.tasks_config['strategy_merge'])
    
    # CHAPTER 5: BUILDING BLOCKS SUBTASKS
    @task
    def bb_overview(self) -> Task:
        return Task(config=self.tasks_config['bb_overview'])
    
    @task
    def bb_controllers(self) -> Task:
        return Task(config=self.tasks_config['bb_controllers'])
    
    @task
    def bb_services(self) -> Task:
        return Task(config=self.tasks_config['bb_services'])
    
    @task
    def bb_entities(self) -> Task:
        return Task(config=self.tasks_config['bb_entities'])
    
    @task
    def bb_repositories(self) -> Task:
        return Task(config=self.tasks_config['bb_repositories'])
    
    @task
    def bb_dependencies(self) -> Task:
        return Task(config=self.tasks_config['bb_dependencies'])
    
    @task
    def bb_merge(self) -> Task:
        return Task(config=self.tasks_config['bb_merge'])
    
    # CHAPTER 6: RUNTIME VIEW SUBTASKS
    @task
    def runtime_scenarios(self) -> Task:
        return Task(config=self.tasks_config['runtime_scenarios'])
    
    @task
    def runtime_patterns(self) -> Task:
        return Task(config=self.tasks_config['runtime_patterns'])
    
    @task
    def runtime_merge(self) -> Task:
        return Task(config=self.tasks_config['runtime_merge'])
    
    # CHAPTER 7: DEPLOYMENT VIEW SUBTASKS
    @task
    def deployment_infrastructure(self) -> Task:
        return Task(config=self.tasks_config['deployment_infrastructure'])
    
    @task
    def deployment_environments(self) -> Task:
        return Task(config=self.tasks_config['deployment_environments'])
    
    @task
    def deployment_merge(self) -> Task:
        return Task(config=self.tasks_config['deployment_merge'])
    
    # CHAPTER 8: CROSSCUTTING SUBTASKS
    @task
    def crosscutting_domain(self) -> Task:
        return Task(config=self.tasks_config['crosscutting_domain'])
    
    @task
    def crosscutting_security(self) -> Task:
        return Task(config=self.tasks_config['crosscutting_security'])
    
    @task
    def crosscutting_persistence(self) -> Task:
        return Task(config=self.tasks_config['crosscutting_persistence'])
    
    @task
    def crosscutting_operations(self) -> Task:
        return Task(config=self.tasks_config['crosscutting_operations'])
    
    @task
    def crosscutting_merge(self) -> Task:
        return Task(config=self.tasks_config['crosscutting_merge'])
    
    # CHAPTERS 9-12: SINGLE TASKS (small enough)
    @task
    def arc42_decisions(self) -> Task:
        return Task(config=self.tasks_config['arc42_decisions'])
    
    @task
    def arc42_quality(self) -> Task:
        return Task(config=self.tasks_config['arc42_quality'])
    
    @task
    def arc42_risks(self) -> Task:
        return Task(config=self.tasks_config['arc42_risks'])
    
    @task
    def arc42_glossary(self) -> Task:
        return Task(config=self.tasks_config['arc42_glossary'])
    
    # QUALITY GATE
    @task
    def quality_gate(self) -> Task:
        return Task(config=self.tasks_config['quality_gate'])
    
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
