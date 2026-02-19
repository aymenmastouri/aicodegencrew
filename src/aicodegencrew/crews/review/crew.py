"""Phase 7: Review and Consistency Guard Crew.

Validates consistency across:
- architecture_facts.json vs C4 diagrams
- architecture_facts.json vs arc42 documentation
- Cross-references between documents

Status: PLANNED - not yet implemented.

ARCH-1 fix: kickoff() now returns a proper status dict instead of raising
NotImplementedError, so the orchestrator can handle the 'not_implemented'
status gracefully rather than crashing the pipeline.
"""

from pathlib import Path
from typing import Any


class ReviewCrew:
    """Review and Consistency Guard Crew.

    Agents:
    - Consistency Validator: Cross-reference facts with outputs
    - Quality Auditor: Check documentation completeness
    - Report Generator: Generate quality reports
    """

    def __init__(self, knowledge_path: Path):
        self.knowledge_path = Path(knowledge_path)
        self.facts_path = self.knowledge_path / "architecture_facts.json"
        self.c4_path = self.knowledge_path / "c4"
        self.arc42_path = self.knowledge_path / "arc42"
        self.output_path = self.knowledge_path / "quality"

    def run(self) -> dict[str, Any]:
        """Execute the review crew.

        Returns:
            Dict with review results and quality metrics
        """
        raise NotImplementedError(
            "Phase 7 (Review & Deploy) is planned but not yet implemented. "
            "Use kickoff() via the orchestrator instead, which returns a "
            "'not_implemented' status so the pipeline continues gracefully."
        )

    def kickoff(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Orchestrator-compatible kickoff interface.

        Returns a 'not_implemented' status dict so the orchestrator handles this
        gracefully rather than raising an exception and crashing the pipeline.
        """
        return {
            "status": "skipped",
            "phase": "deliver",
            "message": (
                "Review & Deploy (Phase 7) is not yet implemented. "
                "Skipping this phase."
            ),
        }

    def _create_agents(self):
        """Create review agents."""
        # TODO: Implement agents
        pass

    def _create_tasks(self):
        """Create review tasks."""
        # TODO: Implement tasks
        pass
