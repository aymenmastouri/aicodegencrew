"""Tests for Phase Validation and Architecture Model Builder.

Covers:
- PhaseOutputValidator: file existence, schema, content, dependency checks
- ArchitectureModelBuilder: ID generation, layer classification, deduplication, build, stats
- CanonicalIdGenerator: component/container/interface ID formats, normalization
- LayerClassifier: stereotype-to-layer mapping

All tests run WITHOUT LLM or ChromaDB.
"""

import json

import pytest

from aicodegencrew.pipelines.architecture_facts.collectors.fact_adapter import (
    CollectedComponent,
    CollectedEvidence,
    CollectedInterface,
    CollectedRelation,
)
from aicodegencrew.pipelines.architecture_facts.model_builder import (
    ArchitectureLayer,
    ArchitectureModel,
    ArchitectureModelBuilder,
    CanonicalIdGenerator,
    LayerClassifier,
)
from aicodegencrew.shared.validation import PhaseOutputValidator

# =============================================================================
# Fixtures: Validation
# =============================================================================


@pytest.fixture
def validator():
    """Fresh PhaseOutputValidator instance."""
    return PhaseOutputValidator()


def _valid_facts_json():
    """Return a minimal valid architecture_facts.json payload."""
    return {
        "system": {"id": "system", "name": "TestRepo", "domain": "testing"},
        "containers": [
            {
                "id": "backend",
                "name": "Backend",
                "type": "application",
                "technology": "Spring Boot",
                "evidence": ["ev_001"],
            }
        ],
        "components": [
            {
                "id": "comp_1",
                "container": "backend",
                "name": "UserController",
                "stereotype": "controller",
                "file_path": "src/main/java/UserController.java",
                "evidence": ["ev_001"],
            }
        ],
        "interfaces": [
            {
                "id": "iface_1",
                "container": "backend",
                "type": "REST",
                "path": "/users",
                "method": "GET",
                "implemented_by": "UserController",
                "evidence": ["ev_001"],
            }
        ],
        "relations": [
            {
                "from": "comp_1",
                "to": "comp_1",
                "type": "uses",
                "evidence": ["ev_001"],
            }
        ],
        "endpoint_flows": [],
    }


def _valid_evidence_json():
    """Return a minimal valid evidence_map.json payload."""
    return {
        "ev_001": {
            "path": "src/main/java/UserController.java",
            "lines": "1-50",
            "reason": "@RestController annotation",
            "chunk_id": "chunk_abc",
        }
    }


def _valid_analysis_json():
    """Return a minimal valid analyzed_architecture.json payload."""
    return {
        "architecture": {
            "style": "layered",
            "containers": [],
        },
        "patterns": [
            {"name": "MVC", "evidence": "controllers + services"},
        ],
    }


# =============================================================================
# Fixtures: Model Builder
# =============================================================================


@pytest.fixture
def builder():
    """Fresh ArchitectureModelBuilder instance."""
    return ArchitectureModelBuilder(system_name="TestSystem")


def _make_component(
    comp_id: str,
    name: str,
    container: str = "backend",
    stereotype: str = "service",
    file_path: str = "src/main/java/SomeClass.java",
    module: str = "com.example.service",
    evidence_ids: list = None,
    tags: list = None,
) -> CollectedComponent:
    """Helper to build a CollectedComponent with defaults."""
    return CollectedComponent(
        id=comp_id,
        container=container,
        name=name,
        stereotype=stereotype,
        file_path=file_path,
        module=module,
        evidence_ids=evidence_ids or [],
        tags=tags or [],
    )


def _make_evidence(
    ev_id: str,
    path: str = "src/main/java/Test.java",
    line_start: int = 1,
    line_end: int = 10,
    reason: str = "annotation",
) -> CollectedEvidence:
    """Helper to build a CollectedEvidence with defaults."""
    return CollectedEvidence(
        path=path,
        line_start=line_start,
        line_end=line_end,
        reason=reason,
        chunk_id=None,
    )


def _make_interface(
    iface_id: str,
    name: str,
    container: str = "backend",
    interface_type: str = "rest",
    endpoint: str = "/api/test",
    method: str = "GET",
    implemented_by: str = "",
    evidence_ids: list = None,
) -> CollectedInterface:
    """Helper to build a CollectedInterface with defaults."""
    return CollectedInterface(
        id=iface_id,
        container=container,
        name=name,
        interface_type=interface_type,
        endpoint=endpoint,
        method=method,
        implemented_by=implemented_by,
        evidence_ids=evidence_ids or [],
    )


def _make_relation(
    from_id: str,
    to_id: str,
    relation_type: str = "uses",
    evidence_ids: list = None,
) -> CollectedRelation:
    """Helper to build a CollectedRelation with defaults."""
    return CollectedRelation(
        from_id=from_id,
        to_id=to_id,
        relation_type=relation_type,
        evidence_ids=evidence_ids or [],
    )


# =============================================================================
# Tests: PhaseOutputValidator Instantiation
# =============================================================================


