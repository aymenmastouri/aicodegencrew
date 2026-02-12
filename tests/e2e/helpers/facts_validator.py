"""
Validator for architecture_facts.json.

Validates:
- JSON schema structure
- Evidence integrity (all facts have evidence IDs)
- ID uniqueness (no duplicates)
- Relation consistency (all referenced IDs exist)
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any


class FactsValidator:
    """Validate architecture_facts.json structure and integrity."""

    def __init__(self, facts_path: str | Path):
        """
        Initialize validator.

        Args:
            facts_path: Path to architecture_facts.json
        """
        self.facts_path = Path(facts_path)
        self.facts = self._load_facts()

    def _load_facts(self) -> dict[str, Any]:
        """Load and parse facts JSON."""
        if not self.facts_path.exists():
            raise FileNotFoundError(f"Facts file not found: {self.facts_path}")

        with open(self.facts_path, encoding="utf-8") as f:
            return json.load(f)

    def validate_schema(self) -> bool:
        """
        Validate JSON schema structure.

        Returns:
            True if schema is valid

        Raises:
            AssertionError: If schema validation fails
        """
        # Required top-level keys
        required_keys = {"system", "containers", "components", "interfaces", "relations"}
        actual_keys = set(self.facts.keys())
        assert required_keys.issubset(actual_keys), f"Missing required keys: {required_keys - actual_keys}"

        # System validation
        system = self.facts["system"]
        assert "name" in system, "System must have 'name'"
        assert "domain" in system, "System must have 'domain'"

        # Containers validation
        containers = self.facts["containers"]
        assert isinstance(containers, list), "Containers must be a list"
        for container in containers:
            assert "id" in container, "Container must have 'id'"
            assert "name" in container, "Container must have 'name'"
            assert "stereotype" in container, "Container must have 'stereotype'"

        # Components validation
        components = self.facts["components"]
        assert isinstance(components, list), "Components must be a list"
        for component in components:
            assert "id" in component, "Component must have 'id'"
            assert "name" in component, "Component must have 'name'"
            assert "container" in component, "Component must have 'container'"

        return True

    def validate_evidence_integrity(self) -> bool:
        """
        Validate all facts have evidence IDs.

        Returns:
            True if all facts have evidence

        Raises:
            AssertionError: If facts without evidence found
        """
        facts_without_evidence = []

        # Check containers
        for container in self.facts["containers"]:
            if not container.get("evidence_ids"):
                facts_without_evidence.append(f"Container: {container.get('id')}")

        # Check components
        for component in self.facts["components"]:
            if not component.get("evidence_ids"):
                facts_without_evidence.append(f"Component: {component.get('id')}")

        # Check interfaces
        for interface in self.facts["interfaces"]:
            if not interface.get("evidence_ids"):
                facts_without_evidence.append(f"Interface: {interface.get('id')}")

        assert not facts_without_evidence, f"Facts without evidence: {facts_without_evidence}"

        return True

    def find_duplicate_ids(self) -> dict[str, list[str]]:
        """
        Find duplicate component IDs.

        Returns:
            Dict mapping duplicate IDs to their counts
        """
        all_ids = []

        # Collect all IDs
        for container in self.facts["containers"]:
            all_ids.append(("container", container.get("id")))

        for component in self.facts["components"]:
            all_ids.append(("component", component.get("id")))

        # Find duplicates
        id_counts = Counter([id_tuple[1] for id_tuple in all_ids])
        duplicates = {id_: count for id_, count in id_counts.items() if count > 1}

        return duplicates

    def validate_relations(self) -> tuple[bool, list[str]]:
        """
        Validate all relation IDs reference existing components.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Collect all valid component IDs
        valid_ids = set()
        for container in self.facts["containers"]:
            valid_ids.add(container.get("id"))
        for component in self.facts["components"]:
            valid_ids.add(component.get("id"))

        # Check relations
        for relation in self.facts["relations"]:
            source = relation.get("source")
            target = relation.get("target")

            if not source:
                errors.append(f"Relation has empty source: {relation}")
            elif source not in valid_ids:
                errors.append(f"Relation source not found: {source}")

            if not target:
                errors.append(f"Relation has empty target: {relation}")
            elif target not in valid_ids:
                errors.append(f"Relation target not found: {target}")

        return (len(errors) == 0, errors)

    def get_summary(self) -> dict[str, Any]:
        """
        Get validation summary statistics.

        Returns:
            Dict with counts and validation results
        """
        return {
            "total_containers": len(self.facts["containers"]),
            "total_components": len(self.facts["components"]),
            "total_interfaces": len(self.facts["interfaces"]),
            "total_relations": len(self.facts["relations"]),
            "duplicate_ids": self.find_duplicate_ids(),
            "schema_valid": self.validate_schema(),
            "evidence_valid": self.validate_evidence_integrity(),
            "relations_valid": self.validate_relations()[0],
        }
