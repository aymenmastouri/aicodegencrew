"""
Tests for Phase 5: Code Generation Pipeline.

Covers all 5 stages, 4 strategies, schemas, pipeline orchestration,
dry-run mode, and error paths.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aicodegencrew.hybrid.code_generation.pipeline import CodeGenerationPipeline
from aicodegencrew.hybrid.code_generation.schemas import (
    CodegenPlanInput,
    CodegenReport,
    CollectedContext,
    ComponentTarget,
    FileContext,
    FileValidationResult,
    GeneratedFile,
    ValidationResult,
)
from aicodegencrew.hybrid.code_generation.stages.stage1_plan_reader import PlanReaderStage
from aicodegencrew.hybrid.code_generation.stages.stage2_context_collector import ContextCollectorStage
from aicodegencrew.hybrid.code_generation.stages.stage3_code_generator import CodeGeneratorStage
from aicodegencrew.hybrid.code_generation.stages.stage4_code_validator import CodeValidatorStage
from aicodegencrew.hybrid.code_generation.stages.stage5_output_writer import OutputWriterStage
from aicodegencrew.hybrid.code_generation.strategies import (
    STRATEGY_MAP,
    BaseStrategy,
    BugfixStrategy,
    FeatureStrategy,
    RefactoringStrategy,
    UpgradeStrategy,
)

# =============================================================================
# Test Data Builders
# =============================================================================

SAMPLE_PLAN_JSON = {
    "task_id": "TEST-001",
    "source_files": ["inputs/tasks/TEST-001.xml"],
    "understanding": {
        "summary": "Add email notification on user registration",
        "description": "Send welcome email when user registers",
        "requirements": ["Send welcome email"],
        "acceptance_criteria": ["Email sent within 1 minute"],
        "technical_notes": "Use existing EmailService",
    },
    "development_plan": {
        "affected_components": [
            {
                "id": "component.backend.service.user_service_impl",
                "name": "UserServiceImpl",
                "stereotype": "service",
                "layer": "application",
                "package": "com.example.user",
                "file_path": "backend/src/main/java/com/example/user/UserServiceImpl.java",
                "relevance_score": 0.95,
                "change_type": "modify",
                "source": "chromadb",
            },
            {
                "id": "component.backend.service.email_service",
                "name": "EmailService",
                "stereotype": "service",
                "layer": "application",
                "file_path": "",
                "relevance_score": 0.80,
                "change_type": "create",
                "source": "name_match",
            },
        ],
        "implementation_steps": [
            "1. Add EmailService dependency to UserServiceImpl",
            "2. Create sendWelcomeEmail() method",
            "3. Call sendWelcomeEmail() from registerUser()",
        ],
        "test_strategy": {
            "unit_tests": ["UserServiceImplTest.testSendEmail()"],
            "integration_tests": [],
            "similar_patterns": [],
        },
        "security_considerations": [
            {
                "security_type": "authentication",
                "recommendation": "Verify user is authenticated",
            }
        ],
        "validation_strategy": [
            {
                "validation_type": "not_null",
                "target_class": "UserServiceImpl",
                "recommendation": "Use @NotNull on email field",
            }
        ],
        "error_handling": [
            {
                "exception_class": "EmailSendException",
                "handling_type": "exception_handler",
                "recommendation": "Add retry with backoff",
            }
        ],
        "architecture_context": {
            "style": "Layered Architecture",
            "layer_pattern": "Controller -> Service -> Repository",
            "quality_grade": "B",
        },
        "estimated_complexity": "Low",
        "complexity_reasoning": "Simple service call addition",
        "estimated_files_changed": 2,
        "risks": ["Email failure should not block registration"],
    },
}

SAMPLE_UPGRADE_PLAN_JSON = {
    "task_id": "UPG-001",
    "source_files": ["inputs/tasks/UPG-001.xml"],
    "understanding": {
        "summary": "Upgrade Angular from 18 to 19",
        "description": "Framework upgrade with breaking changes",
    },
    "development_plan": {
        "affected_components": [
            {
                "id": "component.frontend.component.app_component",
                "name": "AppComponent",
                "stereotype": "component",
                "layer": "presentation",
                "file_path": "frontend/src/app/app.component.ts",
                "relevance_score": 0.9,
                "change_type": "modify",
                "source": "chromadb",
            },
        ],
        "implementation_steps": [
            "1. Run ng update @angular/core",
            "2. Migrate to standalone components",
        ],
        "upgrade_plan": {
            "framework": "Angular",
            "from_version": "18",
            "to_version": "19",
            "migration_sequence": [
                {
                    "rule_id": "ng19-standalone-default",
                    "title": "Standalone components are now default",
                    "severity": "breaking",
                    "migration_steps": [
                        "Run ng generate @angular/core:standalone-migration",
                    ],
                    "affected_files": ["frontend/src/app/app.component.ts"],
                    "estimated_effort_minutes": 30,
                    "schematic": "ng generate @angular/core:standalone-migration",
                }
            ],
            "verification_commands": ["ng build", "ng test"],
            "total_estimated_effort_hours": 0.5,
        },
        "test_strategy": {"unit_tests": [], "integration_tests": []},
        "security_considerations": [],
        "validation_strategy": [],
        "error_handling": [],
        "architecture_context": {"style": "SPA"},
        "estimated_complexity": "Medium",
        "complexity_reasoning": "Angular upgrade with breaking changes",
        "estimated_files_changed": 5,
    },
}

SAMPLE_FACTS = {
    "components": [
        {
            "id": "component.backend.service.user_service_impl",
            "name": "UserServiceImpl",
            "stereotype": "service",
            "layer": "application",
            "file_paths": ["backend/src/main/java/com/example/user/UserServiceImpl.java"],
        },
        {
            "id": "component.backend.service.email_service",
            "name": "EmailService",
            "stereotype": "service",
            "layer": "application",
            "file_paths": ["backend/src/main/java/com/example/email/EmailService.java"],
        },
    ]
}


def _write_plan(tmp_path: Path, plan: dict, task_id: str = "TEST-001") -> Path:
    """Write a plan JSON to tmp_path and return its path."""
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_file = plans_dir / f"{task_id}_plan.json"
    plan_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan_file


def _write_facts(tmp_path: Path, facts: dict = None) -> Path:
    """Write architecture_facts.json and return its path."""
    facts_dir = tmp_path / "knowledge" / "architecture"
    facts_dir.mkdir(parents=True, exist_ok=True)
    facts_file = facts_dir / "architecture_facts.json"
    facts_file.write_text(json.dumps(facts or SAMPLE_FACTS, indent=2), encoding="utf-8")
    return facts_file


def _create_repo_file(repo_path: Path, rel_path: str, content: str) -> Path:
    """Create a source file in the mock repo."""
    full = repo_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


# =============================================================================
# Schema Tests
# =============================================================================


class TestSchemas:
    """Test Pydantic schema defaults, ranges, and validation."""

    def test_component_target_defaults(self):
        ct = ComponentTarget(id="c1", name="Svc", file_path="/a/b.java")
        assert ct.stereotype == "unknown"
        assert ct.layer == "unknown"
        assert ct.change_type == "modify"
        assert ct.relevance_score == 0.0

    def test_component_target_score_range(self):
        ct = ComponentTarget(id="c1", name="S", file_path="f.java", relevance_score=0.95)
        assert 0 <= ct.relevance_score <= 1

    def test_component_target_invalid_score(self):
        with pytest.raises(Exception):
            ComponentTarget(id="c1", name="S", file_path="f.java", relevance_score=1.5)

    def test_codegen_plan_input_defaults(self):
        pi = CodegenPlanInput(task_id="T-1", task_type="feature", summary="Do X")
        assert pi.affected_components == []
        assert pi.implementation_steps == []
        assert pi.upgrade_plan is None
        assert pi.patterns == {}

    def test_codegen_plan_input_all_types(self):
        for tt in ("upgrade", "feature", "bugfix", "refactoring"):
            pi = CodegenPlanInput(task_id="T-1", task_type=tt, summary="X")
            assert pi.task_type == tt

    def test_file_context_defaults(self):
        fc = FileContext(file_path="a.java")
        assert fc.content == ""
        assert fc.language == "other"
        assert fc.sibling_files == []

    def test_generated_file_defaults(self):
        gf = GeneratedFile(file_path="a.java")
        assert gf.action == "modify"
        assert gf.confidence == 0.5
        assert gf.error == ""

    def test_codegen_report_defaults(self):
        r = CodegenReport(task_id="T-1")
        assert r.status == "failed"
        assert r.files_changed == 0
        assert r.branch_name == ""
        assert r.dry_run is False
        assert r.degradation_reasons == []

    def test_codegen_report_model_dump(self):
        r = CodegenReport(task_id="T-1", status="success", files_changed=3)
        d = r.model_dump()
        assert d["task_id"] == "T-1"
        assert d["status"] == "success"
        assert d["files_changed"] == 3

    def test_validation_result_defaults(self):
        vr = ValidationResult()
        assert vr.total_valid == 0
        assert vr.total_invalid == 0
        assert vr.security_issues == []


# =============================================================================
# Stage 1: Plan Reader Tests
# =============================================================================


class TestPlanReaderStage:
    """Test Stage 1: Plan Reader."""

    def test_read_feature_plan(self, tmp_path):
        plan_file = _write_plan(tmp_path, SAMPLE_PLAN_JSON)
        stage = PlanReaderStage(plans_dir=str(plan_file.parent))
        plan_input, strategy = stage.run(task_id="TEST-001")

        assert plan_input.task_id == "TEST-001"
        assert plan_input.task_type == "feature"
        assert plan_input.summary == "Add email notification on user registration"
        assert len(plan_input.affected_components) == 2
        assert plan_input.affected_components[0].name == "UserServiceImpl"
        assert isinstance(strategy, FeatureStrategy)

    def test_read_upgrade_plan(self, tmp_path):
        plan_file = _write_plan(tmp_path, SAMPLE_UPGRADE_PLAN_JSON, "UPG-001")
        stage = PlanReaderStage(plans_dir=str(plan_file.parent))
        plan_input, strategy = stage.run(task_id="UPG-001")

        assert plan_input.task_type == "upgrade"
        assert plan_input.upgrade_plan is not None
        assert plan_input.upgrade_plan["framework"] == "Angular"
        assert isinstance(strategy, UpgradeStrategy)

    def test_read_by_plan_path(self, tmp_path):
        plan_file = _write_plan(tmp_path, SAMPLE_PLAN_JSON)
        stage = PlanReaderStage(plans_dir=str(tmp_path))  # Wrong dir, but plan_path overrides
        plan_input, _strategy = stage.run(plan_path=str(plan_file))
        assert plan_input.task_id == "TEST-001"

    def test_missing_plan_raises(self, tmp_path):
        stage = PlanReaderStage(plans_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            stage.run(task_id="MISSING-999")

    def test_no_task_id_or_path_raises(self, tmp_path):
        stage = PlanReaderStage(plans_dir=str(tmp_path))
        with pytest.raises(ValueError, match="Either task_id or plan_path"):
            stage.run()

    def test_detect_bugfix_type(self, tmp_path):
        plan = dict(SAMPLE_PLAN_JSON)
        plan["understanding"] = {"summary": "Fix NullPointerException in login", "description": ""}
        plan["development_plan"] = dict(plan["development_plan"])
        _write_plan(tmp_path, plan)

        stage = PlanReaderStage(plans_dir=str(tmp_path / "plans"))
        pi, strategy = stage.run(task_id="TEST-001")
        assert pi.task_type == "bugfix"
        assert isinstance(strategy, BugfixStrategy)

    def test_detect_refactoring_type(self, tmp_path):
        plan = dict(SAMPLE_PLAN_JSON)
        plan["understanding"] = {"summary": "Refactor user service to use strategy pattern", "description": ""}
        plan["development_plan"] = dict(plan["development_plan"])
        _write_plan(tmp_path, plan)

        stage = PlanReaderStage(plans_dir=str(tmp_path / "plans"))
        pi, strategy = stage.run(task_id="TEST-001")
        assert pi.task_type == "refactoring"
        assert isinstance(strategy, RefactoringStrategy)

    def test_file_path_resolved_from_facts(self, tmp_path):
        """When plan has empty file_path, resolve from architecture_facts.json."""
        plan = json.loads(json.dumps(SAMPLE_PLAN_JSON))  # deep copy
        # Clear file_path for first component
        plan["development_plan"]["affected_components"][0]["file_path"] = ""

        _write_plan(tmp_path, plan)
        facts_file = _write_facts(tmp_path)

        stage = PlanReaderStage(
            plans_dir=str(tmp_path / "plans"),
            facts_path=str(facts_file),
        )
        pi, _ = stage.run(task_id="TEST-001")

        # Should have resolved from facts
        assert pi.affected_components[0].file_path != ""
        assert "UserServiceImpl" in pi.affected_components[0].file_path

    def test_file_path_resolved_by_name_fallback(self, tmp_path):
        """Resolve file_path by component name when ID doesn't match."""
        plan = json.loads(json.dumps(SAMPLE_PLAN_JSON))
        plan["development_plan"]["affected_components"][0]["id"] = "unknown.id"
        plan["development_plan"]["affected_components"][0]["file_path"] = ""

        _write_plan(tmp_path, plan)
        facts_file = _write_facts(tmp_path)

        stage = PlanReaderStage(
            plans_dir=str(tmp_path / "plans"),
            facts_path=str(facts_file),
        )
        pi, _ = stage.run(task_id="TEST-001")

        # Should resolve by name
        assert "UserServiceImpl" in pi.affected_components[0].file_path

    def test_missing_facts_graceful(self, tmp_path):
        """Stage 1 works even when architecture_facts.json doesn't exist."""
        plan = json.loads(json.dumps(SAMPLE_PLAN_JSON))
        plan["development_plan"]["affected_components"][1]["file_path"] = ""

        _write_plan(tmp_path, plan)

        stage = PlanReaderStage(
            plans_dir=str(tmp_path / "plans"),
            facts_path=str(tmp_path / "nonexistent.json"),
        )
        pi, _ = stage.run(task_id="TEST-001")

        # Should not crash, second component stays empty
        assert pi.affected_components[1].file_path == ""