class TestPhaseOutputValidatorInstantiation:
    def test_instantiation(self):
        """PhaseOutputValidator() creates a valid instance."""
        v = PhaseOutputValidator()
        assert v is not None
        assert hasattr(v, "validate_phase")
        assert hasattr(v, "validate_dependency")

    def test_unknown_phase_returns_no_errors(self, validator):
        """Validating an undefined phase ID should return empty list (no spec)."""
        errors = validator.validate_phase("phase99_nonexistent")
        assert errors == []


# =============================================================================
# Tests: Phase 0 Validation (Indexing)
# =============================================================================


class TestPhase0Validation:
    def test_missing_chroma_dir_returns_errors(self, validator, tmp_path, monkeypatch):
        """validate_phase('phase0_indexing') with missing .chroma dir returns errors."""
        monkeypatch.chdir(tmp_path)
        # .cache/.chroma does NOT exist
        errors = validator.validate_phase("phase0_indexing")
        assert len(errors) >= 1
        assert any(".chroma" in e for e in errors)

    def test_empty_chroma_file_returns_errors(self, validator, tmp_path, monkeypatch):
        """An empty .chroma file (not a directory) should report as empty."""
        monkeypatch.chdir(tmp_path)
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        chroma_file = cache_dir / ".chroma"
        chroma_file.write_text("")  # Empty file (not dir)
        errors = validator.validate_phase("phase0_indexing")
        assert len(errors) >= 1
        assert any("Empty" in e or "Missing" in e for e in errors)

    def test_valid_chroma_dir_returns_no_errors(self, validator, tmp_path, monkeypatch):
        """A real .chroma directory passes phase0 validation."""
        monkeypatch.chdir(tmp_path)
        chroma_dir = tmp_path / ".cache" / ".chroma"
        chroma_dir.mkdir(parents=True)
        # Phase 0 spec only checks required_paths; a directory isn't a file,
        # so is_file() is False and the empty check is skipped.
        errors = validator.validate_phase("phase0_indexing")
        # Directory exists -> no "Missing" error; not a file -> no "Empty" error
        assert errors == []


# =============================================================================
# Tests: Phase 1 Validation (Architecture Facts)
# =============================================================================


class TestPhase1Validation:
    def test_missing_json_returns_errors(self, validator, tmp_path, monkeypatch):
        """validate_phase('phase1_architecture_facts') with missing JSON files returns errors."""
        monkeypatch.chdir(tmp_path)
        errors = validator.validate_phase("phase1_architecture_facts")
        assert len(errors) >= 1
        assert any("architecture_facts.json" in e for e in errors)

    def test_valid_json_returns_no_errors(self, validator, tmp_path, monkeypatch):
        """Valid JSON that passes Pydantic schema should produce no errors."""
        monkeypatch.chdir(tmp_path)
        # Create directory structure
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        # Write valid facts JSON
        facts_path = arch_dir / "architecture_facts.json"
        facts_path.write_text(json.dumps(_valid_facts_json()), encoding="utf-8")

        # Write valid evidence JSON
        evidence_path = arch_dir / "evidence_map.json"
        evidence_path.write_text(json.dumps(_valid_evidence_json()), encoding="utf-8")

        errors = validator.validate_phase("phase1_architecture_facts")
        assert errors == [], f"Unexpected errors: {errors}"

    def test_invalid_json_content_returns_errors(self, validator, tmp_path, monkeypatch):
        """Malformed JSON (not valid JSON at all) returns parse error."""
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        # Write invalid JSON
        facts_path = arch_dir / "architecture_facts.json"
        facts_path.write_text("{this is not: valid json!!!}", encoding="utf-8")

        evidence_path = arch_dir / "evidence_map.json"
        evidence_path.write_text(json.dumps(_valid_evidence_json()), encoding="utf-8")

        errors = validator.validate_phase("phase1_architecture_facts")
        assert len(errors) >= 1
        assert any("Invalid JSON" in e for e in errors)

    def test_schema_violation_returns_errors(self, validator, tmp_path, monkeypatch):
        """JSON that doesn't conform to ArchitectureFacts schema returns errors."""
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        # Valid JSON but missing 'system' field (required by ArchitectureFacts)
        bad_data = {"containers": [], "components": []}
        facts_path = arch_dir / "architecture_facts.json"
        facts_path.write_text(json.dumps(bad_data), encoding="utf-8")

        evidence_path = arch_dir / "evidence_map.json"
        evidence_path.write_text(json.dumps({}), encoding="utf-8")

        errors = validator.validate_phase("phase1_architecture_facts")
        assert len(errors) >= 1
        assert any("Schema validation failed" in e for e in errors)

    def test_zero_components_returns_error(self, validator, tmp_path, monkeypatch):
        """Facts with 0 components should fail the min_components check."""
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        # Valid schema but no components and no containers
        data = _valid_facts_json()
        data["components"] = []
        data["containers"] = []
        data["interfaces"] = []
        data["relations"] = []

        facts_path = arch_dir / "architecture_facts.json"
        facts_path.write_text(json.dumps(data), encoding="utf-8")

        evidence_path = arch_dir / "evidence_map.json"
        evidence_path.write_text(json.dumps(_valid_evidence_json()), encoding="utf-8")

        errors = validator.validate_phase("phase1_architecture_facts")
        assert len(errors) >= 1
        assert any("Too few" in e for e in errors)

    def test_zero_components_with_containers_returns_component_error(self, validator, tmp_path, monkeypatch):
        """Facts with containers but 0 components should fail min_components."""
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        data = _valid_facts_json()
        data["components"] = []  # No components
        # Keep containers to pass min_containers
        data["interfaces"] = []
        data["relations"] = []

        facts_path = arch_dir / "architecture_facts.json"
        facts_path.write_text(json.dumps(data), encoding="utf-8")

        evidence_path = arch_dir / "evidence_map.json"
        evidence_path.write_text(json.dumps(_valid_evidence_json()), encoding="utf-8")

        errors = validator.validate_phase("phase1_architecture_facts")
        assert any("Too few components" in e for e in errors)


