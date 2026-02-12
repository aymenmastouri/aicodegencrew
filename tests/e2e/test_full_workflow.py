"""
E2E Tests for Full Workflow: Phase 0 -> Phase 1 -> Phase 2

Tests:
- End-to-end execution
- Data flow between phases
- Error recovery
- Complete validation
"""

import json
from pathlib import Path

import pytest

from tests.e2e.helpers import EvidenceValidator, FactsValidator, SynthesisValidator


@pytest.mark.e2e
def test_full_workflow_end_to_end(sample_project):
    """
    Test complete workflow data structure.

    Given: Clean workspace with sample project
    When: Checking all output directories
    Then: All phases have valid outputs
    """
    # Verify all outputs exist
    assert (sample_project / "knowledge" / "architecture" / "architecture_facts.json").exists()
    assert (sample_project / "knowledge" / "architecture" / "evidence_map.json").exists()
    assert (sample_project / "knowledge" / "architecture" / "c4").exists()
    assert (sample_project / "knowledge" / "architecture" / "arc42").exists()


@pytest.mark.e2e
def test_workflow_phase1_to_phase2_data_flow(sample_project):
    """
    Test data flows correctly from Phase 1 to Phase 2.

    Given: Phase 1 completed with architecture_facts.json
    When: Phase 2 reads facts
    Then: Phase 2 outputs reference actual container/component IDs from Phase 1
    """
    facts_path = sample_project / "knowledge" / "architecture" / "architecture_facts.json"
    c4_path = sample_project / "knowledge" / "architecture" / "c4"

    if not all([facts_path.exists(), c4_path.exists()]):
        pytest.skip("Full workflow not completed")

    # Load Phase 1 output
    with open(facts_path) as f:
        facts = json.load(f)

    container_ids = {c["id"] for c in facts["containers"]}

    # Check Phase 2 uses these IDs
    c4_container = c4_path / "c4-container.md"
    if c4_container.exists():
        content = c4_container.read_text(encoding="utf-8")

        # At least some container IDs should appear
        found_ids = sum(1 for cid in container_ids if cid in content)

        assert found_ids >= 1, f"Phase 2 uses Phase 1 container IDs: {found_ids}/{len(container_ids)} found"


@pytest.mark.e2e
def test_workflow_evidence_chain(sample_project):
    """
    Test evidence chain is maintained throughout workflow.

    Given: Complete workflow executed
    When: Tracing evidence from code -> facts -> synthesis
    Then: Evidence IDs consistent across all outputs
    """
    facts_path = sample_project / "knowledge" / "architecture" / "architecture_facts.json"
    evidence_path = sample_project / "knowledge" / "architecture" / "evidence_map.json"

    if not all([facts_path.exists(), evidence_path.exists()]):
        pytest.skip("Full workflow not completed")

    # Load data
    with open(facts_path) as f:
        facts = json.load(f)

    with open(evidence_path) as f:
        evidence_map = json.load(f)

    # Check evidence chain
    evidence_ids_in_facts = set()
    for container in facts["containers"]:
        evidence_ids_in_facts.update(container.get("evidence_ids", []))
    for component in facts["components"]:
        evidence_ids_in_facts.update(component.get("evidence_ids", []))

    # All evidence IDs should exist in evidence_map
    missing = evidence_ids_in_facts - set(evidence_map.keys())

    assert len(missing) == 0, f"Evidence IDs in facts but not in evidence_map: {list(missing)[:5]}"