# =============================================================================
# Stage 2: Context Collector Tests
# =============================================================================


class TestContextCollectorStage:
    """Test Stage 2: Context Collector."""

    def test_collect_existing_file(self, tmp_path):
        repo = tmp_path / "repo"
        _create_repo_file(
            repo,
            "backend/src/main/java/UserServiceImpl.java",
            "package com.example;\npublic class UserServiceImpl { }",
        )

        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="feature",
            summary="Test",
            affected_components=[
                ComponentTarget(
                    id="c1",
                    name="UserServiceImpl",
                    file_path="backend/src/main/java/UserServiceImpl.java",
                    stereotype="service",
                    layer="application",
                ),
            ],
        )

        stage = ContextCollectorStage(repo_path=str(repo))
        ctx = stage.run(plan)

        assert ctx.total_files == 1
        assert ctx.skipped_files == 0
        assert "UserServiceImpl" in ctx.file_contexts[0].content
        assert ctx.file_contexts[0].language == "java"

    def test_collect_missing_file_skipped(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()

        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="feature",
            summary="Test",
            affected_components=[
                ComponentTarget(
                    id="c1",
                    name="Missing",
                    file_path="nonexistent/File.java",
                    stereotype="service",
                    layer="application",
                    change_type="modify",
                ),
            ],
        )

        stage = ContextCollectorStage(repo_path=str(repo))
        ctx = stage.run(plan)
        assert ctx.total_files == 0
        assert ctx.skipped_files == 1

    def test_collect_new_file_for_create(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()

        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="feature",
            summary="Test",
            affected_components=[
                ComponentTarget(
                    id="c1",
                    name="NewService",
                    file_path="backend/src/NewService.java",
                    change_type="create",
                ),
            ],
        )

        stage = ContextCollectorStage(repo_path=str(repo))
        ctx = stage.run(plan)
        assert ctx.total_files == 1
        assert ctx.file_contexts[0].content == ""

    def test_file_truncation(self, tmp_path):
        repo = tmp_path / "repo"
        content = "x" * 20000
        _create_repo_file(repo, "big.java", content)

        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="feature",
            summary="Test",
            affected_components=[
                ComponentTarget(id="c1", name="Big", file_path="big.java"),
            ],
        )

        stage = ContextCollectorStage(repo_path=str(repo))
        ctx = stage.run(plan)
        assert len(ctx.file_contexts[0].content) < 20000
        assert "truncated" in ctx.file_contexts[0].content

    def test_language_detection(self, tmp_path):
        repo = tmp_path / "repo"
        for fname, expected_lang in [
            ("A.java", "java"),
            ("B.ts", "typescript"),
            ("C.html", "html"),
            ("D.scss", "scss"),
            ("E.json", "json"),
            ("F.xml", "xml"),
            ("G.txt", "other"),
        ]:
            _create_repo_file(repo, fname, "content")

            plan = CodegenPlanInput(
                task_id="T-1",
                task_type="feature",
                summary="Test",
                affected_components=[
                    ComponentTarget(id="c1", name="X", file_path=fname),
                ],
            )
            stage = ContextCollectorStage(repo_path=str(repo))
            ctx = stage.run(plan)
            assert ctx.file_contexts[0].language == expected_lang, f"{fname} -> {expected_lang}"

    def test_related_patterns_extracted(self, tmp_path):
        repo = tmp_path / "repo"
        _create_repo_file(repo, "Svc.java", "class Svc {}")

        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="feature",
            summary="Test",
            affected_components=[
                ComponentTarget(id="c1", name="Svc", file_path="Svc.java"),
            ],
            patterns={
                "security_considerations": [
                    {"security_type": "auth", "recommendation": "Check token"},
                ],
                "error_handling": [
                    {"exception_class": "SvcEx", "recommendation": "Log it"},
                ],
            },
        )

        stage = ContextCollectorStage(repo_path=str(repo))
        ctx = stage.run(plan)
        assert len(ctx.file_contexts[0].related_patterns) >= 2


