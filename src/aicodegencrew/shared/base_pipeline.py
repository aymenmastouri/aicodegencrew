"""BasePipeline — abstract base class for all deterministic pipelines.

Every pipeline follows the same contract:
    collect data → build prompt → LLM call → validate → persist → return result
"""

from abc import ABC, abstractmethod


class BasePipeline(ABC):
    """Abstract base for all Pipeline implementations.

    Subclasses must implement ``run()`` which orchestrates the full
    data-collect → prompt-build → LLM-generate → validate → persist flow.

    Returns a result dict that always contains at minimum:
        ``{"status": "success|partial|failed", "phase": "<phase_name>"}``
    """

    @abstractmethod
    def run(self) -> dict:
        """Execute the pipeline and return a status dict.

        Returns:
            Dict with at minimum ``status`` ("success", "partial", "failed")
            and ``phase`` keys.  Pipelines may add extra keys.
        """

    def kickoff(self, inputs: dict | None = None) -> dict:
        """Orchestrator-compatible entry point — delegates to run().

        The SDLCOrchestrator calls kickoff() on all registered phases.
        Pipelines that need inputs should override __init__ instead of
        using the inputs parameter here.
        """
        return self.run()