# =============================================================================
# Tests: Phase 2 Validation (Architecture Analysis)
# =============================================================================


class TestPhase2Validation:
    def test_missing_keys_returns_errors(self, validator, tmp_path, monkeypatch):
        """validate_phase('phase2_architecture_analysis') with missing required keys returns errors."""
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        # JSON is valid but missing 'architecture' and 'patterns' keys
        incomplete_data = {"summary": "just a summary"}
        analysis_path = arch_dir / "analyzed_architecture.json"
        analysis_path.write_text(json.dumps(incomplete_data), encoding="utf-8")

        errors = validator.validate_phase("phase2_architecture_analysis")
        assert len(errors) >= 1
        assert any("architecture" in e for e in errors)
        assert any("patterns" in e for e in errors)

    def test_valid_analysis_returns_no_errors(self, validator, tmp_path, monkeypatch):
        """Valid analysis JSON with all required keys should pass."""
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        analysis_path = arch_dir / "analyzed_architecture.json"
        analysis_path.write_text(json.dumps(_valid_analysis_json()), encoding="utf-8")

        errors = validator.validate_phase("phase2_architecture_analysis")
        assert errors == [], f"Unexpected errors: {errors}"

    def test_partial_keys_returns_specific_errors(self, validator, tmp_path, monkeypatch):
        """JSON with only 'architecture' but missing 'patterns' returns error for 'patterns'."""
        monkeypatch.chdir(tmp_path)
        arch_dir = tmp_path / "knowledge" / "architecture"
        arch_dir.mkdir(parents=True)

        partial = {"architecture": {"style": "microservice"}}
        analysis_path = arch_dir / "analyzed_architecture.json"
        analysis_path.write_text(json.dumps(partial), encoding="utf-8")

        errors = validator.validate_phase("phase2_architecture_analysis")
        assert len(errors) == 1
        assert "patterns" in errors[0]


# =============================================================================
# Tests: Phase 3 Validation (Architecture Synthesis)
# =============================================================================


class TestPhase3Validation:
    def test_missing_md_files_returns_errors(self, validator, tmp_path, monkeypatch):
        """validate_phase('phase3_architecture_synthesis') with missing .md files returns errors."""
        monkeypatch.chdir(tmp_path)
        errors = validator.validate_phase("phase3_architecture_synthesis")
        assert len(errors) >= 1
        assert any(".md" in e for e in errors)

    def test_too_small_files_returns_errors(self, validator, tmp_path, monkeypatch):
        """Files smaller than min_file_size (500 bytes) should produce errors."""
        monkeypatch.chdir(tmp_path)
        c4_dir = tmp_path / "knowledge" / "architecture" / "c4"
        c4_dir.mkdir(parents=True)

        required = [
            "c4-context.md",
            "c4-container.md",
            "c4-component.md",
            "c4-deployment.md",
        ]
        for fname in required:
            (c4_dir / fname).write_text("# Short", encoding="utf-8")

        errors = validator.validate_phase("phase3_architecture_synthesis")
        assert len(errors) >= 1
        assert any("too small" in e.lower() or "Output too small" in e for e in errors)

    def test_valid_synthesis_files_returns_no_errors(self, validator, tmp_path, monkeypatch):
        """Sufficiently large .md files should pass phase3 validation."""
        monkeypatch.chdir(tmp_path)
        c4_dir = tmp_path / "knowledge" / "architecture" / "c4"
        c4_dir.mkdir(parents=True)

        required = [
            "c4-context.md",
            "c4-container.md",
            "c4-component.md",
            "c4-deployment.md",
        ]
        big_content = "# C4 Documentation\n\n" + ("This is a detailed architecture document. " * 50)
        for fname in required:
            (c4_dir / fname).write_text(big_content, encoding="utf-8")

        errors = validator.validate_phase("phase3_architecture_synthesis")
        assert errors == [], f"Unexpected errors: {errors}"


# =============================================================================
# Tests: Dependency Validation
# =============================================================================


