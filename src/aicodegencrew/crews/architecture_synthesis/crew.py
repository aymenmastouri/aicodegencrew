"""
Architecture Synthesis Crew - Phase 3
=====================================
Orchestrates two sub-crews for reverse engineering documentation:

REVERSE ENGINEERING APPROACH:
- Input: architecture_facts.json (Phase 1) + analyzed_architecture.json (Phase 2)
- C4 Crew: Creates 4 C4 diagrams with DrawIO files
- Arc42 Crew: Creates 12 arc42 chapters (50+ pages, 90% coverage)

The agents are REVERSE ENGINEERING EXPERTS who analyze extracted facts
and generate comprehensive architecture documentation.
"""
import logging
from pathlib import Path

from .c4.crew import C4Crew
from .arc42.crew import Arc42Crew

logger = logging.getLogger(__name__)


class ArchitectureSynthesisCrew:
    """
    Architecture Synthesis Crew - Phase 3 Orchestrator.
    
    Reverse Engineering Documentation:
    1. C4 Crew - Creates 4 C4 diagrams with DrawIO files  
    2. Arc42 Crew - Creates 12 arc42 chapters (50+ pages)
    
    Data Sources:
    - architecture_facts.json: Components, relations, interfaces, containers (Phase 1)
    - analyzed_architecture.json: Architecture styles, patterns, quality (Phase 2)
    - evidence_map.json: Code snippets and file references
    - ChromaDB Index: Semantic search (optional)
    """
    
    def __init__(self, facts_path: str = "knowledge/architecture/architecture_facts.json"):
        """Initialize orchestrator with architecture facts path."""
        self.facts_path = Path(facts_path)
        self.evidence_path = self.facts_path.parent / "evidence_map.json"
        self.analyzed_path = self.facts_path.parent / "analyzed_architecture.json"
        self.c4_crew = None
        self.arc42_crew = None
        # Note: Validation happens at kickoff(), not here (allows Phase 1+2 to run first)
    
    def _validate_prerequisites(self):
        """Validate that Phase 1 and Phase 2 output files exist before running Phase 3."""
        logger.info("")
        logger.info("[Phase3] Checking prerequisites...")
        
        missing_files = []
        optional_missing = []
        
        # Required: Phase 1 outputs
        if not self.facts_path.exists():
            missing_files.append(str(self.facts_path))
        else:
            logger.info(f"   [OK] Found: {self.facts_path}")
        
        if not self.evidence_path.exists():
            missing_files.append(str(self.evidence_path))
        else:
            logger.info(f"   [OK] Found: {self.evidence_path}")
        
        # Required: Phase 2 output
        if not self.analyzed_path.exists():
            missing_files.append(str(self.analyzed_path))
        else:
            logger.info(f"   [OK] Found: {self.analyzed_path}")
        
        if missing_files:
            logger.error("")
            logger.error("=" * 60)
            logger.error("[ERROR] PHASE 3 CANNOT START")
            logger.error("=" * 60)
            logger.error("")
            logger.error("Missing prerequisite files:")
            for f in missing_files:
                logger.error(f"   [MISSING] {f}")
            logger.error("")
            logger.error("[HINT] Solution: Run Phase 1 and Phase 2 first:")
            logger.error("   python -m aicodegencrew run --phases phase1_architecture_facts,phase2_architecture_analysis")
            logger.error("")
            logger.error("=" * 60)
            raise FileNotFoundError(
                f"Missing prerequisite files: {', '.join(missing_files)}. "
                f"Run Phase 1 and Phase 2 first."
            )
        
        logger.info("   [OK] All prerequisites satisfied!")
        logger.info("")
    
    def run(self) -> str:
        """
        Execute both crews sequentially.
        
        Sequence:
        1. C4: Facts + Analysis -> 4 C4 diagrams + DrawIO
        2. Arc42: Facts + Analysis -> 12 deep chapters (50+ pages)
        
        Returns combined result summary.
        """
        # Validate prerequisites before running
        self._validate_prerequisites()
        
        results = []
        
        # Phase 3a: C4 Diagrams
        logger.info("=" * 60)
        logger.info("PHASE 3a: C4 CREW - Creating C4 Diagrams + DrawIO")
        logger.info("=" * 60)
        
        self.c4_crew = C4Crew(
            facts_path=str(self.facts_path),
            analyzed_path=str(self.analyzed_path)
        )
        c4_result = self.c4_crew.run()
        results.append(f"C4 Crew Result:\n{c4_result}")
        
        logger.info("C4 Crew completed")
        
        # Phase 3b: Arc42 Documentation
        logger.info("=" * 60)
        logger.info("PHASE 3b: ARC42 CREW - Creating Deep arc42 Documentation (50+ pages)")
        logger.info("=" * 60)
        
        self.arc42_crew = Arc42Crew(
            facts_path=str(self.facts_path),
            analyzed_path=str(self.analyzed_path)
        )
        arc42_result = self.arc42_crew.run()
        results.append(f"Arc42 Crew Result:\n{arc42_result}")
        
        logger.info("Arc42 Crew completed")
        
        # Combined summary
        summary = "\n\n".join(results)
        logger.info("=" * 60)
        logger.info("PHASE 3 COMPLETE: Reverse Engineering Documentation created")
        logger.info("=" * 60)
        
        return summary
    
    def run_c4_only(self) -> str:
        """Run only the C4 Crew."""
        logger.info("Running C4 Crew only...")
        self.c4_crew = C4Crew(facts_path=str(self.facts_path))
        return self.c4_crew.run()
    
    def run_arc42_only(self) -> str:
        """Run only the Arc42 Crew."""
        logger.info("Running Arc42 Crew only...")
        self.arc42_crew = Arc42Crew(facts_path=str(self.facts_path))
        return self.arc42_crew.run()
    
    def kickoff(self, inputs: dict = None) -> str:
        """
        Execute crews - compatible with orchestrator interface.
        
        Args:
            inputs: Optional inputs dict (ignored, we use facts_path)
            
        Returns:
            Combined result summary.
        """
        return self.run()
