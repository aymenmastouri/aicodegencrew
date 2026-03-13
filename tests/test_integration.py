"""
Integration tests for phase data flow.

Tests the data contracts between SDLC phases without requiring LLM or network.
Each test group verifies that output from one phase can be consumed by the next.
"""

import json
import sys
import time
from pathlib import Path

import pytest

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Phase 0 -> Phase 1  data flow
# =============================================================================


class TestPhase0ToPhase1:
    """IndexingConfig, IndexingState, and fingerprint calculation."""

    # ---- IndexingConfig validates modes ----

    def test_indexing_config_valid_modes(self, tmp_path):
        """IndexingConfig accepts all four documented modes."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingConfig

        repo = tmp_path / "repo"
        repo.mkdir()

        for mode in ("off", "auto", "smart", "force"):
            cfg = IndexingConfig(repo_path=repo, index_mode=mode)
            assert cfg.index_mode == mode
            assert cfg.repo_path == repo

    def test_indexing_config_defaults(self, tmp_path):
        """IndexingConfig uses sensible defaults."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingConfig

        repo = tmp_path / "repo"
        repo.mkdir()

        cfg = IndexingConfig(repo_path=repo)
        assert cfg.index_mode == "auto"
        assert cfg.batch_size == 50
        assert cfg.max_total_files == 8000
        assert cfg.chunk_chars == 1800
        assert cfg.chunk_overlap == 200

    def test_indexing_config_from_env_requires_repo(self, monkeypatch):
        """from_env raises ValueError when no repo path is available."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingConfig

        monkeypatch.delenv("PROJECT_PATH", raising=False)
        monkeypatch.delenv("REPO_PATH", raising=False)

        with pytest.raises(ValueError, match="No repository path"):
            IndexingConfig.from_env()

    def test_indexing_config_from_env_with_override(self, tmp_path, monkeypatch):
        """from_env respects explicit overrides."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingConfig

        repo = tmp_path / "repo"
        repo.mkdir()

        cfg = IndexingConfig.from_env(
            repo_path=str(repo),
            index_mode="force",
            chroma_dir=str(tmp_path / "chroma"),
        )
        assert cfg.index_mode == "force"
        assert cfg.chroma_dir == str(tmp_path / "chroma")

    # ---- IndexingState serialization / deserialization ----

    def test_indexing_state_save_and_load(self, tmp_path):
        """IndexingState round-trips through JSON correctly."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingState

        state = IndexingState(
            fingerprint="abc123",
            fingerprint_type="git",
            chunk_count=42,
            timestamp=time.time(),
            repo_path="/some/repo",
        )
        state.save(tmp_path)

        loaded = IndexingState.load(tmp_path)
        assert loaded is not None
        assert loaded.fingerprint == "abc123"
        assert loaded.fingerprint_type == "git"
        assert loaded.chunk_count == 42
        assert loaded.repo_path == "/some/repo"

    def test_indexing_state_load_missing(self, tmp_path):
        """Loading from a directory without state returns None."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingState

        result = IndexingState.load(tmp_path)
        assert result is None

    def test_indexing_state_load_corrupt_json(self, tmp_path):
        """Loading corrupt JSON returns None gracefully."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingState

        state_file = tmp_path / ".indexing_state.json"
        state_file.write_text("not valid json {{{", encoding="utf-8")

        result = IndexingState.load(tmp_path)
        assert result is None

    def test_indexing_state_overwrite(self, tmp_path):
        """Saving overwrites previously saved state."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingState

        state1 = IndexingState(fingerprint="old", chunk_count=10, timestamp=1.0)
        state1.save(tmp_path)

        state2 = IndexingState(fingerprint="new", chunk_count=99, timestamp=2.0)
        state2.save(tmp_path)

        loaded = IndexingState.load(tmp_path)
        assert loaded.fingerprint == "new"
        assert loaded.chunk_count == 99

    # ---- Fingerprint calculation on mock repo ----

    def test_fingerprint_filesystem_fallback(self, tmp_path):
        """Fingerprint falls back to filesystem when .git is absent."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import (
            _calculate_repo_fingerprint,
        )

        # Create a small mock repo with Java files
        src = tmp_path / "src" / "main" / "java"
        src.mkdir(parents=True)
        (src / "App.java").write_text("public class App {}", encoding="utf-8")
        (src / "Service.java").write_text("public class Service {}", encoding="utf-8")

        fp, fp_type = _calculate_repo_fingerprint(tmp_path, include_submodules=False)
        assert fp_type == "fs"
        assert len(fp) == 16  # sha256[:16]

    def test_fingerprint_deterministic(self, tmp_path):
        """Same repo content produces same fingerprint."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import (
            _calculate_repo_fingerprint,
        )

        src = tmp_path / "src"
        src.mkdir()
        (src / "Main.java").write_text("class Main {}", encoding="utf-8")

        fp1, _ = _calculate_repo_fingerprint(tmp_path, include_submodules=False)
        fp2, _ = _calculate_repo_fingerprint(tmp_path, include_submodules=False)
        assert fp1 == fp2

    def test_fingerprint_changes_on_file_add(self, tmp_path):
        """Adding a file changes the fingerprint."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import (
            _calculate_repo_fingerprint,
        )

        src = tmp_path / "src"
        src.mkdir()
        (src / "A.java").write_text("class A {}", encoding="utf-8")

        fp1, _ = _calculate_repo_fingerprint(tmp_path, include_submodules=False)

        (src / "B.java").write_text("class B {}", encoding="utf-8")

        fp2, _ = _calculate_repo_fingerprint(tmp_path, include_submodules=False)
        assert fp1 != fp2

    # ---- IndexingPipeline off mode ----

    def test_indexing_pipeline_off_mode(self, tmp_path, monkeypatch):
        """IndexingPipeline with mode=off returns skip result without any IO."""
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingPipeline

        repo = tmp_path / "repo"
        repo.mkdir()

        monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))

        pipeline = IndexingPipeline(repo_path=str(repo), index_mode="off")
        result = pipeline.kickoff()

        assert result["status"] == "skipped"
        assert result["skipped"] is True
        assert result["index_mode"] == "off"
        assert result["phase"] == "discover"


# =============================================================================
# Phase 1 -> Phase 2  data flow
# =============================================================================


class TestPhase1ToPhase2:
    """Validates architecture_facts.json, evidence_map.json, and collector orchestrator."""

    def _create_mock_facts(self, output_dir: Path) -> dict:
        """Create a minimal valid architecture_facts.json."""
        facts = {
            "system": {
                "name": "TestSystem",
                "subsystems": [],
            },
            "containers": [
                {
                    "id": "backend",
                    "name": "backend",
                    "type": "application",
                    "technology": "Spring Boot",
                    "path": "backend",
                    "category": "application",
                }
            ],
            "components": [
                {
                    "name": "UserService",
                    "stereotype": "service",
                    "container_hint": "backend",
                    "file_path": "src/main/java/com/example/UserService.java",
                },
                {
                    "name": "UserController",
                    "stereotype": "controller",
                    "container_hint": "backend",
                    "file_path": "src/main/java/com/example/UserController.java",
                },
            ],
            "interfaces": [
                {
                    "name": "GET /api/users",
                    "type": "rest_endpoint",
                    "path": "/api/users",
                    "method": "GET",
                },
            ],
            "relations": [
                {"from": "UserController", "to": "UserService", "type": "uses"},
            ],
            "data_model": {"entities": [], "tables": [], "migrations": []},
            "runtime": [],
            "infrastructure": [],
            "dependencies": [],
            "workflows": [],
            "tech_versions": [],
            "security_details": [],
            "validation": [],
            "tests": [],
            "error_handling": [],
            "evidence": {},
            "statistics": {
                "containers": 1,
                "components": 2,
                "interfaces": 1,
                "relation_hints": 1,
            },
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        facts_path = output_dir / "architecture_facts.json"
        facts_path.write_text(json.dumps(facts, indent=2), encoding="utf-8")
        return facts

    def _create_mock_evidence_map(self, output_dir: Path) -> dict:
        """Create a minimal evidence_map.json."""
        evidence = {
            "ev_001": {
                "path": "src/main/java/com/example/UserService.java",
                "lines": "1-50",
                "reason": "@Service annotated class",
            },
            "ev_002": {
                "path": "src/main/java/com/example/UserController.java",
                "lines": "1-30",
                "reason": "@RestController annotated class",
            },
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = output_dir / "evidence_map.json"
        evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        return evidence

    def test_facts_json_has_required_keys(self, tmp_path):
        """architecture_facts.json must have all top-level keys Phase 2 expects."""
        facts = self._create_mock_facts(tmp_path)

        required_keys = [
            "system",
            "containers",
            "components",
            "interfaces",
            "relations",
            "data_model",
            "runtime",
            "infrastructure",
            "dependencies",
            "workflows",
            "statistics",
        ]
        for key in required_keys:
            assert key in facts, f"Missing key: {key}"

    def test_facts_json_system_has_name(self, tmp_path):
        """system object must have a name."""
        facts = self._create_mock_facts(tmp_path)
        assert facts["system"]["name"] == "TestSystem"

    def test_facts_json_components_have_stereotype(self, tmp_path):
        """Every component must have a stereotype field."""
        facts = self._create_mock_facts(tmp_path)
        for comp in facts["components"]:
            assert "stereotype" in comp, f"Component {comp['name']} missing stereotype"

    def test_evidence_map_references_valid_paths(self, tmp_path):
        """Evidence map entries must have path and lines fields."""
        evidence = self._create_mock_evidence_map(tmp_path)

        for ev_id, entry in evidence.items():
            assert "path" in entry, f"Evidence {ev_id} missing path"
            assert "lines" in entry, f"Evidence {ev_id} missing lines"
            assert "reason" in entry, f"Evidence {ev_id} missing reason"

    def test_facts_json_readable_by_load_json(self, tmp_path):
        """MiniCrewBase._load_json can read a valid facts file."""
        from aicodegencrew.crews.architecture_synthesis.base_crew import MiniCrewBase

        self._create_mock_facts(tmp_path)
        facts_path = tmp_path / "architecture_facts.json"

        loaded = MiniCrewBase._load_json(facts_path)
        assert loaded["system"]["name"] == "TestSystem"
        assert len(loaded["components"]) == 2

    def test_load_json_missing_file(self, tmp_path):
        """_load_json returns empty dict for missing files."""
        from aicodegencrew.crews.architecture_synthesis.base_crew import MiniCrewBase

        loaded = MiniCrewBase._load_json(tmp_path / "nonexistent.json")
        assert loaded == {}

    def test_load_json_invalid_json(self, tmp_path):
        """_load_json returns empty dict for invalid JSON."""
        from aicodegencrew.crews.architecture_synthesis.base_crew import MiniCrewBase

        bad_file = tmp_path / "broken.json"
        bad_file.write_text("{broken json}}}", encoding="utf-8")

        loaded = MiniCrewBase._load_json(bad_file)
        assert loaded == {}

    def test_collector_orchestrator_on_mock_repo(self, tmp_path):
        """CollectorOrchestrator produces valid DimensionResults on a mock repo."""
        from aicodegencrew.pipelines.architecture_facts.collectors.orchestrator import (
            CollectorOrchestrator,
            DimensionResults,
        )

        # Create minimal Java repo structure
        java_dir = tmp_path / "src" / "main" / "java" / "com" / "example"
        java_dir.mkdir(parents=True)

        (java_dir / "UserService.java").write_text(
            """package com.example;