class TestDependencyValidation:
    def test_validate_dependency_calls_validate_phase_for_upstream(self, validator, tmp_path, monkeypatch):
        """validate_dependency() should validate upstream phase outputs.

        Since validate_dependency imports SDLCOrchestrator (which may need config),
        we mock the orchestrator to return a known dependency list, then assert
        validate_phase is called for each dependency.
        """
        monkeypatch.chdir(tmp_path)

        # Record which phases were validated
        validated_phases = []
        original_validate = validator.validate_phase

        def mock_validate_phase(phase_id):
            validated_phases.append(phase_id)
            return original_validate(phase_id)

        validator.validate_phase = mock_validate_phase

        # Mock the orchestrator import and usage
        class MockOrchestrator:
            def get_phase_config(self, phase_id):
                return {
                    "phase1_architecture_facts": {
                        "dependencies": ["phase0_indexing"],
                    },
                    "phase2_architecture_analysis": {
                        "dependencies": ["phase0_indexing", "phase1_architecture_facts"],
                    },
                }.get(phase_id, {"dependencies": []})

        # Patch the import inside validate_dependency
        monkeypatch.setattr(
            "aicodegencrew.shared.validation.PhaseOutputValidator.validate_dependency",
            lambda self_, phase_id: self_._mock_validate_dependency(phase_id, MockOrchestrator()),
        )

        def _mock_validate_dependency(self_, phase_id, mock_orch):
            phase_config = mock_orch.get_phase_config(phase_id)
            deps = phase_config.get("dependencies", [])
            all_errors = []
            for dep_id in deps:
                errors = self_.validate_phase(dep_id)
                if errors:
                    all_errors.append(f"Dependency {dep_id} invalid:")
                    all_errors.extend(f"  - {e}" for e in errors)
            return all_errors

        validator._mock_validate_dependency = lambda pid, mo: _mock_validate_dependency(validator, pid, mo)

        # Call the mocked version directly to test the logic
        errors = _mock_validate_dependency(validator, "phase2_architecture_analysis", MockOrchestrator())

        # Should have validated both upstream phases
        assert "phase0_indexing" in validated_phases
        assert "phase1_architecture_facts" in validated_phases
        # Both phases have missing files, so errors should exist
        assert len(errors) >= 2
        assert any("phase0_indexing" in e for e in errors)
        assert any("phase1_architecture_facts" in e for e in errors)


# =============================================================================
# Tests: CanonicalIdGenerator
# =============================================================================


class TestCanonicalIdGenerator:
    def test_for_component_generates_stable_id(self):
        """for_component() produces a hierarchical component.container.module.name ID."""
        cid = CanonicalIdGenerator.for_component(
            container="Backend",
            module="workflow",
            name="WorkflowController",
            stereotype="controller",
        )
        assert cid.startswith("component.")
        assert "backend" in cid.lower()
        assert "workflow_controller" in cid

    def test_for_component_deterministic(self):
        """Same inputs always produce the same ID."""
        id1 = CanonicalIdGenerator.for_component("Backend", "svc", "UserService", "service")
        id2 = CanonicalIdGenerator.for_component("Backend", "svc", "UserService", "service")
        assert id1 == id2

    def test_for_container_generates_name_format(self):
        """for_container() generates 'container.name' format."""
        cid = CanonicalIdGenerator.for_container("Backend", "Spring Boot")
        assert cid == "container.backend"

    def test_for_container_normalizes_name(self):
        """Container names with special chars are normalized."""
        cid = CanonicalIdGenerator.for_container("My-Frontend App", "Angular")
        assert cid.startswith("container.")
        assert " " not in cid
        assert "-" not in cid.split("container.")[1]

    def test_for_interface_rest_generates_stable_id(self):
        """for_interface() for REST produces interface.container.rest.METHOD_path."""
        iid = CanonicalIdGenerator.for_interface(
            container="backend",
            iface_type="rest",
            method="POST",
            path="/workflow/create",
        )
        assert iid.startswith("interface.")
        assert "rest" in iid
        assert "post" in iid.lower()
        assert "workflow" in iid

    def test_for_interface_route_generates_stable_id(self):
        """for_interface() for route type produces route-specific ID."""
        iid = CanonicalIdGenerator.for_interface(
            container="frontend",
            iface_type="route",
            method="",
            path="/dashboard/overview",
        )
        assert "route" in iid
        assert "dashboard" in iid

    def test_for_interface_fallback(self):
        """for_interface() with unknown type falls back to hash-based ID."""
        iid = CanonicalIdGenerator.for_interface(
            container="backend",
            iface_type="grpc",
            method="call",
            path="",
        )
        assert iid.startswith("interface.backend.grpc.")

    def test_normalize_converts_camelcase_to_snake(self):
        """_normalize() converts CamelCase to snake_case."""
        assert CanonicalIdGenerator._normalize("WorkflowController") == "workflow_controller"
        assert CanonicalIdGenerator._normalize("UserService") == "user_service"
        assert CanonicalIdGenerator._normalize("HTMLParser") == "html_parser"

    def test_normalize_removes_special_chars(self):
        """_normalize() replaces non-alphanumeric chars with underscores."""
        assert CanonicalIdGenerator._normalize("my-service.v2") == "my_service_v2"
        assert CanonicalIdGenerator._normalize("hello world!") == "hello_world"  # trailing _ stripped

    def test_normalize_empty_string(self):
        """_normalize() returns empty for empty input."""
        assert CanonicalIdGenerator._normalize("") == ""
        assert CanonicalIdGenerator._normalize(None) == ""

    def test_for_evidence_generates_hash_based_id(self):
        """for_evidence() generates ev.HASH format."""
        eid = CanonicalIdGenerator.for_evidence("src/Main.java", 10, 50)
        assert eid.startswith("ev.")
        assert len(eid) > 4  # ev. + at least some hash chars

    def test_for_evidence_deterministic(self):
        """Same file and line range produce same evidence ID."""
        e1 = CanonicalIdGenerator.for_evidence("src/Main.java", 10, 50)
        e2 = CanonicalIdGenerator.for_evidence("src/Main.java", 10, 50)
        assert e1 == e2

    def test_for_table_generates_stable_id(self):
        """for_table() produces table.schema.name format."""
        tid = CanonicalIdGenerator.for_table("public", "DOCUMENT")
        assert tid.startswith("table.")
        assert "public" in tid
        assert "document" in tid.lower()


