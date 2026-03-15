"""
Architecture Synthesis — Phase 3
=================================
Thin wrapper around DocumentPipeline for backward compatibility.
The actual implementation lives in pipelines/document/.
"""

from pathlib import Path

from ...pipelines.document import DocumentPipeline
from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


class ArchitectureSynthesisCrew:
    """Phase 3 Orchestrator — delegates to DocumentPipeline.

    Maintains backward-compatible interface for the orchestrator
    (kickoff, run methods) while using the pipeline internally.
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
        """Execute document generation pipeline."""
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
        """Execute — compatible with orchestrator PhaseExecutable interface."""
        inputs = inputs or {}
        previous = inputs.get("previous_results", {})
        analyze_out = previous.get("analyze", {})
        quality_context = analyze_out.get("quality_metrics", {}) if isinstance(analyze_out, dict) else {}
        return self.run(quality_context=quality_context)
