"""
Architecture Analysis Crew - Phase 2
=====================================
Multi-agent crew for analyzing architecture facts and creating analyzed output.

ANALYSIS APPROACH:
- Input: architecture_facts.json + evidence_map.json + ChromaDB Index
- 4 Specialized Agents: Technical, Functional, Quality, Synthesis
- Output: analyzed_architecture.json

The agents use tools to DISCOVER architecture (not hardcoded).
"""
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew, before_kickoff, after_kickoff
from crewai_tools import FileWriterTool

from .tools import FactsQueryTool, RAGQueryTool, StereotypeListTool

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
        chroma_dir: str = ".chroma_db",
        output_dir: str = "knowledge/architecture"
    ):
        """Initialize crew with paths."""
        self.facts_path = Path(facts_path)
        self.evidence_path = self.facts_path.parent / "evidence_map.json"
        self.chroma_dir = chroma_dir
        self.output_dir = Path(output_dir)
        
        # Initialize tools (shared by agents)
        self._facts_tool = FactsQueryTool(facts_path=str(self.facts_path))
        self._rag_tool = RAGQueryTool(chroma_dir=chroma_dir)
        self._stereotype_tool = StereotypeListTool(facts_path=str(self.facts_path))
        self._file_writer = FileWriterTool()
        
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
            logger.info(f"   [OK] Found: {self.facts_path}")
        
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
        
        logger.info("")
        
        return inputs
    
    @after_kickoff
    def log_completion(self, result):
        """Log completion message."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("PHASE 2 COMPLETE: Architecture Analysis finished")
        logger.info("=" * 60)
        logger.info(f"Output: {self.output_dir / 'analyzed_architecture.json'}")
        return result
    
    # =========================================================================
    # AGENTS
    # =========================================================================
    
    @agent
    def tech_architect(self) -> Agent:
        """Technical Architect Agent."""
        return Agent(
            config=self.agents_config['tech_architect'],
            tools=[
                self._facts_tool,
                self._rag_tool,
                self._stereotype_tool,
            ],
            verbose=True,
        )
    
    @agent
    def func_analyst(self) -> Agent:
        """Functional Analyst Agent."""
        return Agent(
            config=self.agents_config['func_analyst'],
            tools=[
                self._facts_tool,
                self._rag_tool,
                self._stereotype_tool,
            ],
            verbose=True,
        )
    
    @agent
    def quality_analyst(self) -> Agent:
        """Quality Analyst Agent."""
        return Agent(
            config=self.agents_config['quality_analyst'],
            tools=[
                self._facts_tool,
                self._rag_tool,
                self._stereotype_tool,
            ],
            verbose=True,
        )
    
    @agent
    def synthesis_lead(self) -> Agent:
        """Synthesis Lead Agent."""
        return Agent(
            config=self.agents_config['synthesis_lead'],
            tools=[
                self._file_writer,
            ],
            verbose=True,
        )
    
    # =========================================================================
    # TASKS
    # =========================================================================
    
    @task
    def analyze_technical(self) -> Task:
        """Technical architecture analysis task."""
        return Task(
            config=self.tasks_config['analyze_technical'],
            agent=self.tech_architect(),
            output_file=str(self.output_dir / "analysis_technical.json"),
            # Sequential - deep analysis takes time, no rush
        )
    
    @task
    def analyze_functional(self) -> Task:
        """Functional/domain analysis task."""
        return Task(
            config=self.tasks_config['analyze_functional'],
            agent=self.func_analyst(),
            output_file=str(self.output_dir / "analysis_functional.json"),
            # Sequential - deep analysis takes time, no rush
        )
    
    @task
    def analyze_quality(self) -> Task:
        """Quality analysis task."""
        return Task(
            config=self.tasks_config['analyze_quality'],
            agent=self.quality_analyst(),
            output_file=str(self.output_dir / "analysis_quality.json"),
            # Sequential - deep analysis takes time, no rush
        )
    
    @task
    def synthesize_architecture(self) -> Task:
        """Merge all analyses into analyzed_architecture.json."""
        return Task(
            config=self.tasks_config['synthesize_architecture'],
            agent=self.synthesis_lead(),
            context=[
                self.analyze_technical(),
                self.analyze_functional(),
                self.analyze_quality(),
            ],
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
        )
    
    def run(self) -> str:
        """Execute the crew."""
        result = self.crew().kickoff()
        return str(result)
    
    def kickoff(self, inputs: Dict[str, Any] = None) -> str:
        """Execute crew - compatible with orchestrator interface."""
        return self.run()