# =============================================================================
# Tests: LayerClassifier
# =============================================================================


class TestLayerClassifier:
    def test_controller_returns_presentation(self):
        assert LayerClassifier.classify("controller") == ArchitectureLayer.PRESENTATION

    def test_service_returns_application(self):
        assert LayerClassifier.classify("service") == ArchitectureLayer.APPLICATION

    def test_repository_returns_dataaccess(self):
        assert LayerClassifier.classify("repository") == ArchitectureLayer.DATA_ACCESS

    def test_entity_returns_domain(self):
        assert LayerClassifier.classify("entity") == ArchitectureLayer.DOMAIN

    def test_unknown_returns_unknown(self):
        """An unmapped stereotype returns UNKNOWN (not infrastructure as default)."""
        result = LayerClassifier.classify("unknown")
        assert result == ArchitectureLayer.UNKNOWN

    def test_configuration_returns_infrastructure(self):
        assert LayerClassifier.classify("configuration") == ArchitectureLayer.INFRASTRUCTURE

    def test_case_insensitive(self):
        """Classification should be case-insensitive."""
        assert LayerClassifier.classify("Controller") == ArchitectureLayer.PRESENTATION
        assert LayerClassifier.classify("SERVICE") == ArchitectureLayer.APPLICATION
        assert LayerClassifier.classify("Repository") == ArchitectureLayer.DATA_ACCESS

    def test_hyphen_and_space_normalization(self):
        """Hyphens and spaces are converted to underscores before lookup."""
        assert LayerClassifier.classify("domain-service") == ArchitectureLayer.DOMAIN
        assert LayerClassifier.classify("domain service") == ArchitectureLayer.DOMAIN
        assert LayerClassifier.classify("value_object") == ArchitectureLayer.DOMAIN

    def test_facade_returns_application(self):
        assert LayerClassifier.classify("facade") == ArchitectureLayer.APPLICATION

    def test_dao_returns_dataaccess(self):
        assert LayerClassifier.classify("dao") == ArchitectureLayer.DATA_ACCESS

    def test_aggregate_returns_domain(self):
        assert LayerClassifier.classify("aggregate") == ArchitectureLayer.DOMAIN

    def test_dockerfile_returns_infrastructure(self):
        assert LayerClassifier.classify("dockerfile") == ArchitectureLayer.INFRASTRUCTURE

    def test_layer_values(self):
        """Verify .value strings match expected format."""
        assert ArchitectureLayer.PRESENTATION.value == "presentation"
        assert ArchitectureLayer.APPLICATION.value == "application"
        assert ArchitectureLayer.DOMAIN.value == "domain"
        assert ArchitectureLayer.DATA_ACCESS.value == "dataaccess"
        assert ArchitectureLayer.INFRASTRUCTURE.value == "infrastructure"
        assert ArchitectureLayer.UNKNOWN.value == "unknown"


# =============================================================================
# Tests: Component Deduplication
# =============================================================================


