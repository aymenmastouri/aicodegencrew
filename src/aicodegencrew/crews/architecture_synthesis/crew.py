"""
Architecture Synthesis — Phase 3
=================================
Generates C4 diagrams and arc42 documentation from architecture facts.

V2 Architecture: Pipeline + LLM Hybrid
- Deterministic data collection (no agents, no tool loops)
- Single LLM call per chapter (no iterations)
- Validation before write (structure, grounding, banned phrases)
- Retry with feedback (not blind retry)

Input:  architecture_facts.json (Phase 1) + analyzed_architecture.json (Phase 2)
Output: C4 diagrams (c4/*.md) + arc42 chapters (arc42/*.md) + quality report
"""

from pathlib import Path

from ...shared.utils.logger import setup_logger
from .pipeline import DocumentPipeline

logger = setup_logger(__name__)


class ArchitectureSynthesisCrew:
    """Phase 3 Orchestrator — delegates to DocumentPipeline.

    Maintains backward-compatible interface for the orchestrator
    (kickoff, run methods) while using the new pipeline internally.
    """

    def __init__(
        self,
        facts_path: str = "knowledge/extract/architecture_facts.json",
        analyzed_path: str | None = None,
        output_dir: str | None = None,
        chroma_dir: str | None = None,
    ):
        self.facts_path = Path(facts_path)
        if analyzed_path:
            self.analyzed_path = Path(analyzed_path)
        else:
            knowledge_base = self.facts_path.parent.parent
            self.analyzed_path = knowledge_base / "analyze" / "analyzed_architecture.json"
        self.output_dir = Path(output_dir) if output_dir else self.facts_path.parent.parent / "document"
        self.chroma_dir = chroma_dir

    def run(self, quality_context: dict | None = None) -> dict:
        """Execute document generation pipeline.

        Args:
            quality_context: Optional quality metrics from analyze phase (unused in V2,
                            kept for backward compatibility).

        Returns:
            Dict with status and result summary.
        """
        pipeline = DocumentPipeline(
            facts_path=self.facts_path,
            analyzed_path=self.analyzed_path,
            output_dir=self.output_dir,
            chroma_dir=self.chroma_dir,
        )

        result = pipeline.run()

        return {
            "status": result.status,
            "phase": "document",
            "result": result.to_dict(),
            "degradation_reasons": result.degradation_reasons,
        }

    def kickoff(self, inputs: dict | None = None) -> dict:
        """Execute — compatible with orchestrator PhaseExecutable interface.

        Args:
            inputs: Optional inputs dict from orchestrator.

        Returns:
            Dict with status and result.
        """
        inputs = inputs or {}
        previous = inputs.get("previous_results", {})
        analyze_out = previous.get("analyze", {})
        quality_context = analyze_out.get("quality_metrics", {}) if isinstance(analyze_out, dict) else {}
        return self.run(quality_context=quality_context)
