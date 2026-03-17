"""
RuntimeCollector - Extracts runtime behavior facts.

Thin router that delegates ecosystem-specific collection to specialist
collectors via the EcosystemRegistry.

Detects:
- Background jobs
- Schedulers
- Async operations
- Workflow triggers
- Event handlers

Output -> runtime.json
"""

from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from .base import CollectorOutput, DimensionCollector


class RuntimeCollector(DimensionCollector):
    """
    Extracts runtime behavior facts.

    Delegates to ecosystem specialists:
    - spring/runtime_collector.py (Java @Scheduled, @Async, @EventListener, Batch)
    - python_eco/runtime_collector.py (Celery, APScheduler)
    """

    DIMENSION = "runtime"

    def __init__(self, repo_path: Path, container_id: str = "backend"):
        super().__init__(repo_path)
        self.container_id = container_id
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect runtime behavior facts via ecosystem delegation."""
        self._log_start()

        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output