import org.springframework.stereotype.Service;

@Service
public class UserService {
    public void getUser() {}
}""",
            encoding="utf-8",
        )

        (java_dir / "UserController.java").write_text(
            """package com.example;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    private final UserService userService;
    public UserController(UserService userService) {
        this.userService = userService;
    }
    @GetMapping
    public String getUsers() { return "[]"; }
}""",
            encoding="utf-8",
        )

        # build.gradle to detect Spring Boot
        (tmp_path / "build.gradle").write_text(
            """plugins { id 'org.springframework.boot' version '3.2.0' }""",
            encoding="utf-8",
        )

        output_dir = tmp_path / "output"
        orchestrator = CollectorOrchestrator(repo_path=tmp_path, output_dir=output_dir)
        results = orchestrator.run_all()

        assert isinstance(results, DimensionResults)
        stats = results.get_statistics()
        # Should find at least the two Java components
        assert stats["components"] >= 1
        # Should find at least one container
        assert stats["containers"] >= 1

    def test_dimension_results_statistics(self):
        """DimensionResults.get_statistics returns dict with all dimension keys."""
        from aicodegencrew.pipelines.architecture_facts.collectors.orchestrator import (
            DimensionResults,
        )

        results = DimensionResults()
        stats = results.get_statistics()

        expected_keys = [
            "subsystems",
            "containers",
            "components",
            "interfaces",
            "entities",
            "tables",
            "migrations",
            "runtime_facts",
            "infrastructure_facts",
            "dependencies",
            "workflows",
            "tech_versions",
            "security_details",
            "validation",
            "tests",
            "error_handling",
            "relation_hints",
            "evidence_items",
        ]
        for key in expected_keys:
            assert key in stats, f"Missing stat key: {key}"
            assert isinstance(stats[key], int)


# =============================================================================
# Phase 2 -> Phase 3  data flow
# =============================================================================


class TestPhase2ToPhase3:
    """Validates analyzed_architecture.json and MiniCrewBase._load_json."""

    def _create_mock_analyzed(self, output_dir: Path) -> dict:
        """Create a minimal analyzed_architecture.json matching the current schema."""
        analyzed = {
            "macro_architecture": {
                "style": "Layered + Modular",
                "layers": ["Presentation", "Application", "Domain", "Data Access"],
            },
            "micro_architecture": {
                "layers": {
                    "presentation": {"components": 10},
                    "application": {"components": 15},
                    "domain": {"components": 20},
                    "data_access": {"components": 8},
                },
            },
            "container_analyses": [
                {"container": "backend", "style": "MVC", "patterns": ["Repository Pattern"]},
            ],
            "quality": {
                "grade": "B",
                "metrics": {
                    "layer_compliance": 0.85,
                },
            },
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "analyzed_architecture.json"
        path.write_text(json.dumps(analyzed, indent=2), encoding="utf-8")
        return analyzed

    def test_analyzed_json_has_required_keys(self, tmp_path):
        """analyzed_architecture.json must have current required keys."""
        analyzed = self._create_mock_analyzed(tmp_path)
        assert "macro_architecture" in analyzed
        assert "micro_architecture" in analyzed
        assert "container_analyses" in analyzed

    def test_analyzed_json_architecture_has_style(self, tmp_path):
        """macro_architecture section must have style field."""
        analyzed = self._create_mock_analyzed(tmp_path)
        assert "style" in analyzed["macro_architecture"]

    def test_analyzed_json_readable_by_load_json(self, tmp_path):
        """MiniCrewBase._load_json can read analyzed JSON."""
        from aicodegencrew.crews.architecture_synthesis.base_crew import MiniCrewBase

        self._create_mock_analyzed(tmp_path)
        path = tmp_path / "analyzed_architecture.json"

        loaded = MiniCrewBase._load_json(path)
        assert loaded["macro_architecture"]["style"] == "Layered + Modular"
        assert "container_analyses" in loaded

    def test_phase_validation_analyzed_structure(self, tmp_path, monkeypatch):
        """PhaseOutputValidator spec has current required keys for analyzed JSON."""
        from aicodegencrew.shared.validation import PHASE_OUTPUT_SPECS

        spec = PHASE_OUTPUT_SPECS["analyze"]
        assert "required_keys" in spec
        assert "macro_architecture" in spec["required_keys"]
        assert "micro_architecture" in spec["required_keys"]
        assert "quality" in spec["required_keys"]
        assert "executive_summary" in spec["required_keys"]

    def test_synthesis_crew_detects_missing_prerequisites(self, tmp_path):
        """ArchitectureSynthesisCrew raises FileNotFoundError on missing inputs."""
        from aicodegencrew.crews.architecture_synthesis.crew import (
            ArchitectureSynthesisCrew,
        )

        crew = ArchitectureSynthesisCrew(facts_path=str(tmp_path / "nonexistent" / "facts.json"))
        with pytest.raises(FileNotFoundError, match="Missing prerequisite"):
            crew._validate_prerequisites()


# =============================================================================
# Phase 4  pipeline stages flow
# =============================================================================


class TestPhase4StageFlow:
    """Tests Stage 1->2->3->5 data flow without LLM (Stage 4 is mocked)."""

    @pytest.fixture
    def mock_facts(self):
        """Minimal architecture_facts.json for Phase 4 stages."""
        return {
            "system": {"name": "TestSystem"},
            "containers": [
                {
                    "id": "backend",
                    "name": "backend",
                    "type": "application",
                    "technology": "Spring Boot",
                }
            ],
            "components": [
                {
                    "id": "comp.backend.UserService",
                    "name": "UserService",
                    "stereotype": "service",
                    "layer": "application",
                    "container": "container.backend",
                    "module": "com.example.service",
                    "file_path": "src/main/java/com/example/UserService.java",
                    "file_paths": [
                        "src/main/java/com/example/UserService.java",
                    ],
                },
                {
                    "id": "comp.backend.UserController",
                    "name": "UserController",
                    "stereotype": "controller",
                    "layer": "presentation",
                    "container": "container.backend",
                    "module": "com.example.controller",
                    "file_path": "src/main/java/com/example/UserController.java",
                    "file_paths": [
                        "src/main/java/com/example/UserController.java",
                    ],
                },
                {
                    "id": "comp.backend.UserEntity",
                    "name": "UserEntity",
                    "stereotype": "entity",
                    "layer": "domain",
                    "container": "container.backend",
                    "module": "com.example.domain",
                    "file_path": "src/main/java/com/example/UserEntity.java",
                    "file_paths": [
                        "src/main/java/com/example/UserEntity.java",
                    ],
                },
            ],
            "interfaces": [
                {
                    "id": "iface.rest.GET./api/users",
                    "type": "REST",
                    "path": "/api/users",
                    "method": "GET",
                    "implemented_by": "UserController",
                },
            ],
            "relations": [
                {
                    "from": "comp.backend.UserController",
                    "to": "comp.backend.UserService",
                    "type": "uses",
                },
            ],
            "tests": [
                {
                    "name": "UserServiceTest",
                    "test_type": "unit",
                    "framework": "junit",
                    "file_path": "src/test/java/com/example/UserServiceTest.java",
                    "scenarios": ["testGetUser", "testCreateUser"],
                    "tested_component_hint": "UserService",
                },
            ],
            "security_details": [
                {
                    "name": "UserController.getUsers",
                    "security_type": "pre_authorize",
                    "roles": ["ROLE_USER"],
                    "class_name": "UserController",
                    "file_path": "src/main/java/com/example/UserController.java",
                },
            ],
            "validation": [
                {
                    "name": "UserEntity.email",
                    "validation_type": "not_blank",
                    "target_class": "UserEntity",
                    "target_field": "email",
                },
            ],
            "error_handling": [
                {
                    "name": "GlobalExceptionHandler",
                    "handling_type": "controller_advice",
                    "exception_class": "RuntimeException",
                    "handler_method": "handleRuntime",
                },
            ],
            "workflows": [],
            "data_model": {"entities": [], "tables": [], "migrations": []},
            "runtime": [],
            "infrastructure": [],
            "dependencies": [],
            "tech_versions": [],
            "evidence": {},
            "statistics": {"components": 3, "interfaces": 1},
        }

    def test_stage1_parses_text_file(self, tmp_path):
        """Stage 1 InputParserStage can parse a .txt task file."""
        from aicodegencrew.hybrid.development_planning.schemas import TaskInput
        from aicodegencrew.hybrid.development_planning.stages import (
            InputParserStage,
        )

        task_file = tmp_path / "TASK-001.txt"
        task_file.write_text(
            "Implement user authentication with JWT tokens.\nThe UserService needs a new login method.\n",
            encoding="utf-8",
        )

        stage1 = InputParserStage()
        task = stage1.run(str(task_file))

        assert isinstance(task, TaskInput)
        assert task.task_id == "TASK-001"
        assert task.source_format == "text"
        assert "authentication" in task.description.lower() or "authentication" in task.summary.lower()

    def test_stage1_detects_upgrade_type(self, tmp_path):
        """Stage 1 detects upgrade task type from content."""
        from aicodegencrew.hybrid.development_planning.stages import (
            InputParserStage,
        )

        task_file = tmp_path / "TASK-002.txt"
        task_file.write_text(
            "Angular upgrade from version 16 to version 17.\nBreaking changes in Angular router.\n",
            encoding="utf-8",
        )

        stage1 = InputParserStage()
        task = stage1.run(str(task_file))
        assert task.task_type == "upgrade"

    def test_stage1_detects_bugfix_type(self, tmp_path):
        """Stage 1 detects bugfix task type."""
        from aicodegencrew.hybrid.development_planning.stages import (
            InputParserStage,
        )

        task_file = tmp_path / "BUG-003.txt"
        task_file.write_text(
            "Fix null pointer error in UserService.getUser()\nNullPointerException at line 42.\n",
            encoding="utf-8",
        )

        stage1 = InputParserStage()
        task = stage1.run(str(task_file))
        assert task.task_type == "bugfix"

    def test_stage2_component_discovery_no_chromadb(self, mock_facts):
        """Stage 2 works with facts-only scoring when ChromaDB is unavailable."""
        from aicodegencrew.hybrid.development_planning.schemas import TaskInput
        from aicodegencrew.hybrid.development_planning.stages import (
            ComponentDiscoveryStage,
        )

        stage2 = ComponentDiscoveryStage(
            facts=mock_facts,
            chroma_dir="/nonexistent/chroma",
        )

        task = TaskInput(
            task_id="TEST-001",
            source_file="test.txt",
            source_format="text",
            summary="Fix UserService authentication bug",
            description="UserService.login() throws NullPointerException",
        )

        result = stage2.run(task, top_k=5)
        assert "affected_components" in result
        assert "interfaces" in result
        assert "dependencies" in result
        assert isinstance(result["affected_components"], list)

    def test_stage3_pattern_matcher_returns_all_categories(self, mock_facts):
        """Stage 3 returns test_patterns, security_patterns, etc."""
        from aicodegencrew.hybrid.development_planning.schemas import TaskInput
        from aicodegencrew.hybrid.development_planning.stages import (
            PatternMatcherStage,
        )

        stage3 = PatternMatcherStage(facts=mock_facts)

        task = TaskInput(
            task_id="TEST-001",
            source_file="test.txt",
            source_format="text",
            summary="Add user profile endpoint",
            description="New REST endpoint for user profile data",
        )

        # Simulated Stage 2 output
        components = [
            {
                "id": "comp.backend.UserService",
                "name": "UserService",
                "stereotype": "service",
                "layer": "application",
                "file_path": "src/main/java/com/example/UserService.java",
            },
        ]

        result = stage3.run(task, components, top_k=5)

        assert "test_patterns" in result
        assert "security_patterns" in result
        assert "validation_patterns" in result
        assert "error_patterns" in result
        assert isinstance(result["test_patterns"], list)
        assert isinstance(result["security_patterns"], list)

    def test_stage5_validates_valid_plan(self):
        """Stage 5 validates a well-formed plan as valid."""
        from aicodegencrew.hybrid.development_planning.schemas import (
            ImplementationPlan,
            ValidationResult,
        )
        from aicodegencrew.hybrid.development_planning.stages import ValidatorStage

        stage5 = ValidatorStage(analyzed_architecture={})

        plan = ImplementationPlan(
            task_id="TEST-001",
            source_files=["test.txt"],
            understanding={
                "summary": "Add user profile",
                "requirements": ["REST endpoint"],
            },
            development_plan={
                "affected_components": [
                    {
                        "id": "comp.backend.UserService",
                        "name": "UserService",
                        "stereotype": "service",
                        "layer": "application",
                    }
                ],
                "implementation_steps": [
                    "1. Add getProfile() to UserService",
                    "2. Add /api/users/profile endpoint to UserController",
                ],
                "test_strategy": {
                    "unit_tests": ["UserServiceTest.testGetProfile"],
                    "integration_tests": ["UserControllerIT.testProfileEndpoint"],
                },
                "estimated_complexity": "Medium",
                "estimated_files_changed": 3,
                "security_considerations": [],
                "validation_strategy": [],
                "error_handling": [],
                "architecture_context": {"layer_compliance": True},
                "risks": ["Breaking existing tests"],
            },
        )

        result = stage5.run(plan)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_stage5_rejects_empty_components(self):
        """Stage 5 rejects plans with no affected components."""
        from aicodegencrew.hybrid.development_planning.schemas import (
            ImplementationPlan,
        )
        from aicodegencrew.hybrid.development_planning.stages import ValidatorStage

        stage5 = ValidatorStage()

        plan = ImplementationPlan(
            task_id="TEST-002",
            source_files=["test.txt"],
            understanding={"summary": "test"},
            development_plan={
                "affected_components": [],
                "implementation_steps": ["Do something"],
                "test_strategy": {"unit_tests": []},
                "estimated_complexity": "Low",
                "estimated_files_changed": 1,
            },
        )

        result = stage5.run(plan)
        assert result.is_valid is False
        assert any("component" in e.lower() for e in result.errors)

    def test_stage_chain_1_to_3_with_mock_data(self, tmp_path, mock_facts):
        """Full Stage 1 -> 2 -> 3 chain with mock data (no LLM)."""
        from aicodegencrew.hybrid.development_planning.stages import (
            ComponentDiscoveryStage,
            InputParserStage,
            PatternMatcherStage,
        )

        # Stage 1: Parse input
        task_file = tmp_path / "FEAT-100.txt"
        task_file.write_text(
            "Add UserService caching layer for performance improvement.\nThe UserService response time is too slow.\n",
            encoding="utf-8",
        )

        stage1 = InputParserStage()
        task = stage1.run(str(task_file))
        assert task.task_type == "feature"

        # Stage 2: Discover components
        stage2 = ComponentDiscoveryStage(
            facts=mock_facts,
            chroma_dir="/nonexistent",
        )
        discovery = stage2.run(task, top_k=5)
        assert "affected_components" in discovery

        # Stage 3: Match patterns
        stage3 = PatternMatcherStage(facts=mock_facts)
        patterns = stage3.run(task, discovery["affected_components"], top_k=5)
        assert "test_patterns" in patterns
        assert "security_patterns" in patterns

    def test_task_input_schema_roundtrip(self):
        """TaskInput can be serialized and deserialized."""
        from aicodegencrew.hybrid.development_planning.schemas import TaskInput

        task = TaskInput(
            task_id="PROJ-456",
            source_file="/path/to/file.xml",
            source_format="xml",
            summary="Implement password reset",
            description="Add forgot-password flow",
            acceptance_criteria=["AC1: email sent", "AC2: link expires"],
            labels=["security", "authentication"],
            priority="Major",
            task_type="feature",
        )

        task_dict = task.dict()
        restored = TaskInput(**task_dict)

        assert restored.task_id == "PROJ-456"
        assert len(restored.acceptance_criteria) == 2
        assert restored.task_type == "feature"


# =============================================================================
# Confluence converter integration
# =============================================================================


class TestConfluenceConverterIntegration:
    """Tests DocumentConverter on realistic markdown content."""

    SAMPLE_ARCH_MD = """\
