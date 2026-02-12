"""Deterministic Quality Validator for Architecture Facts.

Validates architecture_facts.json against schema and consistency rules.
NO LLM needed - pure deterministic checks.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationError:
    """A single validation error."""

    severity: str  # "error", "warning", "info"
    category: str  # "schema", "consistency", "completeness"
    message: str
    location: str = ""


@dataclass
class ValidationResult:
    """Result of validation."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)


class ArchitectureFactsValidator:
    """Deterministic validator for architecture facts JSON.

    Performs:
    1. Schema validation (required fields, types)
    2. Consistency checks (references exist)
    3. Completeness checks (no empty sections)
    4. Evidence validation (all evidence_ids exist)
    """

    def __init__(self, facts_path: Path):
        self.facts_path = Path(facts_path)
        self.facts: dict = {}
        self.evidence: dict = {}
        self.errors: list[ValidationError] = []
        self.warnings: list[ValidationError] = []

    def validate(self) -> ValidationResult:
        """Run all validations and return result."""
        self.errors = []
        self.warnings = []

        # Load files
        if not self._load_facts():
            return ValidationResult(is_valid=False, errors=self.errors, warnings=self.warnings, stats={})

        # Run validations
        self._validate_schema()
        self._validate_containers()
        self._validate_components()
        self._validate_interfaces()
        self._validate_relations()
        self._validate_evidence_references()
        self._validate_completeness()

        # Collect stats
        stats = self._collect_stats()

        is_valid = len([e for e in self.errors if e.severity == "error"]) == 0

        return ValidationResult(is_valid=is_valid, errors=self.errors, warnings=self.warnings, stats=stats)

    def _load_facts(self) -> bool:
        """Load architecture facts JSON."""
        try:
            with open(self.facts_path, encoding="utf-8") as f:
                self.facts = json.load(f)

            # Load evidence map if exists
            evidence_path = self.facts_path.parent / "evidence_map.json"
            if evidence_path.exists():
                with open(evidence_path, encoding="utf-8") as f:
                    self.evidence = json.load(f)

            return True
        except FileNotFoundError:
            self.errors.append(
                ValidationError(
                    severity="error",
                    category="schema",
                    message=f"File not found: {self.facts_path}",
                    location=str(self.facts_path),
                )
            )
            return False
        except json.JSONDecodeError as e:
            self.errors.append(
                ValidationError(
                    severity="error", category="schema", message=f"Invalid JSON: {e}", location=str(self.facts_path)
                )
            )
            return False

    def _validate_schema(self):
        """Validate required top-level fields."""
        required_fields = ["containers", "components", "interfaces", "relations", "evidence"]

        for field_name in required_fields:
            if field_name not in self.facts:
                self.errors.append(
                    ValidationError(
                        severity="error",
                        category="schema",
                        message=f"Missing required field: {field_name}",
                        location="root",
                    )
                )
            elif not isinstance(self.facts.get(field_name), list):
                self.errors.append(
                    ValidationError(
                        severity="error",
                        category="schema",
                        message=f"Field '{field_name}' must be an array",
                        location="root",
                    )
                )

    def _validate_containers(self):
        """Validate container entries."""
        containers = self.facts.get("containers", [])
        container_ids = set()

        for i, container in enumerate(containers):
            loc = f"containers[{i}]"

            # Required fields
            if not container.get("id"):
                self.errors.append(
                    ValidationError(
                        severity="error", category="schema", message="Container missing 'id' field", location=loc
                    )
                )
            else:
                if container["id"] in container_ids:
                    self.errors.append(
                        ValidationError(
                            severity="error",
                            category="consistency",
                            message=f"Duplicate container id: {container['id']}",
                            location=loc,
                        )
                    )
                container_ids.add(container["id"])

            if not container.get("name"):
                self.warnings.append(
                    ValidationError(
                        severity="warning",
                        category="completeness",
                        message=f"Container {container.get('id')} missing 'name'",
                        location=loc,
                    )
                )

    def _validate_components(self):
        """Validate component entries."""
        components = self.facts.get("components", [])
        component_ids = set()
        container_ids = {c.get("id") for c in self.facts.get("containers", [])}

        for i, comp in enumerate(components):
            loc = f"components[{i}]"

            # Required fields
            if not comp.get("id"):
                self.errors.append(
                    ValidationError(
                        severity="error", category="schema", message="Component missing 'id' field", location=loc
                    )
                )
            else:
                if comp["id"] in component_ids:
                    self.errors.append(
                        ValidationError(
                            severity="error",
                            category="consistency",
                            message=f"Duplicate component id: {comp['id']}",
                            location=loc,
                        )
                    )
                component_ids.add(comp["id"])

            if not comp.get("name"):
                self.warnings.append(
                    ValidationError(
                        severity="warning",
                        category="completeness",
                        message=f"Component {comp.get('id')} missing 'name'",
                        location=loc,
                    )
                )

            # Container reference check
            container = comp.get("container")
            if container and container not in container_ids:
                self.warnings.append(
                    ValidationError(
                        severity="warning",
                        category="consistency",
                        message=f"Component {comp.get('id')} references unknown container: {container}",
                        location=loc,
                    )
                )

    def _validate_interfaces(self):
        """Validate interface entries."""
        interfaces = self.facts.get("interfaces", [])
        component_ids = {c.get("id") for c in self.facts.get("components", [])}

        for i, iface in enumerate(interfaces):
            loc = f"interfaces[{i}]"

            if not iface.get("id"):
                self.errors.append(
                    ValidationError(
                        severity="error", category="schema", message="Interface missing 'id' field", location=loc
                    )
                )

            # Check implemented_by reference
            impl_by = iface.get("implemented_by")
            if impl_by and impl_by not in component_ids:
                self.warnings.append(
                    ValidationError(
                        severity="warning",
                        category="consistency",
                        message=f"Interface {iface.get('id')} implemented_by unknown component: {impl_by}",
                        location=loc,
                    )
                )

    def _validate_relations(self):
        """Validate relation entries."""
        relations = self.facts.get("relations", [])
        component_ids = {c.get("id") for c in self.facts.get("components", [])}

        relation_set = set()

        for i, rel in enumerate(relations):
            loc = f"relations[{i}]"

            from_id = rel.get("from")
            to_id = rel.get("to")

            if not from_id:
                self.errors.append(
                    ValidationError(
                        severity="error", category="schema", message="Relation missing 'from' field", location=loc
                    )
                )

            if not to_id:
                self.errors.append(
                    ValidationError(
                        severity="error", category="schema", message="Relation missing 'to' field", location=loc
                    )
                )

            # Check for duplicates
            rel_key = (from_id, to_id, rel.get("type", "uses"))
            if rel_key in relation_set:
                self.warnings.append(
                    ValidationError(
                        severity="warning",
                        category="consistency",
                        message=f"Duplicate relation: {from_id} -> {to_id}",
                        location=loc,
                    )
                )
            relation_set.add(rel_key)

            # Check references exist
            if from_id and from_id not in component_ids:
                self.warnings.append(
                    ValidationError(
                        severity="warning",
                        category="consistency",
                        message=f"Relation references unknown 'from' component: {from_id}",
                        location=loc,
                    )
                )

            if to_id and to_id not in component_ids:
                self.warnings.append(
                    ValidationError(
                        severity="warning",
                        category="consistency",
                        message=f"Relation references unknown 'to' component: {to_id}",
                        location=loc,
                    )
                )

    def _validate_evidence_references(self):
        """Validate that all evidence_ids references exist."""
        evidence_ids = {e.get("id") for e in self.facts.get("evidence", [])}

        # Check components
        for comp in self.facts.get("components", []):
            for eid in comp.get("evidence_ids", []):
                if eid not in evidence_ids:
                    self.warnings.append(
                        ValidationError(
                            severity="warning",
                            category="consistency",
                            message=f"Component {comp.get('id')} references unknown evidence: {eid}",
                            location=f"component:{comp.get('id')}",
                        )
                    )

        # Check interfaces
        for iface in self.facts.get("interfaces", []):
            for eid in iface.get("evidence_ids", []):
                if eid not in evidence_ids:
                    self.warnings.append(
                        ValidationError(
                            severity="warning",
                            category="consistency",
                            message=f"Interface {iface.get('id')} references unknown evidence: {eid}",
                            location=f"interface:{iface.get('id')}",
                        )
                    )

    def _validate_completeness(self):
        """Check for completeness issues."""
        # Check for empty sections
        if not self.facts.get("containers"):
            self.warnings.append(
                ValidationError(
                    severity="warning", category="completeness", message="No containers detected", location="containers"
                )
            )

        if not self.facts.get("components"):
            self.warnings.append(
                ValidationError(
                    severity="warning", category="completeness", message="No components detected", location="components"
                )
            )

        # Check for orphan components (no relations)
        component_ids = {c.get("id") for c in self.facts.get("components", [])}
        related_ids = set()

        for rel in self.facts.get("relations", []):
            related_ids.add(rel.get("from"))
            related_ids.add(rel.get("to"))

        orphans = component_ids - related_ids
        if len(orphans) > len(component_ids) * 0.5:  # More than 50% orphans
            self.warnings.append(
                ValidationError(
                    severity="warning",
                    category="completeness",
                    message=f"Many components have no relations ({len(orphans)}/{len(component_ids)})",
                    location="relations",
                )
            )

    def _collect_stats(self) -> dict[str, Any]:
        """Collect statistics about the facts."""
        return {
            "containers": len(self.facts.get("containers", [])),
            "components": len(self.facts.get("components", [])),
            "interfaces": len(self.facts.get("interfaces", [])),
            "relations": len(self.facts.get("relations", [])),
            "evidence": len(self.facts.get("evidence", [])),
            "errors": len([e for e in self.errors if e.severity == "error"]),
            "warnings": len([e for e in self.warnings if e.severity == "warning"]),
        }


def validate_architecture_facts(facts_path: str) -> ValidationResult:
    """Convenience function to validate architecture facts."""
    validator = ArchitectureFactsValidator(Path(facts_path))
    return validator.validate()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python quality_validator.py <path-to-architecture_facts.json>")
        sys.exit(1)

    result = validate_architecture_facts(sys.argv[1])

    print(f"\n{'=' * 60}")
    print("ARCHITECTURE FACTS VALIDATION REPORT")
    print(f"{'=' * 60}")
    print(f"Status: {'[VALID]' if result.is_valid else '[INVALID]'}")
    print("\nStats:")
    for key, value in result.stats.items():
        print(f"  {key}: {value}")

    if result.errors:
        print(f"\n[ERROR] Errors ({len(result.errors)}):")
        for err in result.errors[:10]:
            print(f"  - [{err.category}] {err.message}")
            if err.location:
                print(f"    at {err.location}")

    if result.warnings:
        print(f"\n[WARN] Warnings ({len(result.warnings)}):")
        for warn in result.warnings[:10]:
            print(f"  - [{warn.category}] {warn.message}")

    sys.exit(0 if result.is_valid else 1)
