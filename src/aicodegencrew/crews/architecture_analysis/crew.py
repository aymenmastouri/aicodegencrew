"""
Architecture Analysis Crew - Phase 2
=====================================
Multi-agent crew for analyzing architecture facts and creating analyzed output.

ANALYSIS APPROACH:
- Input: architecture_facts.json + evidence_map.json + ChromaDB Index
- 4 Specialized Agents: Technical, Functional, Quality, Synthesis
- 17 Focused Tasks for token efficiency
- Output: analyzed_architecture.json

The agents use tools to DISCOVER architecture (not hardcoded).
"""
import logging
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai.mcp import MCPServerStdio
from crewai_tools import FileWriterTool

from .tools import FactsStatisticsTool, FactsQueryTool, RAGQueryTool, StereotypeListTool, PartialResultsTool

# MCP server script path (project root)
_MCP_SERVER_PATH = str(Path(__file__).resolve().parents[4] / "mcp_server.py")

# Import Pydantic schemas for output validation
from ...shared.models import (
    MacroArchitectureOutput,
    BackendPatternOutput,
    FrontendPatternOutput,
    ArchitectureQualityOutput,
    DomainModelOutput,
    BusinessCapabilitiesOutput,
    BoundedContextsOutput,
    StateMachinesOutput,
    WorkflowEnginesOutput,
    SagaPatternsOutput,
    RuntimeScenariosOutput,
    ApiDesignOutput,
    ComplexityOutput,
    TechnicalDebtOutput,
    SecurityOutput,
    OperationalReadinessOutput,
    AnalyzedArchitecture,
)

logger = logging.getLogger(__name__)