# C4 Context Diagram

## System Overview

The **Sample System** is a multi-tier web application.

### External Actors

| Actor | Description | Protocol |
|-------|-------------|----------|
| User | End user accessing via browser | HTTPS |
| Admin | System administrator | SSH/HTTPS |

### Containers

- **Backend**: Spring Boot REST API
- **Frontend**: Angular SPA
  - Uses REST for data
- **Database**: Oracle 19c

```java
@RestController
@RequestMapping("/api")
public class MainController {
    // Entry point
}
```

> This is a blockquote about architecture decisions.

---

1. First constraint
2. Second constraint
"""

    def test_convert_to_confluence(self):
        """Markdown converts to Confluence Wiki Markup."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.to_confluence(self.SAMPLE_ARCH_MD)

        # Verify key Confluence formatting
        assert "h1. C4 Context Diagram" in result
        assert "h2. System Overview" in result
        assert "*Sample System*" in result  # bold
        assert "||Actor||Description||Protocol||" in result  # table header
        assert "{code:language=java}" in result  # code block
        assert "{quote}" in result  # blockquote
        assert "----" in result  # horizontal rule

    def test_convert_to_asciidoc(self):
        """Markdown converts to AsciiDoc."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.to_asciidoc(self.SAMPLE_ARCH_MD)

        assert "= C4 Context Diagram" in result  # h1
        assert "== System Overview" in result  # h2
        assert "|===" in result  # table delimiter
        assert "[source,java]" in result  # code block
        assert "----" in result  # code block delimiter
        assert "[quote]" in result  # blockquote

    def test_convert_to_html(self):
        """Markdown converts to standalone HTML."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.to_html(self.SAMPLE_ARCH_MD, title="Test Doc")

        assert "<!DOCTYPE html>" in result
        assert "<title>Test Doc</title>" in result
        assert "<h1>" in result or "<h1" in result
        assert "<table>" in result or "<table" in result
        assert "<code>" in result or "<pre>" in result

    def test_convert_file_creates_all_formats(self, tmp_path):
        """convert_file creates .confluence, .adoc, and .html alongside .md."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        md_path = tmp_path / "c4-context.md"
        md_path.write_text(self.SAMPLE_ARCH_MD, encoding="utf-8")

        converter = DocumentConverter()
        results = converter.convert_file(md_path)

        assert "confluence" in results
        assert "adoc" in results
        assert "html" in results

        # Verify files exist
        assert (tmp_path / "c4-context.confluence").exists()
        assert (tmp_path / "c4-context.adoc").exists()
        assert (tmp_path / "c4-context.html").exists()

        # Verify non-empty
        for fmt, path in results.items():
            assert path.stat().st_size > 0, f"{fmt} file is empty"

    def test_convert_directory_generates_arc42_toc(self, tmp_path):
        """convert_directory generates ToC when arc42/ subdirectory exists."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        # Create arc42 directory with sample chapters
        arc42_dir = tmp_path / "arc42"
        arc42_dir.mkdir()

        for ch_num in ["01", "02", "03"]:
            (arc42_dir / f"{ch_num}-chapter.md").write_text(
                f"# Chapter {ch_num}\n\nContent here.\n",
                encoding="utf-8",
            )

        converter = DocumentConverter()
        total = converter.convert_directory(tmp_path, lang="en")

        # Should generate 3 formats per 3 files = 9, plus 3 ToC files = 12
        assert total >= 9  # At least the 9 converted files

        # Check ToC files created
        assert (arc42_dir / "00-arc42-toc.confluence").exists()
        assert (arc42_dir / "00-arc42-toc.adoc").exists()
        assert (arc42_dir / "00-arc42-toc.html").exists()

    def test_convert_directory_german_language(self, tmp_path):
        """German arc42 ToC uses German chapter titles."""
        from aicodegencrew.shared.utils.confluence_converter import (
            DocumentConverter,
        )

        arc42_dir = tmp_path / "arc42"
        arc42_dir.mkdir()
        (arc42_dir / "01-intro.md").write_text("# Intro\n", encoding="utf-8")

        converter = DocumentConverter()
        converter.convert_directory(tmp_path, lang="de")

        toc_conf = arc42_dir / "00-arc42-toc.confluence"
        if toc_conf.exists():
            content = toc_conf.read_text(encoding="utf-8")
            # German chapters use German titles
            assert "Architekturdokumentation" in content

    def test_convert_real_phase3_output_if_available(self):
        """Convert actual Phase 3 output if the knowledge directory exists."""
        from aicodegencrew.shared.utils.confluence_converter import DocumentConverter

        arch_dir = Path("knowledge/architecture")
        if not arch_dir.exists():
            pytest.skip("No knowledge/architecture directory available")

        c4_dir = arch_dir / "c4"
        if not c4_dir.exists() or not list(c4_dir.glob("*.md")):
            pytest.skip("No C4 markdown files available")

        converter = DocumentConverter()
        results = converter.convert_file(next(iter(c4_dir.glob("*.md"))))

        assert len(results) >= 1
        for fmt, path in results.items():
            assert path.exists(), f"{fmt} output not created"
            assert path.stat().st_size > 0, f"{fmt} output is empty"


