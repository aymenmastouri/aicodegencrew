"""
Architecture Synthesis Crew - Phase 2
=====================================
Orchestrates two sub-crews for reverse engineering documentation:

REVERSE ENGINEERING APPROACH:
- Input: architecture_facts.json + evidence_map.json + ChromaDB Index
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
    Architecture Synthesis Crew - Phase 2 Orchestrator.
    
    Reverse Engineering Documentation:
    1. C4 Crew - Creates 4 C4 diagrams with DrawIO files  
    2. Arc42 Crew - Creates 12 arc42 chapters (50+ pages)
    
    Data Sources:
    - architecture_facts.json: Components, relations, interfaces, containers
    - evidence_map.json: Code snippets and file references
    - ChromaDB Index: Semantic search for specific patterns
    """
    
    def __init__(self, facts_path: str = "knowledge/architecture/architecture_facts.json"):
        """Initialize orchestrator with architecture facts path."""
        self.facts_path = Path(facts_path)
        self.evidence_path = self.facts_path.parent / "evidence_map.json"
        self.c4_crew = None
        self.arc42_crew = None
        # Note: Validation happens at kickoff(), not here (allows Phase 1 to run first)
    
    def _validate_prerequisites(self):
        """Validate that Phase 1 output files exist before running Phase 2."""
        logger.info("")
        logger.info("[Phase2] Checking Phase 1 prerequisites...")
        
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
        logger.info("")
    
    def run(self) -> str:
        """
        Execute both crews sequentially.
        
        Sequence:
        1. C4: Facts -> 4 C4 diagrams + DrawIO
        2. Arc42: Facts -> 12 deep chapters (50+ pages)
        
        Returns combined result summary.
        """
        # Validate prerequisites before running
        self._validate_prerequisites()
        
        results = []
        
        # Phase 2a: C4 Diagrams
        logger.info("=" * 60)
        logger.info("PHASE 2a: C4 CREW - Creating C4 Diagrams + DrawIO")
        logger.info("=" * 60)
        
        self.c4_crew = C4Crew(facts_path=str(self.facts_path))
        c4_result = self.c4_crew.run()
        results.append(f"C4 Crew Result:\n{c4_result}")
        
        logger.info("C4 Crew completed")
        
        # Phase 2b: Arc42 Documentation
        logger.info("=" * 60)
        logger.info("PHASE 2b: ARC42 CREW - Creating Deep arc42 Documentation (50+ pages)")
        logger.info("=" * 60)
        
        self.arc42_crew = Arc42Crew(facts_path=str(self.facts_path))
        arc42_result = self.arc42_crew.run()
        results.append(f"Arc42 Crew Result:\n{arc42_result}")
        
        logger.info("Arc42 Crew completed")
        
        # Combined summary
        summary = "\n\n".join(results)
        logger.info("=" * 60)
        logger.info("PHASE 2 COMPLETE: Reverse Engineering Documentation created")
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
