"""
Tests for Orchestrator Protocol compliance.

Verifies that all phase executables satisfy the PhaseExecutable protocol
and that _invoke_executable() dispatches correctly.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from aicodegencrew.orchestrator import (
    PhaseResult,
    SDLCOrchestrator,
)

MINIMAL_PHASES_CONFIG = {
    "phases": {
        "discover": {
            "enabled": True,
            "name": "Repository Indexing",
            "order": 0,
            "required": True,
        },
        "extract": {
            "enabled": True,
            "name": "Architecture Facts Extraction",
            "order": 1,
            "required": True,
            "dependencies": ["discover"],
        },
    },
    "presets": {
        "index": ["discover"],
        "scan": ["discover", "extract"],
    },
    "execution": {
        "mode": "index",
        "stop_on_error": True,
    },
}


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class _MockPhase:
    """A mock that satisfies PhaseExecutable protocol."""

    def __init__(self, result: dict = None):
        self._result = result or {"status": "completed", "phase": "mock"}

    def kickoff(self, inputs: dict[str, Any] = None) -> dict[str, Any]:
        return self._result


class _BrokenPhase:
    """A mock missing kickoff() — does NOT satisfy PhaseExecutable."""

    def run(self):
        return "running"


class TestPhaseExecutableProtocol:
    """Test that PhaseExecutable protocol works correctly."""

    def test_mock_phase_satisfies_protocol(self):
        """A class with kickoff() satisfies PhaseExecutable."""
        phase = _MockPhase()
        # Python's Protocol uses structural subtyping at runtime via isinstance
        # checks only if @runtime_checkable is set. We verify by duck-typing:
        assert hasattr(phase, "kickoff")
        assert callable(phase.kickoff)

    def test_kickoff_returns_dict(self):
        """kickoff() returns Dict[str, Any]."""
        phase = _MockPhase({"status": "completed", "data": [1, 2, 3]})
        result = phase.kickoff()
        assert isinstance(result, dict)
        assert result["status"] == "completed"

    def test_kickoff_accepts_none_inputs(self):
        """kickoff() works when called with no args."""
        phase = _MockPhase()
        result = phase.kickoff()
        assert result["status"] == "completed"

    def test_kickoff_accepts_dict_inputs(self):
        """kickoff() works when called with inputs dict."""
        phase = _MockPhase()
        result = phase.kickoff(inputs={"repo_path": "/test"})
        assert result["status"] == "completed"


class TestRealPhasesHaveKickoff:
    """Verify that all real phase classes have kickoff() method."""

    def test_indexing_pipeline_has_kickoff(self):
        from aicodegencrew.pipelines.indexing.indexing_pipeline import IndexingPipeline

        assert hasattr(IndexingPipeline, "kickoff")

    def test_facts_pipeline_has_kickoff(self):
        from aicodegencrew.pipelines.architecture_facts.pipeline import ArchitectureFactsPipeline

        assert hasattr(ArchitectureFactsPipeline, "kickoff")

    def test_analysis_crew_has_kickoff(self):
        from aicodegencrew.crews.architecture_analysis.crew import ArchitectureAnalysisCrew

        assert hasattr(ArchitectureAnalysisCrew, "kickoff")

    def test_synthesis_crew_has_kickoff(self):
        from aicodegencrew.crews.architecture_synthesis.crew import ArchitectureSynthesisCrew

        assert hasattr(ArchitectureSynthesisCrew, "kickoff")

    def test_planning_pipeline_has_kickoff(self):
        from aicodegencrew.hybrid.development_planning.pipeline import DevelopmentPlanningPipeline

        assert hasattr(DevelopmentPlanningPipeline, "kickoff")

    def test_codegen_pipeline_has_kickoff(self):
        from aicodegencrew.hybrid.code_generation.crew import ImplementCrew

        assert hasattr(ImplementCrew, "kickoff")


# =============================================================================
# _invoke_executable Tests
# =============================================================================


class TestInvokeExecutable:
    """Test the orchestrator's _invoke_executable() dispatch."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        cfg_file = tmp_path / "phases_config.yaml"
        cfg_file.write_text(yaml.dump(MINIMAL_PHASES_CONFIG), encoding="utf-8")
        return SDLCOrchestrator(config_path=str(cfg_file))

    def test_calls_kickoff_with_inputs(self, orchestrator):
        """_invoke_executable calls kickoff(inputs)."""
        phase = _MockPhase({"status": "completed", "result": "ok"})
        result = orchestrator._invoke_executable(phase, {"key": "value"})
        assert result == {"status": "completed", "result": "ok"}

    def test_calls_kickoff_with_none(self, orchestrator):
        """_invoke_executable works with None inputs."""
        phase = _MockPhase()
        result = orchestrator._invoke_executable(phase, None)
        assert result["status"] == "completed"

    def test_propagates_exceptions(self, orchestrator):
        """Exceptions from kickoff() propagate up."""
        phase = MagicMock()
        phase.kickoff.side_effect = RuntimeError("LLM down")

        with pytest.raises(RuntimeError, match="LLM down"):
            orchestrator._invoke_executable(phase, {})

    def test_timeout_error_includes_phase_id(self, orchestrator, monkeypatch):
        """TimeoutError message should include the phase_id for easier debugging."""
        phase = MagicMock()

        class _FakeFuture:
            def result(self, timeout: float | None = None):  # pragma: no cover - invoked via ThreadPoolExecutor stub
                import concurrent.futures
                raise concurrent.futures.TimeoutError()

        class _FakeExecutor:
            def __init__(self, *args, **kwargs):  # pragma: no cover - accept ThreadPoolExecutor kwargs
                pass

            def __enter__(self):  # pragma: no cover - context manager protocol
                return self

            def __exit__(self, exc_type, exc, tb):  # pragma: no cover - context manager protocol
                return False

            def submit(self, fn, *args, **kwargs):  # pragma: no cover - used by _invoke_executable
                return _FakeFuture()

        monkeypatch.setattr("aicodegencrew.orchestrator._cf.ThreadPoolExecutor", _FakeExecutor)

        inputs = {"config": {"phase_id": "discover"}}
        with pytest.raises(TimeoutError) as excinfo:
            orchestrator._invoke_executable(phase, inputs)

        assert "discover" in str(excinfo.value)


# =============================================================================
# Orchestrator Registration + Execution Tests
# =============================================================================


class TestOrchestratorWithMockPhases:
    """Test orchestrator run() with mock phases."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        cfg_file = tmp_path / "phases_config.yaml"
        cfg_file.write_text(yaml.dump(MINIMAL_PHASES_CONFIG), encoding="utf-8")
        return SDLCOrchestrator(config_path=str(cfg_file))

    def test_register_and_run_single_phase(self, orchestrator):
        """Register a mock phase and run it via _execute_phase."""
        mock_result = {"status": "completed", "phase": "discover"}
        phase = _MockPhase(mock_result)

        orchestrator.register("discover", phase)
        result = orchestrator._execute_phase("discover")

        assert isinstance(result, PhaseResult)
        assert result.status == "success"

    def test_run_phase_returns_failure_on_exception(self, orchestrator):
        """Phase that raises exception returns failed PhaseResult."""
        phase = MagicMock()
        phase.kickoff.side_effect = ValueError("bad input")

        orchestrator.register("discover", phase)
        result = orchestrator._execute_phase("discover")

        assert result.status == "failed"
        assert "bad input" in result.message

    def test_run_unregistered_phase_skipped(self, orchestrator):
        """Running an unregistered phase returns skipped."""
        result = orchestrator._execute_phase("discover")
        assert result.status == "skipped"
