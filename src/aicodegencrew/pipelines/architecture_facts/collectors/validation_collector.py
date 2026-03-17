"""
ValidationCollector - Extracts validation rules from DTOs, entities, and custom validators.

Thin router that delegates ecosystem-specific collection to specialist
collectors via the EcosystemRegistry.

Detects:
- Bean Validation annotations: @Valid, @NotNull, @NotBlank, @Size, @Pattern, @Min, @Max
- Custom validators (implements ConstraintValidator<...>)
- DTO field -> validation rule mapping
- Angular form validators (Validators.required, Validators.pattern, etc.)
- Python validation: Pydantic, Marshmallow, Django Forms

Output -> validation dimension
"""

from pathlib import Path

from ....shared.ecosystems.registry import EcosystemRegistry
from .base import CollectorOutput, DimensionCollector


class ValidationCollector(DimensionCollector):
    """
    Extracts validation rule facts.

    Delegates to ecosystem specialists:
    - spring/validation_collector.py (Java Bean Validation, ConstraintValidator)
    - angular/validation_detail_collector.py (Angular Validators)
    - python_eco/validation_collector.py (Pydantic, Marshmallow, Django Forms)
    """

    DIMENSION = "validation"

    def __init__(self, repo_path: Path, container_id: str = ""):
        super().__init__(repo_path)
        self.container_id = container_id
        self._registry = EcosystemRegistry()

    def collect(self) -> CollectorOutput:
        """Collect validation facts via ecosystem delegation."""
        self._log_start()

        for eco in self._registry.detect(self.repo_path):
            facts, rels = eco.collect_dimension(self.DIMENSION, self.repo_path, self.container_id)
            for f in facts:
                self.output.add_fact(f)
            for r in rels:
                self.output.add_relation(r)

        self._log_end()
        return self.output