@CrewBase
class ArchitectureAnalysisCrew:
    """
    Architecture Analysis Crew - Phase 2.
    
    Multi-agent analysis:
    1. Tech Architect: Analyze styles, patterns, tech stack
    2. Functional Analyst: Analyze domain, capabilities, use cases
    3. Quality Analyst: Analyze quality, debt, risks
    4. Synthesis Lead: Merge all into analyzed_architecture.json
    
    Data Sources:
    - architecture_facts.json: Components, relations, interfaces, containers
    - evidence_map.json: Code snippets and file references
    - ChromaDB Index: Semantic search for specific patterns
    """
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(
        self,
        facts_path: str = "knowledge/architecture/architecture_facts.json",
        chroma_dir: str = None,
        output_dir: str = "knowledge/architecture"
    ):
        """Initialize crew with paths."""
        self.facts_path = Path(facts_path)
        self.evidence_path = self.facts_path.parent / "evidence_map.json"
        self.chroma_dir = chroma_dir or os.getenv("CHROMA_DIR", ".cache/.chroma")
        self.output_dir = Path(output_dir)
        
        # Initialize tools (shared by agents)
        self._facts_stats_tool = FactsStatisticsTool(facts_path=str(self.facts_path))
        self._facts_tool = FactsQueryTool(facts_path=str(self.facts_path))
        self._rag_tool = RAGQueryTool(chroma_dir=chroma_dir)
        self._stereotype_tool = StereotypeListTool(facts_path=str(self.facts_path))
        self._file_writer = FileWriterTool()
        self._partial_results_tool = PartialResultsTool(analysis_dir=str(self.output_dir / "analysis"))
        
        # Directory for partial task outputs
        self._analysis_dir = self.output_dir / "analysis"
        
    @before_kickoff
    def prepare_clean_run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prerequisites and archive+clean old outputs before running."""
        import shutil
        from datetime import datetime
        
        logger.info("")
        logger.info("[Phase2] Preparing clean run...")
        
        # Step 1: Validate prerequisites
        logger.info("[Phase2] Step 1: Checking Phase 1 prerequisites...")
        
        missing_files = []
        
        if not self.facts_path.exists():
            missing_files.append(str(self.facts_path))
        else:
            # Validate JSON is parseable and has required keys
            try:
                with open(self.facts_path, 'r', encoding='utf-8') as f:
                    facts_data = json.load(f)
                if not isinstance(facts_data, dict) or "components" not in facts_data:
                    logger.error(f"   [INVALID] {self.facts_path}: missing 'components' key")
                    missing_files.append(f"{self.facts_path} (invalid JSON structure)")
                else:
                    comp_count = len(facts_data.get("components", []))
                    logger.info(f"   [OK] Found: {self.facts_path} ({comp_count} components)")
            except json.JSONDecodeError as e:
                logger.error(f"   [INVALID] {self.facts_path}: {e}")
                missing_files.append(f"{self.facts_path} (invalid JSON)")

        if not self.evidence_path.exists():
            missing_files.append(str(self.evidence_path))
        else:
            logger.info(f"   [OK] Found: {self.evidence_path}")

        if missing_files:
            logger.error("")
            logger.error("=" * 60)
            logger.error("[ERROR] PHASE 2 CANNOT START")
            logger.error("=" * 60)
            logger.error("")
            logger.error("Missing Phase 1 output files:")
            for f in missing_files:
                logger.error(f"   [MISSING] {f}")
            logger.error("")
            logger.error("[HINT] Solution: Run Phase 1 first:")
            logger.error("   python run.py --phases phase1_architecture_facts")
            logger.error("")
            logger.error("=" * 60)
            raise FileNotFoundError(
                f"Missing Phase 1 files: {', '.join(missing_files)}. "
                f"Run Phase 1 first: python run.py --phases phase1_architecture_facts"
            )
        
        logger.info("   [OK] All prerequisites satisfied!")
        
        # Step 2: Archive and clean old outputs
        logger.info("[Phase2] Step 2: Archive and clean old outputs...")
        
        output_files = [
            "analyzed_architecture.json",
            "analysis_technical.json",
            "analysis_functional.json",
            "analysis_quality.json",
            # Legacy names
            "temp_technical_analysis.json",
            "temp_functional_analysis.json",
            "temp_quality_analysis.json",
        ]
        
        existing_files = [f for f in output_files if (self.output_dir / f).exists()]
        
        if existing_files:
            # Archive old outputs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_dir = self.output_dir / "archive" / f"run_{timestamp}"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            for filename in existing_files:
                src = self.output_dir / filename
                dst = archive_dir / filename
                shutil.copy2(src, dst)
                src.unlink()  # Delete after archiving
                logger.info(f"   [ARCHIVED+DELETED] {filename}")
            
            logger.info(f"   [OK] {len(existing_files)} old files archived to: {archive_dir}")
        else:
            logger.info("   [OK] No old outputs to clean (first run)")
        
        # Step 3: Clean partial analysis outputs
        logger.info("[Phase2] Step 3: Cleaning partial analysis outputs...")
        if self._analysis_dir.exists():
            for json_file in self._analysis_dir.glob("*.json"):
                json_file.unlink()
                logger.info(f"   [DELETED] {json_file.name}")
        self._analysis_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"   [OK] Analysis directory ready: {self._analysis_dir}")
        
        logger.info("")
        
        return inputs
    
    @after_kickoff
    def log_completion(self, result):
        """Log completion message and format JSON outputs."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 2 COMPLETE: Architecture Analysis finished")
        logger.info("=" * 60)
        
        # Format all JSON files with pretty-print
        logger.info("[Phase2] Formatting JSON outputs with pretty-print...")
        
        # Format analysis directory files
        for json_file in self._analysis_dir.glob("*.json"):
            self._format_json_file(json_file)
        
        # Format main output files
        for json_file in self.output_dir.glob("*.json"):
            self._format_json_file(json_file)
        
        logger.info(f"Output: {self.output_dir / 'analyzed_architecture.json'}")
        return result
    
    def _format_json_file(self, json_file: Path) -> None:
        """Format a JSON file with pretty-print."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"   [OK] Formatted: {json_file.name}")
        except Exception as e:
            logger.warning(f"   [WARN] Could not format {json_file.name}: {e}")
    
    # =========================================================================
    # AGENTS
    # =========================================================================
    
    @agent
    def tech_architect(self) -> Agent:
        """Technical Architect Agent."""
        return Agent(
            config=self.agents_config['tech_architect'],
            tools=[
                self._facts_stats_tool,  # Use FIRST for large repos
                self._facts_tool,
                self._rag_tool,
                self._stereotype_tool,
            ],
            # MCP Server for token-efficient architecture queries
            mcps=[
                MCPServerStdio(
                    command="python",
                    args=[_MCP_SERVER_PATH],
                    cache_tools_list=True,
                )
            ],
            verbose=True,
        )

    @agent
    def func_analyst(self) -> Agent:
        """Functional Analyst Agent."""
        return Agent(
            config=self.agents_config['func_analyst'],
            tools=[
                self._facts_stats_tool,  # Use FIRST for large repos
                self._facts_tool,
                self._rag_tool,
                self._stereotype_tool,
            ],
            # MCP Server for token-efficient architecture queries
            mcps=[
                MCPServerStdio(
                    command="python",
                    args=[_MCP_SERVER_PATH],
                    cache_tools_list=True,
                )
            ],
            verbose=True,
        )

    @agent
    def quality_analyst(self) -> Agent:
        """Quality Analyst Agent."""
        return Agent(
            config=self.agents_config['quality_analyst'],
            tools=[
                self._facts_stats_tool,  # Use FIRST for large repos
                self._facts_tool,
                self._rag_tool,
                self._stereotype_tool,
            ],
            # MCP Server for token-efficient architecture queries
            mcps=[
                MCPServerStdio(
                    command="python",
                    args=[_MCP_SERVER_PATH],
                    cache_tools_list=True,
                )
            ],
            verbose=True,
        )

    @agent
    def synthesis_lead(self) -> Agent:
        """Synthesis Lead Agent."""
        return Agent(
            config=self.agents_config['synthesis_lead'],
            tools=[
                self._partial_results_tool,  # Read all partial analysis outputs
                self._file_writer,
            ],
            # MCP Server for token-efficient architecture queries
            mcps=[
                MCPServerStdio(
                    command="python",
                    args=[_MCP_SERVER_PATH],
                    cache_tools_list=True,
                )
            ],
            verbose=True,
        )
    
    # =========================================================================
    # TASKS - Tech Architect (4 independent tasks)
    # =========================================================================
    
    @task
    def analyze_macro_architecture(self) -> Task:
        """Task 1.1: Macro Architecture Analysis."""
        return Task(
            config=self.tasks_config['analyze_macro_architecture'],
            agent=self.tech_architect(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=MacroArchitectureOutput,
            output_file=str(self._analysis_dir / "01_macro_architecture.json"),
        )
    
    @task
    def analyze_backend_pattern(self) -> Task:
        """Task 1.2: Backend Pattern Analysis."""
        return Task(
            config=self.tasks_config['analyze_backend_pattern'],
            agent=self.tech_architect(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=BackendPatternOutput,
            output_file=str(self._analysis_dir / "02_backend_pattern.json"),
        )
    
    @task
    def analyze_frontend_pattern(self) -> Task:
        """Task 1.3: Frontend Pattern Analysis."""
        return Task(
            config=self.tasks_config['analyze_frontend_pattern'],
            agent=self.tech_architect(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=FrontendPatternOutput,
            output_file=str(self._analysis_dir / "03_frontend_pattern.json"),
        )
    
    @task
    def analyze_architecture_quality(self) -> Task:
        """Task 1.4: Architecture Quality Assessment."""
        return Task(
            config=self.tasks_config['analyze_architecture_quality'],
            agent=self.tech_architect(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=ArchitectureQualityOutput,
            output_file=str(self._analysis_dir / "04_architecture_quality.json"),
        )
    
    # =========================================================================
    # TASKS - Functional Analyst (8 independent tasks)
    # =========================================================================
    
    @task
    def analyze_domain_model(self) -> Task:
        """Task 2.1: Domain Model Assessment."""
        return Task(
            config=self.tasks_config['analyze_domain_model'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=DomainModelOutput,
            output_file=str(self._analysis_dir / "05_domain_model.json"),
        )
    
    @task
    def analyze_business_capabilities(self) -> Task:
        """Task 2.2: Business Capabilities Analysis."""
        return Task(
            config=self.tasks_config['analyze_business_capabilities'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=BusinessCapabilitiesOutput,
            output_file=str(self._analysis_dir / "06_business_capabilities.json"),
        )
    
    @task
    def analyze_bounded_contexts(self) -> Task:
        """Task 2.3: Bounded Context Analysis."""
        return Task(
            config=self.tasks_config['analyze_bounded_contexts'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=BoundedContextsOutput,
            output_file=str(self._analysis_dir / "07_bounded_contexts.json"),
        )
    
    @task
    def analyze_state_machines(self) -> Task:
        """Task 2.4: State Machine Detection."""
        return Task(
            config=self.tasks_config['analyze_state_machines'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=StateMachinesOutput,
            output_file=str(self._analysis_dir / "08_state_machines.json"),
        )
    
    @task
    def analyze_workflow_engines(self) -> Task:
        """Task 2.5: Workflow Engine Detection."""
        return Task(
            config=self.tasks_config['analyze_workflow_engines'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=WorkflowEnginesOutput,
            output_file=str(self._analysis_dir / "09_workflow_engines.json"),
        )
    
    @task
    def analyze_saga_patterns(self) -> Task:
        """Task 2.6: Saga Pattern Detection."""
        return Task(
            config=self.tasks_config['analyze_saga_patterns'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=SagaPatternsOutput,
            output_file=str(self._analysis_dir / "10_saga_patterns.json"),
        )
    
    @task
    def analyze_runtime_scenarios(self) -> Task:
        """Task 2.7: Runtime Scenarios (Arc42 Section 6)."""
        return Task(
            config=self.tasks_config['analyze_runtime_scenarios'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=RuntimeScenariosOutput,
            output_file=str(self._analysis_dir / "11_runtime_scenarios.json"),
        )
    
    @task
    def analyze_api_design(self) -> Task:
        """Task 2.8: API Design Quality."""
        return Task(
            config=self.tasks_config['analyze_api_design'],
            agent=self.func_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=ApiDesignOutput,
            output_file=str(self._analysis_dir / "12_api_design.json"),
        )
    
    # =========================================================================
    # TASKS - Quality Analyst (4 independent tasks)
    # =========================================================================
    
    @task
    def analyze_complexity(self) -> Task:
        """Task 3.1: Complexity Assessment."""
        return Task(
            config=self.tasks_config['analyze_complexity'],
            agent=self.quality_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=ComplexityOutput,
            output_file=str(self._analysis_dir / "13_complexity.json"),
        )
    
    @task
    def analyze_technical_debt(self) -> Task:
        """Task 3.2: Technical Debt Assessment."""
        return Task(
            config=self.tasks_config['analyze_technical_debt'],
            agent=self.quality_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=TechnicalDebtOutput,
            output_file=str(self._analysis_dir / "14_technical_debt.json"),
        )
    
    @task
    def analyze_security(self) -> Task:
        """Task 3.3: Security Posture Assessment."""
        return Task(
            config=self.tasks_config['analyze_security'],
            agent=self.quality_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=SecurityOutput,
            output_file=str(self._analysis_dir / "15_security.json"),
        )
    
    @task
    def analyze_operational_readiness(self) -> Task:
        """Task 3.4: Operational Readiness Assessment."""
        return Task(
            config=self.tasks_config['analyze_operational_readiness'],
            agent=self.quality_analyst(),
            context=[],  # No context from previous tasks - independent analysis
            output_pydantic=OperationalReadinessOutput,
            output_file=str(self._analysis_dir / "16_operational_readiness.json"),
        )
    
    # =========================================================================
    # TASKS - Synthesis (merges all outputs)
    # =========================================================================
    
    @task
    def synthesize_architecture(self) -> Task:
        """Task 4: Merge all analyses into analyzed_architecture.json.
        
        Uses PartialResultsTool to read all partial analysis outputs from files.
        All previous tasks have already completed (sequential execution with context=[]).
        This task also uses context=[] to avoid receiving raw outputs - instead reads structured JSON files.
        """
        return Task(
            config=self.tasks_config['synthesize_architecture'],
            agent=self.synthesis_lead(),
            context=[],  # Don't pass previous outputs as context - read from files instead
            output_pydantic=AnalyzedArchitecture,
            output_file=str(self.output_dir / "analyzed_architecture.json"),
        )
    
    # =========================================================================
    # CREW
    # =========================================================================
    
    @crew
    def crew(self) -> Crew:
        """Create the Architecture Analysis Crew."""
        return Crew(
            agents=self.agents,  # Automatically populated by @agent decorators
            tasks=self.tasks,    # Automatically populated by @task decorators
            process=Process.sequential,
            verbose=True,
            memory=False,  # Disable memory - tasks are independent, no shared context needed
            full_output=False,  # Only return final result, not intermediate
            max_rpm=30,  # Rate limit: max 30 requests/minute to LLM API
            planning=False,  # Tasks already have clear step-by-step instructions
        )
    
    def run(self) -> str:
        """Execute the crew."""
        result = self.crew().kickoff()
        return str(result)
    
    def kickoff(self, inputs: Dict[str, Any] = None) -> str:
        """Execute crew - compatible with orchestrator interface."""
        return self.run()