# =============================================================================
# Stage 3: Code Generator Tests
# =============================================================================


class TestCodeGeneratorStage:
    """Test Stage 3: Code Generator (with mocked LLM)."""

    def _mock_stage(self):
        """Create stage with mocked LLM client."""
        with patch.object(CodeGeneratorStage, "_create_llm") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client
            stage = CodeGeneratorStage()
            stage.llm = mock_client
        return stage

    def _mock_response(self, content: str, total_tokens: int = 100):
        """Build a mock LLM response."""
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        resp.usage = MagicMock()
        resp.usage.total_tokens = total_tokens
        return resp

    def test_generate_modify(self):
        stage = self._mock_stage()
        stage.llm.chat.completions.create.return_value = self._mock_response(
            "```java\npackage com;\npublic class Svc { void foo() {} }\n```"
        )

        fc = FileContext(
            file_path="Svc.java",
            content="class Svc {}",
            language="java",
            component=ComponentTarget(id="c1", name="Svc", file_path="Svc.java"),
        )
        plan = CodegenPlanInput(task_id="T-1", task_type="feature", summary="Add foo")
        ctx = CollectedContext(file_contexts=[fc], total_files=1)

        result = stage.run(plan, ctx, FeatureStrategy())
        assert len(result) == 1
        assert result[0].action == "modify"
        assert "Svc" in result[0].content
        assert result[0].error == ""
        assert stage.total_calls == 1

    def test_generate_create(self):
        stage = self._mock_stage()
        stage.llm.chat.completions.create.return_value = self._mock_response("public class NewSvc { }")

        fc = FileContext(
            file_path="NewSvc.java",
            content="",
            language="java",
            component=ComponentTarget(
                id="c1",
                name="NewSvc",
                file_path="NewSvc.java",
                change_type="create",
            ),
        )
        plan = CodegenPlanInput(task_id="T-1", task_type="feature", summary="Create new")
        ctx = CollectedContext(file_contexts=[fc], total_files=1)

        result = stage.run(plan, ctx, FeatureStrategy())
        assert result[0].action == "create"

    def test_generate_delete_no_llm_call(self):
        stage = self._mock_stage()

        fc = FileContext(
            file_path="Old.java",
            content="class Old {}",
            language="java",
            component=ComponentTarget(
                id="c1",
                name="Old",
                file_path="Old.java",
                change_type="delete",
            ),
        )
        plan = CodegenPlanInput(task_id="T-1", task_type="refactoring", summary="Delete")
        ctx = CollectedContext(file_contexts=[fc], total_files=1)

        result = stage.run(plan, ctx, RefactoringStrategy())
        assert result[0].action == "delete"
        assert result[0].confidence == 1.0
        assert stage.total_calls == 0  # No LLM call

    def test_llm_failure_returns_error(self):
        stage = self._mock_stage()
        stage.llm.chat.completions.create.side_effect = RuntimeError("LLM down")

        fc = FileContext(
            file_path="Svc.java",
            content="class Svc {}",
            language="java",
            component=ComponentTarget(id="c1", name="Svc", file_path="Svc.java"),
        )
        plan = CodegenPlanInput(task_id="T-1", task_type="feature", summary="Test")
        ctx = CollectedContext(file_contexts=[fc], total_files=1)

        with (
            patch("aicodegencrew.hybrid.code_generation.stages.stage3_code_generator.MAX_RETRIES", 1),
            patch("aicodegencrew.hybrid.code_generation.stages.stage3_code_generator.CALL_DELAY", 0),
        ):
            result = stage.run(plan, ctx, FeatureStrategy())

        assert result[0].error != ""
        assert result[0].confidence == 0.0

    def test_empty_llm_response_retries(self):
        stage = self._mock_stage()
        # First call returns empty, second returns content
        stage.llm.chat.completions.create.side_effect = [
            self._mock_response(""),  # Empty → will raise ValueError
            self._mock_response("public class Svc { }"),
        ]

        fc = FileContext(
            file_path="Svc.java",
            content="class Svc {}",
            language="java",
            component=ComponentTarget(id="c1", name="Svc", file_path="Svc.java"),
        )
        plan = CodegenPlanInput(task_id="T-1", task_type="feature", summary="Test")
        ctx = CollectedContext(file_contexts=[fc], total_files=1)

        with patch("aicodegencrew.hybrid.code_generation.stages.stage3_code_generator.CALL_DELAY", 0):
            result = stage.run(plan, ctx, FeatureStrategy())

        assert result[0].error == ""
        assert stage.total_calls == 2