# =============================================================================
# Pydantic schema validation (Phase 1 output)
# =============================================================================


class TestArchitectureFactsSchema:
    """Validates ArchitectureFacts Pydantic schema."""

    def test_valid_facts_schema(self):
        """Valid architecture facts pass Pydantic validation."""
        from aicodegencrew.shared.models.architecture_facts_schema import (
            ArchitectureFacts,
            Component,
            Container,
            SystemInfo,
        )

        facts = ArchitectureFacts(
            system=SystemInfo(name="TestSystem"),
            containers=[
                Container(
                    id="backend",
                    name="Backend",
                    technology="Spring Boot",
                    evidence=["ev_001"],
                )
            ],
            components=[
                Component(
                    id="comp.svc",
                    container="backend",
                    name="UserService",
                    stereotype="service",
                    evidence=["ev_001"],
                )
            ],
        )

        assert facts.system.name == "TestSystem"
        assert len(facts.containers) == 1
        assert len(facts.components) == 1

    def test_evidence_validation_finds_broken_refs(self):
        """validate_evidence catches references to nonexistent evidence."""
        from aicodegencrew.shared.models.architecture_facts_schema import (
            ArchitectureFacts,
            Container,
            SystemInfo,
        )

        facts = ArchitectureFacts(
            system=SystemInfo(name="Test"),
            containers=[
                Container(
                    id="backend",
                    name="Backend",
                    technology="Spring Boot",
                    evidence=["ev_999"],  # does not exist
                )
            ],
        )

        errors = facts.validate_evidence({"ev_001": {}})
        assert len(errors) > 0
        assert any("ev_999" in e for e in errors)

    def test_evidence_validation_passes_when_all_exist(self):
        """validate_evidence returns empty list when all references exist."""
        from aicodegencrew.shared.models.architecture_facts_schema import (
            ArchitectureFacts,
            Component,
            Container,
            SystemInfo,
        )

        facts = ArchitectureFacts(
            system=SystemInfo(name="Test"),
            containers=[
                Container(
                    id="backend",
                    name="Backend",
                    technology="Spring Boot",
                    evidence=["ev_001"],
                )
            ],
            components=[
                Component(
                    id="comp.svc",
                    container="backend",
                    name="Svc",
                    stereotype="service",
                    evidence=["ev_002"],
                )
            ],
        )

        errors = facts.validate_evidence({"ev_001": {}, "ev_002": {}})
        assert errors == []
