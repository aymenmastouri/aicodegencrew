"""
SecurityDetailCollector - Extracts method-level security, CSRF/CORS configuration.

Thin router that delegates ecosystem-specific collection to specialist
collectors via the EcosystemRegistry.

Detects:
- @PreAuthorize("hasRole('...')"), @Secured, @RolesAllowed with roles
- Method-level security mapping: Controller method -> required role
- CSRF/CORS configuration from SecurityConfig
- Angular route guards
- Python security decorators and permission classes

Output -> security_details dimension
"""

from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from .base import CollectorOutput, DimensionCollector


class SecurityDetailCollector(DimensionCollector):
    """
    Extracts detailed security facts.

    Delegates to ecosystem specialists:
    - spring/security_detail_collector.py (Java @PreAuthorize, @Secured, CSRF/CORS)
    - angular/security_detail_collector.py (Angular route guards)
    - python_eco/security_collector.py (Django, Flask, FastAPI, DRF)
    """

    DIMENSION = "security_details"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect security detail facts via ecosystem delegation."""
        self._log_start()

        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output