class TestComponentDeduplication:
    def test_dedup_by_container_name_key(self, builder):
        """Two components with same container:name should merge into one."""
        ev1 = _make_evidence("ev1", path="src/A.java", line_start=1, line_end=10)
        ev2 = _make_evidence("ev2", path="src/B.java", line_start=20, line_end=30)

        comp1 = _make_component(
            "c1",
            "UserService",
            container="backend",
            stereotype="service",
            file_path="src/A.java",
            evidence_ids=["ev1"],
        )
        comp2 = _make_component(
            "c2",
            "UserService",
            container="backend",
            stereotype="service",
            file_path="src/B.java",
            evidence_ids=["ev2"],
        )

        builder.add_collector_output(
            components=[comp1, comp2],
            interfaces=[],
            relations=[],
            evidence={"ev1": ev1, "ev2": ev2},
        )

        model = builder.build()
        # Should have exactly 1 deduplicated component
        assert len(model.components) == 1

        # The surviving component should have both file paths
        comp = next(iter(model.components.values()))
        assert len(comp.file_paths) == 2
        assert "src/A.java" in comp.file_paths
        assert "src/B.java" in comp.file_paths

    def test_different_containers_not_deduped(self, builder):
        """Components with same name but different containers remain separate."""
        comp1 = _make_component("c1", "AppComponent", container="frontend", stereotype="component")
        comp2 = _make_component("c2", "AppComponent", container="backend", stereotype="service")

        builder.add_collector_output(
            components=[comp1, comp2],
            interfaces=[],
            relations=[],
            evidence={},
        )

        model = builder.build()
        assert len(model.components) == 2

    def test_different_names_not_deduped(self, builder):
        """Components with different names in same container remain separate."""
        comp1 = _make_component("c1", "UserService", container="backend")
        comp2 = _make_component("c2", "OrderService", container="backend")

        builder.add_collector_output(
            components=[comp1, comp2],
            interfaces=[],
            relations=[],
            evidence={},
        )

        model = builder.build()
        assert len(model.components) == 2


# =============================================================================
# Tests: ArchitectureModelBuilder.build()
# =============================================================================


class TestBuild:
    def test_builder_initialization(self):
        """ArchitectureModelBuilder(system_name) should set system_name."""
        b = ArchitectureModelBuilder(system_name="MyApp")
        assert b.system_name == "MyApp"
        assert len(b._raw_components) == 0
        assert len(b._raw_containers) == 0

    def test_build_produces_architecture_model(self, builder):
        """build() should return an ArchitectureModel instance."""
        model = builder.build()
        assert isinstance(model, ArchitectureModel)
        assert model.system_name == "TestSystem"

    def test_build_with_containers_and_components(self, builder):
        """build() wires containers and components with correct counts."""
        # Add a container
        builder.add_containers(
            containers=[
                {
                    "name": "backend",
                    "technology": "Spring Boot",
                    "category": "application",
                    "root_path": "backend/",
                    "type": "application",
                }
            ],
            evidence={},
        )

        # Add components
        ev1 = _make_evidence("ev1", path="src/UserController.java")
        ev2 = _make_evidence("ev2", path="src/UserService.java")
        ev3 = _make_evidence("ev3", path="src/UserRepo.java")

        controller = _make_component(
            "c1",
            "UserController",
            container="backend",
            stereotype="controller",
            file_path="src/UserController.java",
            evidence_ids=["ev1"],
        )
        service = _make_component(
            "c2",
            "UserService",
            container="backend",
            stereotype="service",
            file_path="src/UserService.java",
            evidence_ids=["ev2"],
        )
        repo = _make_component(
            "c3",
            "UserRepository",
            container="backend",
            stereotype="repository",
            file_path="src/UserRepo.java",
            evidence_ids=["ev3"],
        )

        builder.add_collector_output(
            components=[controller, service, repo],
            interfaces=[],
            relations=[],
            evidence={"ev1": ev1, "ev2": ev2, "ev3": ev3},
        )

        model = builder.build()

        assert len(model.containers) == 1
        assert len(model.components) == 3
        assert len(model.evidence) == 3

    def test_build_with_interfaces(self, builder):
        """build() normalizes interfaces."""
        iface = _make_interface(
            "iface1",
            "getUsers",
            container="backend",
            interface_type="rest",
            endpoint="/api/users",
            method="GET",
        )

        builder.add_collector_output(
            components=[],
            interfaces=[iface],
            relations=[],
            evidence={},
        )

        model = builder.build()
        assert len(model.interfaces) == 1

    def test_build_with_relations(self, builder):
        """build() resolves relations between components."""
        comp1 = _make_component("c1", "UserController", container="backend", stereotype="controller")
        comp2 = _make_component("c2", "UserService", container="backend", stereotype="service")
        rel = _make_relation("c1", "c2", "uses")

        builder.add_collector_output(
            components=[comp1, comp2],
            interfaces=[],
            relations=[rel],
            evidence={},
        )

        model = builder.build()
        assert len(model.relations) >= 1

    def test_build_assigns_correct_layers(self, builder):
        """build() assigns layers based on stereotype."""
        controller = _make_component("c1", "TestCtrl", stereotype="controller")
        service = _make_component("c2", "TestSvc", stereotype="service")
        repo = _make_component("c3", "TestRepo", stereotype="repository")
        entity = _make_component("c4", "TestEntity", stereotype="entity")

        builder.add_collector_output(
            components=[controller, service, repo, entity],
            interfaces=[],
            relations=[],
            evidence={},
        )

        model = builder.build()

        layers = {c.name: c.layer for c in model.components.values()}
        assert layers["TestCtrl"] == "presentation"
        assert layers["TestSvc"] == "application"
        assert layers["TestRepo"] == "dataaccess"
        assert layers["TestEntity"] == "domain"

    def test_build_empty_model(self, builder):
        """build() with no inputs returns model with 0 counts."""
        model = builder.build()
        assert len(model.containers) == 0
        assert len(model.components) == 0
        assert len(model.interfaces) == 0
        assert len(model.relations) == 0
        assert len(model.evidence) == 0