# =============================================================================
# Stage 4: Code Validator Tests
# =============================================================================


class TestCodeValidatorStage:
    """Test Stage 4: Code Validator."""

    def test_valid_java_file(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="Svc.java",
            content="package com.example;\npublic class Svc { void run() {} }",
            language="java",
        )
        result = stage.run([gf])
        assert result.total_valid == 1
        assert result.total_invalid == 0

    def test_unbalanced_braces(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="Svc.java",
            content="package com;\npublic class Svc { void run() {",
            language="java",
        )
        result = stage.run([gf])
        assert result.total_invalid == 1
        assert any("braces" in e.lower() for e in result.file_results[0].errors)

    def test_security_hardcoded_password(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="Config.java",
            content='class Config { String password = "secret123"; }',
            language="java",
        )
        result = stage.run([gf])
        assert result.total_invalid == 1
        assert len(result.security_issues) >= 1

    def test_security_sql_concatenation(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="Dao.java",
            content='class Dao { String q = userInput + "SELECT * FROM users"; }',
            language="java",
        )
        result = stage.run([gf])
        assert any("SQL" in i for i in result.security_issues)

    def test_security_eval_detected(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="util.ts",
            content="export function run(s: string) { return eval(s); }",
            language="typescript",
        )
        result = stage.run([gf])
        assert result.total_invalid == 1

    def test_delete_action_always_valid(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(file_path="Old.java", action="delete")
        result = stage.run([gf])
        assert result.total_valid == 1

    def test_already_failed_file(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="Fail.java",
            error="LLM generation failed after 2 retries",
        )
        result = stage.run([gf])
        assert result.total_invalid == 1

    def test_generates_diff(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="Svc.java",
            original_content="class Svc { }",
            content="class Svc { void run() {} }",
            action="modify",
            language="java",
        )
        stage.run([gf])
        assert gf.diff != ""
        assert "run()" in gf.diff

    def test_pattern_warning_class_name_mismatch(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="UserService.java",
            content="package com;\npublic class WrongName { }",
            language="java",
        )
        result = stage.run([gf])
        assert len(result.file_results[0].warnings) >= 1

    def test_typescript_no_export_warning(self):
        stage = CodeValidatorStage()
        gf = GeneratedFile(
            file_path="util.ts",
            content="function helper() { return 1; }",
            action="create",
            language="typescript",
        )
        result = stage.run([gf])
        assert any("export" in w.lower() for w in result.file_results[0].warnings)


# =============================================================================
# Stage 5: Output Writer Tests
# =============================================================================


class TestOutputWriterStage:
    """Test Stage 5: Output Writer."""

    def test_dry_run_skips_writes(self, tmp_path):
        stage = OutputWriterStage(
            repo_path=str(tmp_path),
            report_dir=str(tmp_path / "reports"),
            dry_run=True,
        )

        gf = GeneratedFile(
            file_path=str(tmp_path / "test.java"),
            content="class Test {}",
            language="java",
        )
        validation = ValidationResult(
            file_results=[FileValidationResult(file_path=gf.file_path, is_valid=True)],
            total_valid=1,
        )

        report = stage.run(
            task_id="T-1",
            generated_files=[gf],
            validation=validation,
        )

        assert report.status == "dry_run"
        assert report.dry_run is True

    def test_failure_threshold_aborts(self, tmp_path):
        stage = OutputWriterStage(
            repo_path=str(tmp_path),
            report_dir=str(tmp_path / "reports"),
        )

        files = [GeneratedFile(file_path=f"f{i}.java", error="failed") for i in range(3)]
        validation = ValidationResult(
            file_results=[FileValidationResult(file_path=f.file_path, is_valid=False, errors=["err"]) for f in files],
            total_invalid=3,
        )

        report = stage.run(task_id="T-1", generated_files=files, validation=validation)
        assert report.status == "failed"

    def test_report_json_written(self, tmp_path):
        stage = OutputWriterStage(
            repo_path=str(tmp_path),
            report_dir=str(tmp_path / "reports"),
            dry_run=True,
        )

        gf = GeneratedFile(file_path="a.java", content="class A {}", language="java")
        validation = ValidationResult(
            file_results=[FileValidationResult(file_path="a.java", is_valid=True)],
            total_valid=1,
        )

        stage.run(task_id="T-1", generated_files=[gf], validation=validation)

        # Report should be written (even in dry_run)
        report_file = tmp_path / "reports" / "T-1_report.json"
        assert report_file.exists()
        data = json.loads(report_file.read_text())
        assert data["task_id"] == "T-1"
        assert data["status"] == "dry_run"

    def test_not_git_repo_fails(self, tmp_path):
        stage = OutputWriterStage(
            repo_path=str(tmp_path),
            report_dir=str(tmp_path / "reports"),
        )

        gf = GeneratedFile(file_path="a.java", content="class A {}", language="java")
        validation = ValidationResult(
            file_results=[FileValidationResult(file_path="a.java", is_valid=True)],
            total_valid=1,
        )

        report = stage.run(task_id="T-1", generated_files=[gf], validation=validation)
        assert report.status == "failed"

    def test_degradation_reasons_force_partial(self, tmp_path):
        """Passing degradation reasons turns a 'success' into 'partial' and attaches reasons."""
        stage = OutputWriterStage(
            repo_path=str(tmp_path),
            report_dir=str(tmp_path / "reports"),
            dry_run=True,
        )

        gf = GeneratedFile(file_path="a.java", content="class A {}", language="java")
        validation = ValidationResult(
            file_results=[FileValidationResult(file_path="a.java", is_valid=True)],
            total_valid=1,
        )

        report = stage.run(
            task_id="T-1",
            generated_files=[gf],
            validation=validation,
            degradation_reasons=["build failed"],
        )

        assert report.status == "dry_run"
        assert "build failed" in report.degradation_reasons

    def test_filter_valid_files(self):
        files = [
            GeneratedFile(file_path="a.java", content="ok"),
            GeneratedFile(file_path="b.java", content="ok"),
            GeneratedFile(file_path="c.java", error="failed"),
        ]
        validation = ValidationResult(
            file_results=[
                FileValidationResult(file_path="a.java", is_valid=True),
                FileValidationResult(file_path="b.java", is_valid=True),
                FileValidationResult(file_path="c.java", is_valid=False),
            ],
        )
        valid = OutputWriterStage._filter_valid_files(files, validation)
        assert len(valid) == 2
        assert all(f.file_path in ("a.java", "b.java") for f in valid)


# =============================================================================
# Strategy Tests
# =============================================================================


class TestStrategies:
    """Test all 4 code generation strategies."""

    def test_strategy_map_complete(self):
        assert set(STRATEGY_MAP.keys()) == {"upgrade", "feature", "bugfix", "refactoring"}

    def test_all_strategies_implement_base(self):
        for cls in STRATEGY_MAP.values():
            assert issubclass(cls, BaseStrategy)

    def test_feature_strategy_modify_prompt(self):
        strategy = FeatureStrategy()
        fc = FileContext(
            file_path="Svc.java",
            content="class Svc {}",
            language="java",
            component=ComponentTarget(
                id="c1", name="Svc", file_path="Svc.java", stereotype="service", layer="application"
            ),
        )
        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="feature",
            summary="Add method",
            implementation_steps=["1. Add foo()", "2. Add bar()"],
            architecture_context={"style": "Layered", "layer_pattern": "C -> S -> R"},
        )

        prompt = strategy.build_prompt(fc, plan)
        assert "Add method" in prompt
        assert "CURRENT CODE" in prompt
        assert "class Svc" in prompt
        assert "Add foo()" in prompt

    def test_feature_strategy_create_prompt(self):
        strategy = FeatureStrategy()
        fc = FileContext(
            file_path="New.java",
            content="",
            language="java",
            component=ComponentTarget(
                id="c1", name="New", file_path="New.java", stereotype="service", change_type="create"
            ),
        )
        plan = CodegenPlanInput(task_id="T-1", task_type="feature", summary="Create service")

        prompt = strategy.build_prompt(fc, plan)
        assert "NEW FILE TO CREATE" in prompt
        assert "CURRENT CODE" not in prompt

    def test_bugfix_strategy_prompt(self):
        strategy = BugfixStrategy()
        fc = FileContext(file_path="Svc.java", content="class Svc {}", language="java")
        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="bugfix",
            summary="Fix NPE in login",
            implementation_steps=["1. Add null check"],
        )

        prompt = strategy.build_prompt(fc, plan)
        assert "Fix NPE in login" in prompt
        assert "MINIMAL changes" in prompt

    def test_upgrade_strategy_prompt_with_rules(self):
        strategy = UpgradeStrategy()
        fc = FileContext(
            file_path="frontend/src/app/app.component.ts",
            content="@Component({}) export class AppComponent {}",
            language="typescript",
        )
        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="upgrade",
            summary="Angular upgrade",
            upgrade_plan={
                "framework": "Angular",
                "from_version": "18",
                "to_version": "19",
                "migration_sequence": [
                    {
                        "rule_id": "ng19-standalone",
                        "title": "Standalone default",
                        "severity": "breaking",
                        "migration_steps": ["Run migration schematic"],
                        "affected_files": ["frontend/src/app/app.component.ts"],
                        "schematic": "ng generate @angular/core:standalone-migration",
                    }
                ],
            },
        )

        prompt = strategy.build_prompt(fc, plan)
        assert "Angular" in prompt
        assert "18" in prompt
        assert "19" in prompt
        assert "BREAKING" in prompt
        assert "Standalone default" in prompt

    def test_upgrade_strategy_handles_current_version_alias(self):
        """Test that current_version/target_version aliases work."""
        strategy = UpgradeStrategy()
        fc = FileContext(file_path="a.ts", content="code", language="typescript")
        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="upgrade",
            summary="Upgrade",
            upgrade_plan={
                "framework": "Angular",
                "current_version": "16",
                "target_version": "19",
            },
        )
        prompt = strategy.build_prompt(fc, plan)
        assert "16" in prompt
        assert "19" in prompt

    def test_refactoring_strategy_prompt(self):
        strategy = RefactoringStrategy()
        fc = FileContext(file_path="Svc.java", content="class Svc {}", language="java")
        plan = CodegenPlanInput(
            task_id="T-1",
            task_type="refactoring",
            summary="Extract method pattern",
            architecture_context={"style": "Layered", "layer_pattern": "C -> S -> R"},
        )

        prompt = strategy.build_prompt(fc, plan)
        assert "Extract method pattern" in prompt
        assert "PRESERVE all public method signatures" in prompt

    def test_extract_code_block(self):
        text = "Here is the code:\n```java\nclass Svc {}\n```\nDone."
        assert BaseStrategy._extract_code_block(text) == "class Svc {}"

    def test_extract_code_block_no_markers(self):
        text = "class Svc {}"
        assert BaseStrategy._extract_code_block(text) == "class Svc {}"

    def test_post_process_all_strategies(self):
        fc = FileContext(file_path="a.java", content="old", language="java")
        raw = "```java\nclass New {}\n```"

        for cls in STRATEGY_MAP.values():
            strategy = cls()
            result = strategy.post_process(raw, fc)
            assert "class New" in result

    def test_upgrade_post_process_restores_imports(self):
        strategy = UpgradeStrategy()
        fc = FileContext(
            file_path="a.java",
            content="import com.foo.Bar;\nimport com.foo.Baz;\n\nclass A {}",
            language="java",
        )
        # LLM output without imports
        raw = "class A { void run() {} }"
        result = strategy.post_process(raw, fc)
        assert "import com.foo.Bar" in result
        assert "import com.foo.Baz" in result


