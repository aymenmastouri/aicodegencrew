"""
Tests for Live Progress Bar, Sub-Phase Progress, Live Metrics, ETA Estimation.

Covers:
- schemas: SubPhaseProgress, LiveMetrics, updated PhaseProgress, updated ExecutionStatus
- pipeline_executor: progress computation, sub-phase parsing, live metrics, ETA
- reset exclusion: Reset All excludes phase0_indexing
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path):
    """Create a temporary project structure."""
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / ".cache" / ".chroma").mkdir(parents=True)

    (tmp_path / "config" / "phases_config.yaml").write_text(
        """
phases:
  phase0_indexing:
    enabled: true
    name: "Repository Indexing"
    order: 0
    dependencies: []
  phase1_architecture_facts:
    enabled: true
    name: "Architecture Facts"
    order: 1
    dependencies: [phase0_indexing]
  phase2_architecture_analysis:
    enabled: true
    name: "Architecture Analysis"
    order: 2
    dependencies: [phase1_architecture_facts]
  phase3_architecture_synthesis:
    enabled: true
    name: "Architecture Synthesis"
    order: 3
    dependencies: [phase2_architecture_analysis]
  phase4_development_planning:
    enabled: true
    name: "Development Planning"
    order: 4
    dependencies: [phase2_architecture_analysis]
  phase5_code_generation:
    enabled: true
    name: "Code Generation"
    order: 5
    dependencies: [phase4_development_planning]