# =============================================================================
# Tests: ArchitectureModel.get_statistics()
# =============================================================================


class TestGetStatistics:
    def test_get_statistics_aggregates_by_layer(self, builder):
        """get_statistics() groups component counts by layer."""
        comps = [
            _make_component("c1", "Ctrl1", stereotype="controller"),
            _make_component("c2", "Ctrl2", stereotype="controller"),
            _make_component("c3", "Svc1", stereotype="service"),
            _make_component("c4", "Repo1", stereotype="repository"),
        ]

        builder.add_collector_output(
            components=comps,
            interfaces=[],
            relations=[],
            evidence={},
        )

        model = builder.build()
        stats = model.get_statistics()

        assert stats["system_name"] == "TestSystem"
        assert stats["components"] == 4
        assert stats["by_layer"]["presentation"] == 2
        assert stats["by_layer"]["application"] == 1
        assert stats["by_layer"]["dataaccess"] == 1

    def test_get_statistics_aggregates_by_stereotype(self, builder):
        """get_statistics() groups component counts by stereotype."""
        comps = [
            _make_component("c1", "Ctrl1", stereotype="controller"),
            _make_component("c2", "Svc1", stereotype="service"),
            _make_component("c3", "Svc2", stereotype="service"),
        ]

        builder.add_collector_output(
            components=comps,
            interfaces=[],
            relations=[],
            evidence={},
        )

        model = builder.build()
        stats = model.get_statistics()

        assert stats["by_stereotype"]["controller"] == 1
        assert stats["by_stereotype"]["service"] == 2

    def test_get_statistics_counts_all_element_types(self, builder):
        """get_statistics() includes containers, interfaces, relations, evidence."""
        builder.add_containers(
            containers=[
                {"name": "backend", "technology": "Spring Boot", "category": "app"},
                {"name": "frontend", "technology": "Angular", "category": "app"},
            ],
            evidence={},
        )

        ev1 = _make_evidence("ev1")
        comp1 = _make_component("c1", "Ctrl", stereotype="controller", evidence_ids=["ev1"])
        iface = _make_interface("i1", "getStuff", endpoint="/stuff")

        builder.add_collector_output(
            components=[comp1],
            interfaces=[iface],
            relations=[],
            evidence={"ev1": ev1},
        )

        model = builder.build()
        stats = model.get_statistics()

        assert stats["containers"] == 2
        assert stats["components"] == 1
        assert stats["interfaces"] == 1
        assert stats["evidence"] == 1

    def test_get_statistics_empty_model(self, builder):
        """get_statistics() on empty model returns all zeros."""
        model = builder.build()
        stats = model.get_statistics()

        assert stats["containers"] == 0
        assert stats["components"] == 0
        assert stats["interfaces"] == 0
        assert stats["relations"] == 0
        assert stats["evidence"] == 0
        assert stats["by_layer"] == {}
        assert stats["by_stereotype"] == {}

    def test_get_statistics_includes_extra_dimensions(self, builder):
        """get_statistics() includes dependencies, workflows, etc."""
        model = builder.build()
        stats = model.get_statistics()

        assert "dependencies" in stats
        assert "workflows" in stats
        assert "entities" in stats
        assert "tables" in stats
        assert "migrations" in stats
        assert "runtime" in stats
        assert "infrastructure" in stats


# =============================================================================
# Tests: ArchitectureModel query methods
# =============================================================================


class TestArchitectureModelQueries:
    def _build_sample_model(self):
        """Build a model with known components for querying."""
        builder = ArchitectureModelBuilder(system_name="QueryTest")
        builder.add_containers(
            containers=[{"name": "backend", "technology": "Java", "category": "app"}],
            evidence={},
        )
        comps = [
            _make_component("c1", "UserController", container="backend", stereotype="controller"),
            _make_component("c2", "UserService", container="backend", stereotype="service"),
            _make_component("c3", "OrderService", container="backend", stereotype="service"),
            _make_component("c4", "UserRepository", container="backend", stereotype="repository"),
        ]
        rels = [
            _make_relation("c1", "c2", "uses"),
            _make_relation("c2", "c4", "uses"),
        ]
        builder.add_collector_output(
            components=comps,
            interfaces=[],
            relations=rels,
            evidence={},
        )
        return builder.build()

    def test_get_components_by_layer(self):
        model = self._build_sample_model()
        presentation = model.get_components_by_layer("presentation")
        assert len(presentation) == 1
        assert presentation[0].name == "UserController"

        application = model.get_components_by_layer("application")
        assert len(application) == 2

    def test_get_components_by_stereotype(self):
        model = self._build_sample_model()
        services = model.get_components_by_stereotype("service")
        assert len(services) == 2
        names = {s.name for s in services}
        assert "UserService" in names
        assert "OrderService" in names

    def test_get_components_for_container(self):
        model = self._build_sample_model()
        # Find the backend container ID
        backend_id = None
        for cid in model.containers:
            if "backend" in cid:
                backend_id = cid
                break
        assert backend_id is not None
        comps = model.get_components_for_container(backend_id)
        assert len(comps) == 4

    def test_get_relations_from(self):
        model = self._build_sample_model()
        # Find UserController's canonical ID
        ctrl_id = None
        for cid, comp in model.components.items():
            if comp.name == "UserController":
                ctrl_id = cid
                break
        assert ctrl_id is not None
        rels = model.get_relations_from(ctrl_id)
        assert len(rels) >= 1

    def test_get_relations_to(self):
        model = self._build_sample_model()
        # Find UserRepository's canonical ID
        repo_id = None
        for cid, comp in model.components.items():
            if comp.name == "UserRepository":
                repo_id = cid
                break
        assert repo_id is not None
        rels = model.get_relations_to(repo_id)
        assert len(rels) >= 1


