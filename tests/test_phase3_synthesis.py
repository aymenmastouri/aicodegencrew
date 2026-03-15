"""
Tests for Phase 3: Architecture Synthesis (base_crew, C4, Arc42).

All tests run without LLM, MCP server, or ChromaDB.
Tests cover configuration, checkpoint logic, data loading,
and factory methods with mocked dependencies.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aicodegencrew.crews.architecture_synthesis.arc42.crew import ARC42_AGENT_CONFIG, Arc42Crew
from aicodegencrew.crews.architecture_synthesis.base_crew import (
    TOOL_INSTRUCTION,
    MiniCrewBase,
)
from aicodegencrew.crews.architecture_synthesis.c4.crew import C4_AGENT_CONFIG, C4Crew
from aicodegencrew.crews.architecture_synthesis.crew import ArchitectureSynthesisCrew

# =============================================================================
# Helpers
# =============================================================================


def _write_json(path: Path, data: dict):
    """Write a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


MINIMAL_FACTS = {
    "system": {"name": "TestSystem"},
    "containers": [{"id": "backend", "name": "Backend", "technology": "Spring Boot"}],
    "components": [
        {
            "id": "comp.svc",
            "name": "UserService",
            "stereotype": "service",
            "layer": "application",
            "container": "backend",
        },
    ],
    "interfaces": [],
    "relations": [],
}

MINIMAL_ANALYSIS = {
    "architecture": {"style": "Layered"},
    "patterns": {"domain_patterns": []},
}

MINIMAL_EVIDENCE = {"ev_1": {"file_path": "Svc.java", "start_line": 1, "end_line": 5, "reason": "test"}}


# =============================================================================
# MiniCrewBase Tests
# =============================================================================


