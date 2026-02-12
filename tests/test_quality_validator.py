"""Tests for deterministic architecture facts validator."""

import json

import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory."""
    return tmp_path


def test_valid_facts_file(temp_dir):
    """Test validation of a valid facts file."""
    facts = {
        "containers": [{"id": "backend", "name": "Backend", "technology": "Spring Boot"}],
        "components": [
            {
                "id": "user_service",
                "name": "UserService",
                "container": "backend",
                "stereotype": "service",
                "evidence_ids": ["ev_001"],
            }
        ],
        "interfaces": [
            {
                "id": "if_001",
                "type": "REST",
                "path": "/api/users",
                "implemented_by": "user_service",
                "evidence_ids": ["ev_001"],
            }
        ],
        "relations": [{"from": "user_service", "to": "user_service", "type": "uses"}],
        "evidence": [{"id": "ev_001", "path": "src/UserService.java", "lines": "1-10", "reason": "Service annotation"}],
    }

    facts_path = temp_dir / "architecture_facts.json"
    with open(facts_path, "w") as f:
        json.dump(facts, f)

    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts(str(facts_path))

    assert result.is_valid is True
    assert result.stats["containers"] == 1
    assert result.stats["components"] == 1
    assert result.stats["errors"] == 0


def test_missing_required_fields(temp_dir):
    """Test validation fails for missing required fields."""
    facts = {
        "containers": [],
        # Missing: components, interfaces, relations, evidence
    }

    facts_path = temp_dir / "architecture_facts.json"
    with open(facts_path, "w") as f:
        json.dump(facts, f)

    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts(str(facts_path))

    assert result.is_valid is False
    assert any("Missing required field" in e.message for e in result.errors)


def test_duplicate_component_ids(temp_dir):
    """Test validation detects duplicate component IDs."""
    facts = {
        "containers": [{"id": "backend", "name": "Backend"}],
        "components": [
            {"id": "service_a", "name": "ServiceA", "container": "backend"},
            {"id": "service_a", "name": "ServiceA Duplicate", "container": "backend"},  # Duplicate!
        ],
        "interfaces": [],
        "relations": [],
        "evidence": [],
    }

    facts_path = temp_dir / "architecture_facts.json"
    with open(facts_path, "w") as f:
        json.dump(facts, f)

    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts(str(facts_path))

    assert result.is_valid is False
    assert any("Duplicate component id" in e.message for e in result.errors)


def test_invalid_relation_reference(temp_dir):
    """Test validation warns on invalid relation references."""
    facts = {
        "containers": [{"id": "backend", "name": "Backend"}],
        "components": [{"id": "service_a", "name": "ServiceA", "container": "backend"}],
        "interfaces": [],
        "relations": [
            {"from": "service_a", "to": "nonexistent_service", "type": "uses"}  # Invalid reference
        ],
        "evidence": [],
    }

    facts_path = temp_dir / "architecture_facts.json"
    with open(facts_path, "w") as f:
        json.dump(facts, f)

    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts(str(facts_path))

    assert any("unknown 'to' component" in w.message for w in result.warnings)


def test_invalid_evidence_reference(temp_dir):
    """Test validation warns on invalid evidence references."""
    facts = {
        "containers": [{"id": "backend", "name": "Backend"}],
        "components": [
            {
                "id": "service_a",
                "name": "ServiceA",
                "container": "backend",
                "evidence_ids": ["ev_999"],
            }  # Invalid evidence
        ],
        "interfaces": [],
        "relations": [],
        "evidence": [{"id": "ev_001", "path": "src/test.java", "lines": "1-10"}],
    }

    facts_path = temp_dir / "architecture_facts.json"
    with open(facts_path, "w") as f:
        json.dump(facts, f)

    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts(str(facts_path))

    assert any("unknown evidence" in w.message for w in result.warnings)


def test_file_not_found():
    """Test validation handles missing file."""
    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts("/nonexistent/path/facts.json")

    assert result.is_valid is False
    assert any("File not found" in e.message for e in result.errors)


def test_invalid_json(temp_dir):
    """Test validation handles invalid JSON."""
    facts_path = temp_dir / "architecture_facts.json"
    with open(facts_path, "w") as f:
        f.write("{ invalid json }")

    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts(str(facts_path))

    assert result.is_valid is False
    assert any("Invalid JSON" in e.message for e in result.errors)


def test_duplicate_relations_warning(temp_dir):
    """Test validation warns on duplicate relations."""
    facts = {
        "containers": [{"id": "backend", "name": "Backend"}],
        "components": [
            {"id": "service_a", "name": "ServiceA", "container": "backend"},
            {"id": "service_b", "name": "ServiceB", "container": "backend"},
        ],
        "interfaces": [],
        "relations": [
            {"from": "service_a", "to": "service_b", "type": "uses"},
            {"from": "service_a", "to": "service_b", "type": "uses"},  # Duplicate!
        ],
        "evidence": [],
    }

    facts_path = temp_dir / "architecture_facts.json"
    with open(facts_path, "w") as f:
        json.dump(facts, f)

    from src.aicodegencrew.pipelines.architecture_facts.quality_validator import validate_architecture_facts

    result = validate_architecture_facts(str(facts_path))

    assert any("Duplicate relation" in w.message for w in result.warnings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
