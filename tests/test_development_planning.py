"""Tests for Phase 4 Development Planning Pipeline (stages 1-3, 5).

All stages tested here are deterministic — no LLM or ChromaDB needed.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aicodegencrew.pipelines.development_planning.schemas import (
    TaskInput,
    ComponentMatch,
    ImplementationPlan,
    ValidationResult,
)

# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

SAMPLE_FACTS = {
    "system": {"name": "TestSystem"},
    "containers": [
        {"id": "container.backend", "name": "Backend", "technology": "Spring Boot"},
        {"id": "container.frontend", "name": "Frontend", "technology": "Angular"},
    ],
    "components": [
        {
            "id": "comp.user_service",
            "name": "UserService",
            "stereotype": "service",
            "layer": "application",
            "package": "com.example.user",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/user/UserService.java",
        },
        {
            "id": "comp.auth_controller",
            "name": "AuthController",
            "stereotype": "controller",
            "layer": "presentation",
            "package": "com.example.auth",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/auth/AuthController.java",
        },
        {
            "id": "comp.user_repo",
            "name": "UserRepository",
            "stereotype": "repository",
            "layer": "dataaccess",
            "package": "com.example.user",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/user/UserRepository.java",
        },
        {
            "id": "comp.user_entity",
            "name": "User",
            "stereotype": "entity",
            "layer": "domain",
            "package": "com.example.user",
            "container": "container.backend",
            "file_path": "src/main/java/com/example/user/User.java",
        },
    ],
    "interfaces": [
        {
            "id": "if.get_users",
            "type": "REST",
            "path": "/api/users",
            "method": "GET",
            "implemented_by": "comp.auth_controller",
        },
    ],
    "relations": [
        {"from": "comp.auth_controller", "to": "comp.user_service", "type": "uses"},
        {"from": "comp.user_service", "to": "comp.user_repo", "type": "uses"},
    ],
    "tests": [
        {
            "file_path": "src/test/java/com/example/user/UserServiceTest.java",
            "test_type": "unit",
            "targets": ["UserService"],
        },
    ],
    "security_details": [
        {
            "type": "authentication",
            "package": "com.example.auth",
            "detail": "Spring Security with JWT",
        },
    ],
    "validation_patterns": [
        {
            "target_class": "User",
            "pattern_name": "user.email",
            "annotation": "@Email",
            "usage_count": 3,
        },
    ],
    "error_handling_patterns": [
        {
            "handling_type": "exception_handler",
            "exception_class": "ResourceNotFoundException",
            "handler_method": "handleNotFound",
        },
    ],
    "workflows": [
        {
            "name": "User Registration",
            "components_involved": ["AuthController", "UserService"],
            "trigger": "REST POST /api/users",
        },
    ],
}


def _make_task(**overrides) -> TaskInput:
    """Create a TaskInput with defaults."""
    defaults = {
        "task_id": "TEST-001",
        "source_file": "task.xml",
        "source_format": "xml",
        "summary": "Add user profile endpoint",
        "description": "Implement REST endpoint for user profile retrieval",
        "priority": "High",
        "task_type": "feature",
        "labels": [],
        "acceptance_criteria": ["Profile data returned", "Auth required"],
    }
    defaults.update(overrides)
    return TaskInput(**defaults)


def _make_plan(**overrides) -> ImplementationPlan:
    """Create a minimal valid ImplementationPlan."""
    defaults = {
        "task_id": "TEST-001",
        "source_files": ["task.xml"],
        "understanding": {
            "task_type": "feature",
            "summary": "Add user profile endpoint",
            "scope": "Backend REST endpoint",
        },
        "development_plan": {
            "affected_components": [
                {"id": "comp.user_service", "name": "UserService", "change_type": "modify"},
            ],
            "implementation_steps": [
                {"step": 1, "description": "Add getProfile method to UserService"},
                {"step": 2, "description": "Add GET /api/users/profile endpoint"},
            ],
            "test_strategy": {
                "unit_tests": ["UserServiceTest.testGetProfile"],
                "integration_tests": ["ProfileEndpointIT"],
            },
            "estimated_complexity": "medium",
            "estimated_files_changed": 3,
            "architecture_context": {
                "layer_compliance": "presentation -> application -> dataaccess",
            },
            "security_considerations": [],
            "validation_strategy": [],
            "error_handling": [],
        },
    }
    defaults.update(overrides)
    return ImplementationPlan(**defaults)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_task_input_defaults(self):
        task = TaskInput(
            task_id="X-1",
            source_file="f.xml",
            source_format="xml",
            summary="Do something",
        )
        assert task.task_type == "feature"
        assert task.priority == "Medium"
        assert task.labels == []

    def test_task_input_all_formats(self):
        for fmt in ("xml", "docx", "excel", "text"):
            t = TaskInput(task_id="T-1", source_file="f", source_format=fmt, summary="s")
            assert t.source_format == fmt

    def test_component_match_score_range(self):
        cm = ComponentMatch(
            id="c1", name="Svc", stereotype="service", layer="app",
            relevance_score=0.85,
        )
        assert 0 <= cm.relevance_score <= 1

    def test_validation_result_valid(self):
        vr = ValidationResult(is_valid=True)
        assert vr.errors == []
        assert vr.warnings == []

    def test_validation_result_invalid(self):
        vr = ValidationResult(
            is_valid=False,
            errors=["Missing components"],
            missing_fields=["affected_components"],
        )
        assert not vr.is_valid
        assert len(vr.errors) == 1


# ---------------------------------------------------------------------------
# Stage 1: Input Parser tests
# ---------------------------------------------------------------------------

class TestInputParser:
    def test_parse_text_file(self, tmp_path):
        from aicodegencrew.pipelines.development_planning.stages.stage1_input_parser import InputParserStage

        txt = tmp_path / "TASK-100.txt"
        txt.write_text("Implement user profile page with avatar upload", encoding="utf-8")

        stage = InputParserStage()
        result = stage.run(str(txt))

        assert isinstance(result, TaskInput)
        assert result.source_format == "text"
        assert "profile" in result.summary.lower() or "profile" in result.description.lower()

    def test_parse_missing_file(self):
        from aicodegencrew.pipelines.development_planning.stages.stage1_input_parser import InputParserStage

        stage = InputParserStage()
        with pytest.raises(ValueError, match="not found"):
            stage.run("/nonexistent/file.txt")

    def test_parse_unsupported_format(self, tmp_path):
        from aicodegencrew.pipelines.development_planning.stages.stage1_input_parser import InputParserStage

        pdf = tmp_path / "task.pdf"
        pdf.write_text("dummy", encoding="utf-8")

        stage = InputParserStage()
        with pytest.raises(ValueError, match="Unsupported"):
            stage.run(str(pdf))

    def test_detect_bugfix_type(self):
        from aicodegencrew.pipelines.development_planning.stages.stage1_input_parser import InputParserStage

        stage = InputParserStage()
        task = _make_task(
            summary="Fix NullPointerException in UserService",
            description="Bug: crash when user has no email",
            task_type="feature",  # default, should be overridden
        )
        result = stage._detect_task_type(task)
        assert result.task_type == "bugfix"

    def test_detect_upgrade_type(self):
        from aicodegencrew.pipelines.development_planning.stages.stage1_input_parser import InputParserStage

        stage = InputParserStage()
        task = _make_task(
            summary="Upgrade Angular from 15 to 17",
            description="Migrate framework version, update dependencies, fix breaking changes",
            labels=["upgrade", "angular"],
            task_type="feature",
        )
        result = stage._detect_task_type(task)
        assert result.task_type == "upgrade"

    def test_detect_refactoring_type(self):
        from aicodegencrew.pipelines.development_planning.stages.stage1_input_parser import InputParserStage

        stage = InputParserStage()
        task = _make_task(
            summary="Refactor UserService to use repository pattern",
            description="Clean up and restructure the user module",
            task_type="feature",
        )
        result = stage._detect_task_type(task)
        assert result.task_type == "refactoring"

    def test_detect_feature_type_default(self):
        from aicodegencrew.pipelines.development_planning.stages.stage1_input_parser import InputParserStage

        stage = InputParserStage()
        task = _make_task(
            summary="Add dashboard widget for sales data",
            description="New widget showing monthly sales",
            task_type="feature",
        )
        result = stage._detect_task_type(task)
        assert result.task_type == "feature"


# ---------------------------------------------------------------------------
# Stage 2: Component Discovery tests (no ChromaDB)
# ---------------------------------------------------------------------------

class TestComponentDiscovery:
    def test_name_matching(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)
        scores = stage._name_matching("UserService authentication login")

        assert "comp.user_service" in scores
        assert scores["comp.user_service"] > 0

    def test_package_matching(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)
        scores = stage._package_matching(["user", "auth"])

        # Should match components in com.example.user and com.example.auth packages
        assert len(scores) > 0

    def test_stereotype_matching_controller(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)
        scores = stage._stereotype_matching("REST endpoint API controller")

        assert "comp.auth_controller" in scores
        assert scores["comp.auth_controller"] > 0

    def test_combine_scores(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)
        combined = stage._combine_scores(
            semantic={"comp.user_service": 0.8},
            name={"comp.user_service": 0.9, "comp.auth_controller": 0.3},
            package={"comp.user_service": 0.5},
            stereotype={},
        )

        assert "comp.user_service" in combined
        # Weighted: 0.8*0.4 + 0.9*0.3 + 0.5*0.2 + 0*0.1 = 0.32 + 0.27 + 0.1 = 0.69
        assert combined["comp.user_service"] > 0.5

    def test_find_interfaces(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)
        interfaces = stage._find_interfaces(["comp.auth_controller"])

        assert len(interfaces) >= 1
        assert interfaces[0].path == "/api/users"

    def test_find_dependencies(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)
        deps = stage._find_dependencies(["comp.user_service"])

        # UserService -> UserRepository
        assert len(deps) >= 1

    def test_change_type_inference(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)

        assert stage._infer_change_type("add new user endpoint") == "create"
        assert stage._infer_change_type("remove deprecated API") == "delete"
        assert stage._infer_change_type("update user validation") == "modify"

    def test_run_without_chromadb(self):
        from aicodegencrew.pipelines.development_planning.stages.stage2_component_discovery import ComponentDiscoveryStage

        stage = ComponentDiscoveryStage(facts=SAMPLE_FACTS, chroma_dir=None)
        task = _make_task(summary="Fix UserService validation", labels=["user"])

        result = stage.run(task, top_k=5)

        # Result contains components, interfaces, dependencies
        assert isinstance(result, dict)
        assert "components" in result or "interfaces" in result or "dependencies" in result


# ---------------------------------------------------------------------------
# Stage 3: Pattern Matcher tests
# ---------------------------------------------------------------------------

class TestPatternMatcher:
    def test_match_test_patterns(self):
        from aicodegencrew.pipelines.development_planning.stages.stage3_pattern_matcher import PatternMatcherStage

        stage = PatternMatcherStage(facts=SAMPLE_FACTS)
        patterns = stage._match_test_patterns(
            task_description="user profile endpoint",
            component_names=["UserService"],
            top_k=5,
        )

        assert isinstance(patterns, list)

    def test_match_security_patterns(self):
        from aicodegencrew.pipelines.development_planning.stages.stage3_pattern_matcher import PatternMatcherStage

        stage = PatternMatcherStage(facts=SAMPLE_FACTS)
        patterns = stage._match_security_patterns(
            component_paths=["com.example.auth"],
            top_k=5,
        )

        assert isinstance(patterns, list)
        if patterns:
            assert hasattr(patterns[0], "security_type") or isinstance(patterns[0], dict)

    def test_match_validation_patterns(self):
        from aicodegencrew.pipelines.development_planning.stages.stage3_pattern_matcher import PatternMatcherStage

        stage = PatternMatcherStage(facts=SAMPLE_FACTS)
        patterns = stage._match_validation_patterns(
            entity_names=["User"],
            top_k=5,
        )

        assert isinstance(patterns, list)

    def test_match_error_patterns(self):
        from aicodegencrew.pipelines.development_planning.stages.stage3_pattern_matcher import PatternMatcherStage

        stage = PatternMatcherStage(facts=SAMPLE_FACTS)
        patterns = stage._match_error_patterns(
            task_description="handle not found exception",
            top_k=5,
        )

        assert isinstance(patterns, list)

    def test_match_workflows(self):
        from aicodegencrew.pipelines.development_planning.stages.stage3_pattern_matcher import PatternMatcherStage

        stage = PatternMatcherStage(facts=SAMPLE_FACTS)
        workflows = stage._match_workflows(
            component_names=["AuthController", "UserService"],
            top_k=5,
        )

        assert isinstance(workflows, list)

    def test_run_full(self):
        from aicodegencrew.pipelines.development_planning.stages.stage3_pattern_matcher import PatternMatcherStage

        stage = PatternMatcherStage(facts=SAMPLE_FACTS)
        task = _make_task()
        components = [
            {"id": "comp.user_service", "name": "UserService", "stereotype": "service",
             "layer": "application", "file_path": "com/example/user/UserService.java"},
        ]

        result = stage.run(task, components, top_k=3)

        assert "test_patterns" in result
        assert "security_patterns" in result
        assert "validation_patterns" in result
        assert "error_patterns" in result


# ---------------------------------------------------------------------------
# Stage 5: Validator tests
# ---------------------------------------------------------------------------

class TestValidator:
    def test_valid_plan(self):
        from aicodegencrew.pipelines.development_planning.stages.stage5_validator import ValidatorStage

        stage = ValidatorStage()
        plan = _make_plan()
        # Validator checks comp_name in step — when step is a string, `in` checks substring
        plan.development_plan["implementation_steps"] = [
            "Modify UserService to add getProfile method",
            "Add GET /api/users/profile endpoint",
        ]
        # Fill recommended fields to avoid warnings
        plan.development_plan["risks"] = ["Low risk"]

        result = stage.run(plan)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_components(self):
        from aicodegencrew.pipelines.development_planning.stages.stage5_validator import ValidatorStage

        stage = ValidatorStage()
        plan = _make_plan()
        plan.development_plan["affected_components"] = []

        result = stage.run(plan)

        assert result.is_valid is False
        assert any("component" in e.lower() for e in result.errors)

    def test_missing_steps(self):
        from aicodegencrew.pipelines.development_planning.stages.stage5_validator import ValidatorStage

        stage = ValidatorStage()
        plan = _make_plan()
        plan.development_plan["implementation_steps"] = []

        result = stage.run(plan)

        assert result.is_valid is False

    def test_missing_complexity(self):
        from aicodegencrew.pipelines.development_planning.stages.stage5_validator import ValidatorStage

        stage = ValidatorStage()
        plan = _make_plan()
        del plan.development_plan["estimated_complexity"]

        result = stage.run(plan)

        assert result.is_valid is False

    def test_warnings_for_optional_fields(self):
        from aicodegencrew.pipelines.development_planning.stages.stage5_validator import ValidatorStage

        stage = ValidatorStage()
        plan = _make_plan()
        plan.development_plan.pop("security_considerations", None)
        plan.development_plan.pop("error_handling", None)

        result = stage.run(plan)

        # Should still be valid but with warnings
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# Pipeline integration tests (task sorting)
# ---------------------------------------------------------------------------

class TestPipelineSorting:
    def test_sort_by_priority(self):
        from aicodegencrew.pipelines.development_planning.pipeline import DevelopmentPlanningPipeline

        pipeline = DevelopmentPlanningPipeline.__new__(DevelopmentPlanningPipeline)

        tasks = [
            _make_task(task_id="LOW-1", priority="Low"),
            _make_task(task_id="CRIT-1", priority="Critical"),
            _make_task(task_id="HIGH-1", priority="High"),
        ]

        sorted_tasks = pipeline._sort_tasks(tasks)

        assert sorted_tasks[0].task_id == "CRIT-1"
        assert sorted_tasks[-1].task_id == "LOW-1"

    def test_sort_by_type(self):
        from aicodegencrew.pipelines.development_planning.pipeline import DevelopmentPlanningPipeline

        pipeline = DevelopmentPlanningPipeline.__new__(DevelopmentPlanningPipeline)

        tasks = [
            _make_task(task_id="FEAT-1", priority="Medium", task_type="feature"),
            _make_task(task_id="UPG-1", priority="Medium", task_type="upgrade"),
            _make_task(task_id="BUG-1", priority="Medium", task_type="bugfix"),
        ]

        sorted_tasks = pipeline._sort_tasks(tasks)

        # Upgrades should come before bugfixes, which come before features
        types = [t.task_type for t in sorted_tasks]
        assert types.index("upgrade") < types.index("bugfix")
        assert types.index("bugfix") < types.index("feature")