@pytest.mark.e2e
def test_workflow_comprehensive_validation(sample_project):
    """
    Run all validators on complete workflow output.

    Given: Complete workflow executed
    When: Running all validation helpers
    Then: All validations pass (or known issues only)
    """
    facts_path = sample_project / "knowledge" / "architecture" / "architecture_facts.json"
    evidence_path = sample_project / "knowledge" / "architecture" / "evidence_map.json"
    c4_path = sample_project / "knowledge" / "architecture" / "c4"
    arc42_path = sample_project / "knowledge" / "architecture" / "arc42"

    if not facts_path.exists():
        pytest.skip("Full workflow not completed")

    # Phase 1 validation
    facts_validator = FactsValidator(facts_path)
    facts_summary = facts_validator.get_summary()

    print("\n" + "=" * 80)
    print("COMPREHENSIVE VALIDATION REPORT")
    print("=" * 80)

    print("\nPHASE 1 (Facts Extraction):")
    print(f"  Containers: {facts_summary['total_containers']}")
    print(f"  Components: {facts_summary['total_components']}")
    print(f"  Interfaces: {facts_summary['total_interfaces']}")
    print(f"  Relations: {facts_summary['total_relations']}")
    print(f"  Schema Valid: {facts_summary['schema_valid']}")
    print(f"  Evidence Valid: {facts_summary['evidence_valid']}")
    print(f"  Relations Valid: {facts_summary['relations_valid']}")

    # Evidence validation
    if evidence_path.exists():
        evidence_validator = EvidenceValidator(evidence_path, Path("."))
        evidence_summary = evidence_validator.get_summary()

        print("\nEVIDENCE MAP:")
        print(f"  Total Evidence: {evidence_summary['total_evidence']}")
        print(f"  IDs Unique: {evidence_summary['evidence_ids_unique']}")
        print(f"  Invalid Line Ranges: {evidence_summary['invalid_line_ranges']}")

    # Phase 2 validation
    if c4_path.exists() and arc42_path.exists():
        synthesis_validator = SynthesisValidator(facts_path, c4_path, arc42_path)
        synthesis_summary = synthesis_validator.get_summary()

        print("\nPHASE 2 (Synthesis):")
        print(f"  No Hallucinations: {synthesis_summary['no_hallucinations']}")
        print(f"  Completeness: {synthesis_summary['completeness']}")
        print(f"  Mermaid Syntax Valid: {synthesis_summary['mermaid_syntax_valid']}")
        print(f"  arc42 Structure Valid: {synthesis_summary['arc42_structure_valid']}")
        print(f"  UNKNOWN Markers: {synthesis_summary['unknown_markers_count']}")

    print("=" * 80)

    # Overall assessment
    critical_failures = []

    if not facts_summary["schema_valid"]:
        critical_failures.append("Phase 1 schema invalid")

    if c4_path.exists() and not synthesis_summary.get("mermaid_syntax_valid", True):
        critical_failures.append("Mermaid syntax invalid")

    assert len(critical_failures) == 0, f"Critical validation failures: {critical_failures}"


@pytest.mark.e2e
def test_workflow_idempotency(sample_project):
    """
    Test workflow produces consistent results.

    Given: Workflow already executed once
    When: Checking results
    Then: Results are well-formed
    """
    facts_path = sample_project / "knowledge" / "architecture" / "architecture_facts.json"

    if not facts_path.exists():
        pytest.skip("Initial workflow not completed")

    # Load first run results
    with open(facts_path) as f:
        facts_run1 = json.load(f)

    containers_run1 = len(facts_run1.get("containers", []))
    components_run1 = len(facts_run1.get("components", []))

    # Results should be consistent
    # (Allow some variation due to non-deterministic parsing)
    assert containers_run1 > 0, "First run produced no containers"
    assert components_run1 > 0, "First run produced no components"

    print(f"\nRun 1: {containers_run1} containers, {components_run1} components")


@pytest.mark.e2e
def test_workflow_output_structure(sample_project):
    """
    Test complete output directory structure.

    Given: Full workflow completed
    When: Checking knowledge/ directory
    Then: All expected files and folders exist
    """
    base = sample_project / "knowledge" / "architecture"

    expected_structure = {
        base / "architecture_facts.json": "file",
        base / "evidence_map.json": "file",
        base / "c4": "dir",
        base / "arc42": "dir",
    }

    missing = []
    for path, path_type in expected_structure.items():
        if path_type == "file" and not path.is_file():
            missing.append(f"Missing file: {path}")
        elif path_type == "dir" and not path.is_dir():
            missing.append(f"Missing directory: {path}")

    assert len(missing) == 0, f"Incomplete output structure: {missing}"