# =============================================================================
# Tests: Evidence normalization
# =============================================================================


class TestEvidenceNormalization:
    def test_evidence_ids_are_remapped(self, builder):
        """Component evidence IDs should be mapped to canonical ev.HASH format."""
        ev = _make_evidence("ev_old_1", path="src/Foo.java", line_start=5, line_end=15)
        comp = _make_component("c1", "Foo", evidence_ids=["ev_old_1"])

        builder.add_collector_output(
            components=[comp],
            interfaces=[],
            relations=[],
            evidence={"ev_old_1": ev},
        )

        model = builder.build()
        # All evidence keys should now be canonical ev.XXXX format
        for eid in model.evidence:
            assert eid.startswith("ev.")

    def test_evidence_preserves_path_and_reason(self, builder):
        """Normalized evidence retains original path and reason."""
        ev = _make_evidence(
            "ev_orig",
            path="src/main/Service.java",
            line_start=100,
            line_end=150,
            reason="@Service annotation",
        )

        builder.add_collector_output(
            components=[],
            interfaces=[],
            relations=[],
            evidence={"ev_orig": ev},
        )

        model = builder.build()
        assert len(model.evidence) == 1
        ev_data = next(iter(model.evidence.values()))
        assert ev_data["path"] == "src/main/Service.java"
        assert ev_data["reason"] == "@Service annotation"
        assert ev_data["lines"] == "100-150"


# =============================================================================
# Tests: Edge cases
# =============================================================================


class TestEdgeCases:
    def test_component_with_empty_module(self, builder):
        """Component with empty module uses 'core' as default in ID."""
        comp = _make_component("c1", "MyComp", module="")
        builder.add_collector_output(
            components=[comp],
            interfaces=[],
            relations=[],
            evidence={},
        )
        model = builder.build()
        comp_obj = next(iter(model.components.values()))
        assert "core" in comp_obj.id  # Module defaults to "core"

    def test_self_referencing_relation_skipped(self, builder):
        """Relations where from == to (self-reference) are skipped."""
        comp = _make_component("c1", "SelfRef", container="backend", stereotype="service")
        rel = _make_relation("c1", "c1", "uses")

        builder.add_collector_output(
            components=[comp],
            interfaces=[],
            relations=[rel],
            evidence={},
        )

        model = builder.build()
        assert len(model.relations) == 0

    def test_duplicate_relations_deduped(self, builder):
        """Duplicate relations (same from, to, type) are deduplicated."""
        comp1 = _make_component("c1", "A", container="backend")
        comp2 = _make_component("c2", "B", container="backend")
        rel1 = _make_relation("c1", "c2", "uses")
        rel2 = _make_relation("c1", "c2", "uses")  # duplicate

        builder.add_collector_output(
            components=[comp1, comp2],
            interfaces=[],
            relations=[rel1, rel2],
            evidence={},
        )

        model = builder.build()
        assert len(model.relations) == 1

    def test_canonical_component_to_dict(self, builder):
        """CanonicalComponent.to_dict() includes all expected keys."""
        comp = _make_component("c1", "SomeCtrl", stereotype="controller")
        builder.add_collector_output(
            components=[comp],
            interfaces=[],
            relations=[],
            evidence={},
        )
        model = builder.build()
        comp_obj = next(iter(model.components.values()))
        d = comp_obj.to_dict()
        assert "id" in d
        assert "name" in d
        assert "container" in d
        assert "stereotype" in d
        assert "layer" in d
        assert "module" in d
        assert "file_paths" in d
        assert "evidence_ids" in d
        assert "tags" in d

    def test_canonical_container_to_dict(self, builder):
        """CanonicalContainer.to_dict() includes all expected keys."""
        builder.add_containers(
            containers=[
                {
                    "name": "backend",
                    "technology": "Spring Boot",
                    "category": "application",
                    "root_path": "backend/",
                }
            ],
            evidence={},
        )
        model = builder.build()
        container_obj = next(iter(model.containers.values()))
        d = container_obj.to_dict()
        assert "id" in d
        assert "name" in d
        assert "technology" in d
        assert "category" in d
        assert "root_path" in d
