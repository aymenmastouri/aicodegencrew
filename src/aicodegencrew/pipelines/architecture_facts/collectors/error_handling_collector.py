"""
ErrorHandlingCollector - Extracts error handling patterns.

Thin router that delegates ecosystem-specific collection to specialist
collectors via the EcosystemRegistry.

Detects:
1. @ExceptionHandler methods with exception type
2. @ControllerAdvice / @RestControllerAdvice classes
3. Custom exception classes (extends RuntimeException, etc.)
4. ErrorResponse / HTTP status codes in handlers
5. Angular ErrorHandler, HTTP interceptors
6. Python custom exceptions, Flask errorhandler, Django middleware

Output -> error_handling dimension
"""

from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from .base import CollectorOutput, DimensionCollector


class ErrorHandlingCollector(DimensionCollector):
    """
    Extracts error handling facts.

    Delegates to ecosystem specialists:
    - spring/error_collector.py (Java @ExceptionHandler, @ControllerAdvice, custom exceptions)
    - angular/error_detail_collector.py (Angular ErrorHandler, HTTP interceptors)
    - python_eco/error_collector.py (Python exceptions, Flask errorhandler, Django middleware)
    """

    DIMENSION = "error_handling"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect error handling facts via ecosystem delegation."""
        self._log_start()

        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output