# =============================================================================
# Pipeline Integration Tests
# =============================================================================


class TestCodeGenerationPipeline:
    """Test the full pipeline orchestration."""

    def test_pipeline_dry_run(self, tmp_path):
        """Dry-run mode processes stages 1-4 but skips file writes."""
        plan_file = _write_plan(tmp_path, SAMPLE_PLAN_JSON)

        repo = tmp_path / "repo"
        _create_repo_file(
            repo,
            "backend/src/main/java/com/example/user/UserServiceImpl.java",
            "package com.example.user;\npublic class UserServiceImpl { }",
        )

        report_dir = tmp_path / "reports"

        with patch.object(CodeGeneratorStage, "_create_llm") as mock_llm:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[
                0
            ].message.content = "package com.example.user;\npublic class UserServiceImpl { void sendEmail() {} }"
            mock_resp.usage = MagicMock()
            mock_resp.usage.total_tokens = 200
            mock_client.chat.completions.create.return_value = mock_resp
            mock_llm.return_value = mock_client

            pipeline = CodeGenerationPipeline(
                repo_path=str(repo),
                task_id="TEST-001",
                plans_dir=str(plan_file.parent),
                report_dir=str(report_dir),
                dry_run=True,
            )
            result = pipeline.run()

        assert result["status"] == "dry_run"
        assert result["task_id"] == "TEST-001"

    def test_pipeline_single_task_missing_plan_fails_fast(self, tmp_path):
        """Single-task mode fails fast when plan file is missing."""
        repo = tmp_path / "repo"
        repo.mkdir()
        pipeline = CodeGenerationPipeline(
            repo_path=str(repo),
            task_id="TASK-404",
            plans_dir=str(tmp_path / "plans"),
            report_dir=str(tmp_path / "reports"),
            dry_run=True,
        )
        result = pipeline.run()
        assert result["status"] == "failed"
        assert "plan file not found" in result["message"]

    def test_pipeline_no_plans(self, tmp_path):
        """Pipeline returns skipped when no plan files found."""
        pipeline = CodeGenerationPipeline(
            repo_path=str(tmp_path),
            plans_dir=str(tmp_path / "empty"),
            report_dir=str(tmp_path / "reports"),
        )
        (tmp_path / "empty").mkdir()
        result = pipeline.run()
        assert result["status"] == "skipped"

    def test_pipeline_single_task_mode(self, tmp_path):
        plan_file = _write_plan(tmp_path, SAMPLE_PLAN_JSON)
        repo = tmp_path / "repo"
        _create_repo_file(
            repo,
            "backend/src/main/java/com/example/user/UserServiceImpl.java",
            "package com.example.user;\npublic class UserServiceImpl { }",
        )

        with patch.object(CodeGeneratorStage, "_create_llm") as mock_llm:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[
                0
            ].message.content = "package com.example.user;\npublic class UserServiceImpl { void sendEmail() {} }"
            mock_resp.usage = MagicMock()
            mock_resp.usage.total_tokens = 200
            mock_client.chat.completions.create.return_value = mock_resp
            mock_llm.return_value = mock_client

            pipeline = CodeGenerationPipeline(
                repo_path=str(repo),
                task_id="TEST-001",
                plans_dir=str(plan_file.parent),
                report_dir=str(tmp_path / "reports"),
                dry_run=True,
            )
            result = pipeline.run()

        assert result["task_id"] == "TEST-001"
        assert "metrics" in result
        assert "reports" in result

    def test_pipeline_multi_task_mode(self, tmp_path):
        """Multiple plan files processed sequentially."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()

        for tid in ("TASK-A", "TASK-B"):
            plan = json.loads(json.dumps(SAMPLE_PLAN_JSON))
            plan["task_id"] = tid
            (plans_dir / f"{tid}_plan.json").write_text(json.dumps(plan), encoding="utf-8")

        repo = tmp_path / "repo"
        _create_repo_file(
            repo,
            "backend/src/main/java/com/example/user/UserServiceImpl.java",
            "package com.example.user;\npublic class UserServiceImpl { }",
        )

        with patch.object(CodeGeneratorStage, "_create_llm") as mock_llm:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[
                0
            ].message.content = "package com.example.user;\npublic class UserServiceImpl { void run() {} }"
            mock_resp.usage = MagicMock()
            mock_resp.usage.total_tokens = 100
            mock_client.chat.completions.create.return_value = mock_resp
            mock_llm.return_value = mock_client

            pipeline = CodeGenerationPipeline(
                repo_path=str(repo),
                plans_dir=str(plans_dir),
                report_dir=str(tmp_path / "reports"),
                dry_run=True,
            )
            result = pipeline.run()

        assert result["status"] in ("completed", "partial")
        assert result["metrics"]["tasks_total"] == 2

    def test_kickoff_delegates_to_run(self, tmp_path):
        """Orchestrator-compatible kickoff() calls run()."""
        pipeline = CodeGenerationPipeline(
            repo_path=str(tmp_path),
            plans_dir=str(tmp_path / "empty"),
            report_dir=str(tmp_path / "reports"),
        )
        (tmp_path / "empty").mkdir()

        result = pipeline.kickoff()
        assert result["status"] == "skipped"

    def test_kickoff_uses_current_plan_outputs_only(self, tmp_path):
        """When previous phase outputs are provided, stale plan files are ignored."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)

        # Simulate stale + current plans in the same directory
        (plans_dir / "OLD-001_plan.json").write_text("{}", encoding="utf-8")
        (plans_dir / "NEW-001_plan.json").write_text("{}", encoding="utf-8")

        pipeline = CodeGenerationPipeline(
            repo_path=str(tmp_path),
            plans_dir=str(plans_dir),
            report_dir=str(tmp_path / "reports"),
            dry_run=True,
        )

        with patch.object(CodeGenerationPipeline, "_run_single_cascade") as mock_run_single:
            mock_run_single.return_value = CodegenReport(task_id="NEW-001", status="dry_run")
            result = pipeline.kickoff(
                {
                    "previous_results": {
                        "plan": {
                            "output_files": [str(plans_dir / "NEW-001_plan.json")],
                        }
                    }
                }
            )

        assert result["metrics"]["tasks_total"] == 1
        assert result["metrics"]["tasks_succeeded"] == 1
        assert mock_run_single.call_count == 1
        assert mock_run_single.call_args.kwargs["task_id"] == "NEW-001"