class TestMiniCrewBaseDataLoading:
    """Test static data-loading and utility methods."""

    def test_load_json_valid(self, tmp_path):
        data = {"key": "value"}
        f = tmp_path / "test.json"
        _write_json(f, data)

        result = MiniCrewBase._load_json(f)
        assert result == data

    def test_load_json_missing_file(self, tmp_path):
        result = MiniCrewBase._load_json(tmp_path / "nonexistent.json")
        assert result == {}

    def test_load_json_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json{", encoding="utf-8")
        result = MiniCrewBase._load_json(f)
        assert result == {}

    def test_escape_braces(self):
        assert MiniCrewBase.escape_braces("{test}") == "{{test}}"
        assert MiniCrewBase.escape_braces("no braces") == "no braces"
        assert MiniCrewBase.escape_braces("{{already}}") == "{{{{already}}}}"


class TestMiniCrewBaseLLMFactory:
    """Test LLM creation from env vars."""

    @patch.dict(
        os.environ,
        {
            "MODEL": "test-model",
            "API_BASE": "http://localhost:11434",
            "MAX_LLM_OUTPUT_TOKENS": "2000",
            "LLM_CONTEXT_WINDOW": "64000",
        },
    )
    @patch("aicodegencrew.shared.utils.llm_factory.LLM")
    def test_create_llm_from_env(self, MockLLM):
        """LLM is created with env var settings."""
        mock_instance = MagicMock()
        MockLLM.return_value = mock_instance

        # Create a concrete subclass to test _create_llm
        class TestCrew(MiniCrewBase):
            crew_name = "Test"
            agent_config = {"role": "r", "goal": "g", "backstory": "b"}

            def _summarize_facts(self):
                return {}

            def run(self):
                return ""

        # Mock _load_json to avoid file I/O; bypass __init__ with __new__
        with patch.object(MiniCrewBase, "_load_json", return_value={}):
            crew = TestCrew.__new__(TestCrew)
            crew.facts_path = Path("fake.json")
            crew.analyzed_path = Path("fake2.json")
            crew.chroma_dir = ".cache/.chroma"
            crew.facts = {}
            crew.analysis = {}
            crew.evidence_map = {}
            crew.summaries = {}
            crew._checkpoints = []
            crew._token_budget = 64000
            crew._token_usage = []

            crew._create_llm()

            MockLLM.assert_called_once()
            call_kwargs = MockLLM.call_args[1]
            assert call_kwargs["model"] == "openai/test-model"
            assert call_kwargs["base_url"] == "http://localhost:11434"
            assert call_kwargs["max_tokens"] == 2000
            # context_window_size set after construction
            assert mock_instance.context_window_size == 64000

    @patch.dict(os.environ, {"MAX_LLM_OUTPUT_TOKENS": "0"}, clear=False)
    @patch("aicodegencrew.shared.utils.llm_factory.LLM")
    def test_create_llm_zero_tokens_fallback(self, MockLLM):
        """max_tokens < 1 falls back to 65536."""
        mock_instance = MagicMock()
        MockLLM.return_value = mock_instance

        class TestCrew(MiniCrewBase):
            crew_name = "Test"
            agent_config = {"role": "r", "goal": "g", "backstory": "b"}

            def _summarize_facts(self):
                return {}

            def run(self):
                return ""

        with patch.object(MiniCrewBase, "_load_json", return_value={}):
            crew = TestCrew.__new__(TestCrew)
            crew.facts_path = Path("fake.json")
            crew.facts = {}
            crew.analysis = {}
            crew.evidence_map = {}
            crew.summaries = {}
            crew._checkpoints = []
            crew._token_budget = 120000
            crew._token_usage = []

            crew._create_llm()

            call_kwargs = MockLLM.call_args[1]
            assert call_kwargs["max_tokens"] == 65536


class TestToolInstruction:
    """Test that TOOL_INSTRUCTION contains critical patterns."""

    def test_contains_doc_writer_instruction(self):
        assert "doc_writer" in TOOL_INSTRUCTION

    def test_contains_mandatory_rules(self):
        assert "200 characters" in TOOL_INSTRUCTION
        assert "one-liner" in TOOL_INSTRUCTION.lower()

    def test_contains_correct_pattern(self):
        assert "CORRECT EXECUTION PATTERN" in TOOL_INSTRUCTION

    def test_contains_wrong_examples(self):
        assert "WRONG" in TOOL_INSTRUCTION

    def test_format_safe(self):
        """TOOL_INSTRUCTION can be used with .format() without errors."""
        # This tests that all braces are properly escaped
        try:
            TOOL_INSTRUCTION.format()
        except (KeyError, IndexError):
            pytest.fail("TOOL_INSTRUCTION contains unescaped braces")


# =============================================================================
# C4Crew Tests
# =============================================================================


class TestC4CrewConfig:
    """Test C4 crew configuration."""

    def test_agent_config_has_required_keys(self):
        assert "role" in C4_AGENT_CONFIG
        assert "goal" in C4_AGENT_CONFIG
        assert "backstory" in C4_AGENT_CONFIG

    def test_agent_config_role_mentions_c4(self):
        assert "C4" in C4_AGENT_CONFIG["role"]

    def test_c4_crew_name(self, tmp_path):
        """C4Crew.crew_name returns 'C4'."""
        _write_json(tmp_path / "facts.json", MINIMAL_FACTS)
        _write_json(tmp_path / "analyzed.json", MINIMAL_ANALYSIS)
        _write_json(tmp_path / "evidence_map.json", MINIMAL_EVIDENCE)

        crew = C4Crew(
            facts_path=str(tmp_path / "facts.json"),
            analyzed_path=str(tmp_path / "analyzed.json"),
        )
        assert crew.crew_name == "C4"

    def test_c4_crew_agent_config_matches_module(self, tmp_path):
        """C4Crew.agent_config returns C4_AGENT_CONFIG."""
        _write_json(tmp_path / "facts.json", MINIMAL_FACTS)
        _write_json(tmp_path / "analyzed.json", MINIMAL_ANALYSIS)
        _write_json(tmp_path / "evidence_map.json", MINIMAL_EVIDENCE)

        crew = C4Crew(
            facts_path=str(tmp_path / "facts.json"),
            analyzed_path=str(tmp_path / "analyzed.json"),
        )
        assert crew.agent_config == C4_AGENT_CONFIG


# =============================================================================
# Arc42Crew Tests
# =============================================================================


class TestArc42CrewConfig:
    """Test Arc42 crew configuration."""

    def test_agent_config_has_required_keys(self):
        assert "role" in ARC42_AGENT_CONFIG
        assert "goal" in ARC42_AGENT_CONFIG
        assert "backstory" in ARC42_AGENT_CONFIG

    def test_agent_config_role_mentions_architect(self):
        assert "Architect" in ARC42_AGENT_CONFIG["role"]

    def test_arc42_crew_name(self, tmp_path):
        """Arc42Crew.crew_name returns 'Arc42'."""
        _write_json(tmp_path / "facts.json", MINIMAL_FACTS)
        _write_json(tmp_path / "analyzed.json", MINIMAL_ANALYSIS)
        _write_json(tmp_path / "evidence_map.json", MINIMAL_EVIDENCE)

        crew = Arc42Crew(
            facts_path=str(tmp_path / "facts.json"),
            analyzed_path=str(tmp_path / "analyzed.json"),
        )
        assert crew.crew_name == "Arc42"

    def test_arc42_crew_agent_config_matches_module(self, tmp_path):
        """Arc42Crew.agent_config returns ARC42_AGENT_CONFIG."""
        _write_json(tmp_path / "facts.json", MINIMAL_FACTS)
        _write_json(tmp_path / "analyzed.json", MINIMAL_ANALYSIS)
        _write_json(tmp_path / "evidence_map.json", MINIMAL_EVIDENCE)

        crew = Arc42Crew(
            facts_path=str(tmp_path / "facts.json"),
            analyzed_path=str(tmp_path / "analyzed.json"),
        )
        assert crew.agent_config == ARC42_AGENT_CONFIG


# =============================================================================
# ArchitectureSynthesisCrew (Orchestrator) Tests
# =============================================================================


class TestSynthesisCrewPrerequisites:
    """Test prerequisite validation in the Phase 3 pipeline."""

    def test_validate_prerequisites_all_present(self, tmp_path, monkeypatch):
        """No error when all prerequisite files exist."""
        monkeypatch.chdir(tmp_path)
        extract_dir = tmp_path / "knowledge" / "extract"
        analyze_dir = tmp_path / "knowledge" / "analyze"
        _write_json(extract_dir / "architecture_facts.json", MINIMAL_FACTS)
        _write_json(extract_dir / "evidence_map.json", MINIMAL_EVIDENCE)
        _write_json(analyze_dir / "analyzed_architecture.json", MINIMAL_ANALYSIS)

        from aicodegencrew.pipelines.document.pipeline import DocumentPipeline

        pipeline = DocumentPipeline(
            facts_path=extract_dir / "architecture_facts.json",
            analyzed_path=analyze_dir / "analyzed_architecture.json",
        )
        # Should not raise
        pipeline._validate_prerequisites()

    def test_validate_prerequisites_missing_facts(self, tmp_path):
        """Error when architecture_facts.json is missing."""
        extract_dir = tmp_path / "knowledge" / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        analyze_dir = tmp_path / "knowledge" / "analyze"
        analyze_dir.mkdir(parents=True, exist_ok=True)

        from aicodegencrew.pipelines.document.pipeline import DocumentPipeline

        pipeline = DocumentPipeline(
            facts_path=extract_dir / "architecture_facts.json",
            analyzed_path=analyze_dir / "analyzed_architecture.json",
        )
        with pytest.raises(FileNotFoundError, match="Phase 1 output not found"):
            pipeline._validate_prerequisites()

    def test_validate_prerequisites_missing_analysis(self, tmp_path, monkeypatch):
        """Error when analyzed_architecture.json is missing."""
        monkeypatch.chdir(tmp_path)
        extract_dir = tmp_path / "knowledge" / "extract"
        analyze_dir = tmp_path / "knowledge" / "analyze"
        _write_json(extract_dir / "architecture_facts.json", MINIMAL_FACTS)
        _write_json(extract_dir / "evidence_map.json", MINIMAL_EVIDENCE)

        from aicodegencrew.pipelines.document.pipeline import DocumentPipeline

        pipeline = DocumentPipeline(
            facts_path=extract_dir / "architecture_facts.json",
            analyzed_path=analyze_dir / "analyzed_architecture.json",
        )
        with pytest.raises(FileNotFoundError, match="Phase 2 output not found"):
            pipeline._validate_prerequisites()


class TestSynthesisCrewCleanup:
    """Test checkpoint and resume logic."""

    def test_checkpoint_resume(self, tmp_path, monkeypatch):
        """When checkpoint exists, completed chapters are skipped."""
        monkeypatch.chdir(tmp_path)

        from aicodegencrew.pipelines.document.pipeline import DocumentPipeline

        output_dir = tmp_path / "knowledge" / "document"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a checkpoint marking some chapters as done
        checkpoint = output_dir / ".checkpoint_pipeline.json"
        _write_json(checkpoint, {"completed": ["c4-context", "arc42-ch01"]})

        pipeline = DocumentPipeline(output_dir=output_dir)
        completed = pipeline._load_checkpoint()

        assert "c4-context" in completed
        assert "arc42-ch01" in completed

    def test_checkpoint_cleared_on_success(self, tmp_path):
        """Checkpoint is removed when all chapters succeed."""
        from aicodegencrew.pipelines.document.pipeline import DocumentPipeline

        output_dir = tmp_path / "knowledge" / "document"
        output_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = output_dir / ".checkpoint_pipeline.json"
        _write_json(checkpoint, {"completed": ["test"]})

        pipeline = DocumentPipeline(output_dir=output_dir)
        pipeline._clear_checkpoint()

        assert not checkpoint.exists()


class TestSynthesisCrewKickoff:
    """Test kickoff() interface."""

    def test_kickoff_delegates_to_run(self, tmp_path):
        """kickoff() calls run()."""
        extract_dir = tmp_path / "knowledge" / "extract"
        _write_json(extract_dir / "architecture_facts.json", MINIMAL_FACTS)

        crew = ArchitectureSynthesisCrew(facts_path=str(extract_dir / "architecture_facts.json"))

        mock_result = {"status": "completed", "phase": "document"}
        with patch.object(crew, "run", return_value=mock_result) as mock_run:
            result = crew.kickoff()

        mock_run.assert_called_once()
        assert result == mock_result


class TestSynthesisCrewStatus:
    """Test phase status reporting via pipeline."""

    def test_run_returns_status_and_phase(self, tmp_path):
        """kickoff() returns dict with status and phase keys."""
        from aicodegencrew.pipelines.document.pipeline import DocumentPipeline, PipelineResult

        crew = ArchitectureSynthesisCrew(facts_path=str(tmp_path / "facts.json"))

        mock_result = PipelineResult(status="success", chapters=[], degradation_reasons=[])
        with patch.object(DocumentPipeline, "run", return_value=mock_result):
            result = crew.run()

        assert result["status"] == "success"
        assert result["phase"] == "document"
        assert result["degradation_reasons"] == []

    def test_run_returns_partial_with_degradations(self, tmp_path):
        """When pipeline has degradation reasons, status is partial."""
        from aicodegencrew.pipelines.document.pipeline import DocumentPipeline, PipelineResult

        crew = ArchitectureSynthesisCrew(facts_path=str(tmp_path / "facts.json"))

        mock_result = PipelineResult(
            status="partial",
            chapters=[],
            degradation_reasons=["ch05: missing sections"],
        )
        with patch.object(DocumentPipeline, "run", return_value=mock_result):
            result = crew.run()

        assert result["status"] == "partial"
        assert result["degradation_reasons"] == ["ch05: missing sections"]