"""
    )

    return tmp_path


@pytest.fixture()
def mock_settings(tmp_project):
    """Patch settings for pipeline_executor and history_service."""
    with (
        patch("ui.backend.services.pipeline_executor.settings") as se,
        patch("ui.backend.services.history_service.settings") as sh,
    ):
        se.project_root = tmp_project
        se.knowledge_dir = tmp_project / "knowledge"
        se.phases_config = tmp_project / "config" / "phases_config.yaml"
        se.metrics_file = tmp_project / "logs" / "metrics.jsonl"
        se.run_report = tmp_project / "knowledge" / "run_report.json"
        se.run_history = tmp_project / "logs" / "run_history.jsonl"
        se.logs_dir = tmp_project / "logs"
        se.env_file = tmp_project / ".env"

        sh.project_root = tmp_project
        sh.knowledge_dir = tmp_project / "knowledge"
        sh.run_report = tmp_project / "knowledge" / "run_report.json"
        sh.run_history = tmp_project / "logs" / "run_history.jsonl"
        sh.logs_dir = tmp_project / "logs"
        sh.metrics_file = tmp_project / "logs" / "metrics.jsonl"

        yield se


@pytest.fixture()
def metrics_file(tmp_project):
    """Return path to the metrics.jsonl file."""
    return tmp_project / "logs" / "metrics.jsonl"


def write_metrics(metrics_file: Path, events: list[dict]) -> None:
    """Write metrics events to the JSONL file."""
    with open(metrics_file, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


# =============================================================================
# Schema Tests
# =============================================================================


class TestNewSchemas:
    """Tests for new/updated schema models."""

    def test_sub_phase_progress_defaults(self):
        from ui.backend.schemas import SubPhaseProgress

        sp = SubPhaseProgress(name="architecture_collector")
        assert sp.status == "completed"
        assert sp.total_tokens == 0
        assert sp.tasks == []
        assert sp.duration_seconds is None

    def test_sub_phase_progress_full(self):
        from ui.backend.schemas import SubPhaseProgress

        sp = SubPhaseProgress(
            name="dependency_analyzer",
            status="failed",
            duration_seconds=45.2,
            total_tokens=1500,
            tasks=["analyze_deps", "map_imports"],
        )
        assert sp.name == "dependency_analyzer"
        assert sp.status == "failed"
        assert sp.total_tokens == 1500
        assert len(sp.tasks) == 2

    def test_live_metrics_defaults(self):
        from ui.backend.schemas import LiveMetrics

        lm = LiveMetrics()
        assert lm.total_tokens == 0
        assert lm.crew_completions == 0

    def test_live_metrics_values(self):
        from ui.backend.schemas import LiveMetrics

        lm = LiveMetrics(total_tokens=25000, crew_completions=5)
        assert lm.total_tokens == 25000
        assert lm.crew_completions == 5

    def test_phase_progress_with_sub_phases(self):
        from ui.backend.schemas import PhaseProgress, SubPhaseProgress

        pp = PhaseProgress(
            phase_id="deep_analysis",
            name="Architecture Analysis",
            status="running",
            sub_phases=[
                SubPhaseProgress(name="arch_analyzer", total_tokens=500),
                SubPhaseProgress(name="dep_analyzer", total_tokens=300),
            ],
            total_tokens=800,
        )
        assert len(pp.sub_phases) == 2
        assert pp.total_tokens == 800

    def test_phase_progress_empty_sub_phases(self):
        from ui.backend.schemas import PhaseProgress

        pp = PhaseProgress(phase_id="indexing", name="Indexing")
        assert pp.sub_phases == []
        assert pp.total_tokens == 0

    def test_execution_status_new_fields_defaults(self):
        from ui.backend.schemas import ExecutionStatus

        es = ExecutionStatus()
        assert es.progress_percent == 0
        assert es.completed_phase_count == 0
        assert es.total_phase_count == 0
        assert es.eta_seconds is None
        assert es.live_metrics is None

    def test_execution_status_new_fields_values(self):
        from ui.backend.schemas import ExecutionStatus, LiveMetrics

        es = ExecutionStatus(
            state="running",
            progress_percent=66.7,
            completed_phase_count=2,
            total_phase_count=3,
            eta_seconds=120.5,
            live_metrics=LiveMetrics(total_tokens=10000, crew_completions=3),
        )
        assert es.progress_percent == 66.7
        assert es.completed_phase_count == 2
        assert es.total_phase_count == 3
        assert es.eta_seconds == 120.5
        assert es.live_metrics is not None
        assert es.live_metrics.total_tokens == 10000


# =============================================================================
# Pipeline Executor — Progress Computation
# =============================================================================


class TestProgressComputation:
    """Tests for progress percent computation in get_status()."""

    def test_idle_status_zero_progress(self, mock_settings):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()

        status = executor.get_status()
        assert status["state"] == "idle"
        assert status["progress_percent"] == 0
        assert status["completed_phase_count"] == 0
        assert status["total_phase_count"] == 0

    def test_progress_all_completed(self, mock_settings, metrics_file):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        write_metrics(metrics_file, [
            {"event": "phase_start", "timestamp": "T1", "data": {"phase": "p1", "name": "Phase 1"}},
            {"event": "phase_complete", "timestamp": "T2", "data": {"phase": "p1", "duration_seconds": 10}},
            {"event": "phase_start", "timestamp": "T3", "data": {"phase": "p2", "name": "Phase 2"}},
            {"event": "phase_complete", "timestamp": "T4", "data": {"phase": "p2", "duration_seconds": 20}},
        ])

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "completed"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1", "p2"], started_at="T0")
        executor._started_at = time.monotonic() - 30

        status = executor.get_status()
        assert status["completed_phase_count"] == 2
        assert status["total_phase_count"] == 2
        assert status["progress_percent"] == 100.0

    def test_progress_one_running(self, mock_settings, metrics_file):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        write_metrics(metrics_file, [
            {"event": "phase_start", "timestamp": "T1", "data": {"phase": "p1", "name": "Phase 1"}},
            {"event": "phase_complete", "timestamp": "T2", "data": {"phase": "p1", "duration_seconds": 10}},
            {"event": "phase_start", "timestamp": "T3", "data": {"phase": "p2", "name": "Phase 2"}},
        ])

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1", "p2", "p3"], started_at="T0")
        executor._started_at = time.monotonic() - 10

        status = executor.get_status()
        assert status["completed_phase_count"] == 1
        assert status["total_phase_count"] == 3
        # (1 completed + 0.5 running) / 3 * 100 = 50.0
        assert status["progress_percent"] == 50.0

    def test_progress_no_phases(self, mock_settings):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=[], started_at="T0")
        executor._started_at = time.monotonic() - 5

        status = executor.get_status()
        assert status["progress_percent"] == 0


# =============================================================================
# Pipeline Executor — Sub-Phase Parsing
# =============================================================================


class TestSubPhaseParsing:
    """Tests for sub-phase parsing from mini_crew_complete events."""

    def test_sub_phases_attached_to_correct_parent(self, mock_settings, metrics_file):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        write_metrics(metrics_file, [
            {"event": "phase_start", "timestamp": "T1", "data": {"phase": "deep_analysis", "name": "Analysis"}},
            {
                "event": "mini_crew_complete",
                "timestamp": "T2",
                "data": {
                    "crew_type": "architecture_analyzer",
                    "crew_name": "Arch Analyzer",
                    "total_tokens": 500,
                    "duration_seconds": 12.5,
                    "tasks": ["analyze"],
                },
            },
            {
                "event": "mini_crew_complete",
                "timestamp": "T3",
                "data": {
                    "crew_type": "dependency_analyzer",
                    "crew_name": "Dep Analyzer",
                    "total_tokens": 300,
                    "duration_seconds": 8.0,
                },
            },
        ])

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["deep_analysis"], started_at="T0")
        executor._started_at = time.monotonic() - 20

        status = executor.get_status()
        progress = status["phase_progress"]
        assert len(progress) == 1

        phase = progress[0]
        assert phase["phase_id"] == "deep_analysis"
        assert len(phase["sub_phases"]) == 2
        assert phase["sub_phases"][0]["name"] == "Arch Analyzer"
        assert phase["sub_phases"][0]["total_tokens"] == 500
        assert phase["sub_phases"][1]["name"] == "Dep Analyzer"
        assert phase["total_tokens"] == 800  # 500 + 300

    def test_sub_phases_with_failed_crew(self, mock_settings, metrics_file):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        write_metrics(metrics_file, [
            {"event": "phase_start", "timestamp": "T1", "data": {"phase": "facts_extraction", "name": "Facts"}},
            {
                "event": "mini_crew_complete",
                "timestamp": "T2",
                "data": {"crew_type": "architecture_collector", "crew_name": "Arch Collector", "total_tokens": 200},
            },
            {
                "event": "mini_crew_failed",
                "timestamp": "T3",
                "data": {"crew_type": "security_collector", "crew_name": "Security Collector", "total_tokens": 50},
            },
        ])

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["facts_extraction"], started_at="T0")
        executor._started_at = time.monotonic() - 10

        status = executor.get_status()
        phase = status["phase_progress"][0]
        assert len(phase["sub_phases"]) == 2
        assert phase["sub_phases"][0]["status"] == "completed"
        assert phase["sub_phases"][1]["status"] == "failed"

    def test_unknown_crew_type_no_parent(self, mock_settings, metrics_file):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        write_metrics(metrics_file, [
            {"event": "phase_start", "timestamp": "T1", "data": {"phase": "facts_extraction", "name": "Facts"}},
            {
                "event": "mini_crew_complete",
                "timestamp": "T2",
                "data": {"crew_type": "unknown_crew", "crew_name": "Unknown", "total_tokens": 100},
            },
        ])

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["facts_extraction"], started_at="T0")
        executor._started_at = time.monotonic() - 5

        status = executor.get_status()
        phase = status["phase_progress"][0]
        # Unknown crew doesn't map to facts_extraction, so no sub-phases attached
        assert len(phase["sub_phases"]) == 0

    def test_no_metrics_file_empty_progress(self, mock_settings):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 5

        status = executor.get_status()
        assert status["phase_progress"] == []


# =============================================================================
# Pipeline Executor — Live Metrics
# =============================================================================


class TestLiveMetrics:
    """Tests for live metrics aggregation."""

    def test_live_metrics_when_running(self, mock_settings, metrics_file):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        write_metrics(metrics_file, [
            {"event": "phase_start", "timestamp": "T1", "data": {"phase": "p1", "name": "Phase 1"}},
            {"event": "mini_crew_complete", "timestamp": "T2", "data": {"total_tokens": 1000}},
            {"event": "mini_crew_complete", "timestamp": "T3", "data": {"total_tokens": 2000}},
            {"event": "mini_crew_complete", "timestamp": "T4", "data": {"total_tokens": 500}},
        ])

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 10

        status = executor.get_status()
        assert status["live_metrics"] is not None
        assert status["live_metrics"]["total_tokens"] == 3500
        assert status["live_metrics"]["crew_completions"] == 3

    def test_live_metrics_not_returned_when_idle(self, mock_settings):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()

        status = executor.get_status()
        assert status["live_metrics"] is None

    def test_live_metrics_not_returned_when_completed(self, mock_settings, metrics_file):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        write_metrics(metrics_file, [
            {"event": "mini_crew_complete", "timestamp": "T1", "data": {"total_tokens": 1000}},
        ])

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "completed"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 60

        status = executor.get_status()
        assert status["live_metrics"] is None

    def test_live_metrics_no_file(self, mock_settings):
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 5

        status = executor.get_status()
        assert status["live_metrics"] is None


# =============================================================================
# Pipeline Executor — ETA Estimation
# =============================================================================


class TestETAEstimation:
    """Tests for ETA estimation from historical runs."""

    def test_eta_with_history(self, mock_settings, tmp_project):
        from ui.backend.services.history_service import append_run_to_history
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        # Add some completed runs
        for i in range(3):
            append_run_to_history({
                "run_id": f"hist_{i}",
                "status": "completed",
                "trigger": "pipeline",
                "duration_seconds": 300.0,  # 5 minutes each
            })

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 60  # 1 minute elapsed

        status = executor.get_status()
        # avg=300, elapsed=60, remaining=240
        assert status["eta_seconds"] is not None
        assert 230 <= status["eta_seconds"] <= 250  # ~240 with rounding

    def test_eta_none_with_insufficient_history(self, mock_settings, tmp_project):
        from ui.backend.services.history_service import append_run_to_history
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        # Only 1 completed run (need >= 2)
        append_run_to_history({
            "run_id": "hist_0",
            "status": "completed",
            "trigger": "pipeline",
            "duration_seconds": 300.0,
        })

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 60

        status = executor.get_status()
        assert status["eta_seconds"] is None

    def test_eta_none_when_idle(self, mock_settings):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()

        status = executor.get_status()
        assert status["eta_seconds"] is None

    def test_eta_floors_at_zero(self, mock_settings, tmp_project):
        from ui.backend.services.history_service import append_run_to_history
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        # History says runs take 60s, but we've been running for 120s already
        for i in range(3):
            append_run_to_history({
                "run_id": f"hist_{i}",
                "status": "completed",
                "trigger": "pipeline",
                "duration_seconds": 60.0,
            })

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 120  # 2 minutes elapsed > avg 60s

        status = executor.get_status()
        assert status["eta_seconds"] == 0.0

    def test_eta_ignores_reset_entries(self, mock_settings, tmp_project):
        from ui.backend.services.history_service import append_run_to_history
        from ui.backend.services.pipeline_executor import PipelineExecutor, RunInfo

        # 2 pipeline runs + 1 reset (should ignore reset)
        append_run_to_history({"run_id": "r1", "status": "completed", "trigger": "pipeline", "duration_seconds": 200.0})
        append_run_to_history({"run_id": "r2", "status": "completed", "trigger": "pipeline", "duration_seconds": 400.0})
        append_run_to_history({"run_id": "reset1", "status": "reset", "trigger": "reset", "duration_seconds": 2.0})

        executor = PipelineExecutor.__new__(PipelineExecutor)
        executor._init()
        executor.state = "running"
        executor.current_run = RunInfo(run_id="test", preset=None, phases=["p1"], started_at="T0")
        executor._started_at = time.monotonic() - 100

        status = executor.get_status()
        # avg of 200 and 400 = 300, elapsed=100, remaining=200
        assert status["eta_seconds"] is not None
        assert 190 <= status["eta_seconds"] <= 210


# =============================================================================
# Crew-to-Phase Mapping
# =============================================================================


class TestCrewPhaseMapping:
    """Tests for _CREW_PHASE_MAP correctness."""

    def test_all_fact_collectors_map_to_facts(self):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        facts_crews = [
            "architecture_collector",
            "dependency_collector",
            "quality_collector",
            "security_collector",
            "test_collector",
        ]
        for crew in facts_crews:
            assert PipelineExecutor._CREW_PHASE_MAP.get(crew) == "facts_extraction", f"{crew} should map to facts_extraction"

    def test_all_analyzers_map_to_analysis(self):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        analysis_crews = [
            "architecture_analyzer",
            "dependency_analyzer",
            "quality_analyzer",
            "impact_analyzer",
        ]
        for crew in analysis_crews:
            assert PipelineExecutor._CREW_PHASE_MAP.get(crew) == "deep_analysis", f"{crew} should map to deep_analysis"

    def test_synthesis_crews_map_correctly(self):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        assert PipelineExecutor._CREW_PHASE_MAP["synthesis_crew"] == "synthesis"
        assert PipelineExecutor._CREW_PHASE_MAP["cross_cutting_crew"] == "synthesis"
        assert PipelineExecutor._CREW_PHASE_MAP["recommendation_crew"] == "synthesis"

    def test_codegen_crews_map_correctly(self):
        from ui.backend.services.pipeline_executor import PipelineExecutor

        assert PipelineExecutor._CREW_PHASE_MAP["code_generation_crew"] == "code_generation"
        assert PipelineExecutor._CREW_PHASE_MAP["code_validation_crew"] == "code_generation"


# =============================================================================
# Reset All Excludes Indexing
# =============================================================================


class TestResetAllExcludesIndexing:
    """Verify that the reset-all endpoint itself does not exclude indexing
    (that's a frontend concern), but test the backend reset-all behavior."""

    def test_reset_all_includes_indexing_by_default(self, tmp_project):
        """Backend reset-all resets everything including indexing."""
        with (
            patch("ui.backend.services.reset_service.settings") as s,
            patch("ui.backend.services.history_service.settings") as sh,
        ):
            s.project_root = tmp_project
            s.knowledge_dir = tmp_project / "knowledge"
            s.phases_config = tmp_project / "config" / "phases_config.yaml"
            s.run_report = tmp_project / "knowledge" / "run_report.json"
            s.run_history = tmp_project / "logs" / "run_history.jsonl"
            s.logs_dir = tmp_project / "logs"

            sh.run_history = tmp_project / "logs" / "run_history.jsonl"
            sh.knowledge_dir = tmp_project / "knowledge"

            from ui.backend.services.reset_service import compute_cascade

            result = compute_cascade(["phase0_indexing"])
            assert "phase0_indexing" in result

    def test_filtering_excludes_indexing(self):
        """Simulate frontend filter: completed phases minus indexing."""
        phases = [
            {"id": "phase0_indexing", "status": "completed"},
            {"id": "phase1_architecture_facts", "status": "completed"},
            {"id": "phase2_architecture_analysis", "status": "completed"},
            {"id": "phase3_architecture_synthesis", "status": "idle"},
        ]
        # Frontend logic
        reset_ids = [p["id"] for p in phases if p["status"] == "completed" and p["id"] != "phase0_indexing"]
        assert "phase0_indexing" not in reset_ids
        assert "phase1_architecture_facts" in reset_ids
        assert "phase2_architecture_analysis" in reset_ids
        assert len(reset_ids) == 2


class TestEmptyDirectoryNotCompleted:
    """After reset, empty recreated directories must NOT report as completed."""

    def test_empty_dir_is_not_completed(self, tmp_project):
        """An empty output directory should be detected as 'not completed'."""
        # Create empty dirs (simulating post-reset state)
        (tmp_project / "knowledge" / "development").mkdir(parents=True, exist_ok=True)
        (tmp_project / "knowledge" / "codegen").mkdir(parents=True, exist_ok=True)

        with patch("ui.backend.services.phase_runner.settings") as s:
            s.project_root = tmp_project
            s.phases_config = tmp_project / "config" / "phases_config.yaml"

            from ui.backend.services.phase_runner import get_pipeline_status

            status = get_pipeline_status()
            for p in status.phases:
                assert p.output_exists is False, f"{p.id} falsely reports output_exists=True"
                assert p.status != "completed", f"{p.id} falsely reports completed with empty dir"

    def test_dir_with_files_is_completed(self, tmp_project):
        """A directory with actual files should still report as completed."""
        dev_dir = tmp_project / "knowledge" / "phase4_planning"
        dev_dir.mkdir(parents=True, exist_ok=True)
        (dev_dir / "task1_plan.json").write_text('{"plan": true}')

        with patch("ui.backend.services.phase_runner.settings") as s:
            s.project_root = tmp_project
            s.phases_config = tmp_project / "config" / "phases_config.yaml"

            from ui.backend.services.phase_runner import get_pipeline_status

            status = get_pipeline_status()
            planning = next((p for p in status.phases if p.id == "phase4_development_planning"), None)
            assert planning is not None
            assert planning.output_exists is True
            assert planning.status == "completed"
