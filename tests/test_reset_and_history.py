"""
Tests for Pipeline Reset & Run History services.

Covers:
- history_service: append, read, legacy fallback, ordering
- reset_service: cascade computation, preview, execute (delete)
- reset router: preview, execute, reset-all, 409 on running
- schemas: ResetRequest, ResetPreview, ResetResult, RunHistoryEntry
"""

import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path):
    """Create a temporary project structure mimicking the real layout."""
    # Create per-phase dirs
    (tmp_path / "knowledge" / "phase0_indexing").mkdir(parents=True)
    (tmp_path / "knowledge" / "phase1_facts").mkdir(parents=True)
    (tmp_path / "knowledge" / "phase2_analysis").mkdir(parents=True)
    (tmp_path / "knowledge" / "phase3_synthesis" / "c4").mkdir(parents=True)
    (tmp_path / "knowledge" / "phase3_synthesis" / "arc42").mkdir(parents=True)
    (tmp_path / "knowledge" / "phase4_planning").mkdir(parents=True)
    (tmp_path / "knowledge" / "phase5_codegen").mkdir(parents=True)
    (tmp_path / "logs").mkdir()
    (tmp_path / "config").mkdir()

    # Create sample output files
    (tmp_path / "knowledge" / "phase0_indexing" / "index.bin").write_text("binary-data")
    (tmp_path / "knowledge" / "phase1_facts" / "architecture_facts.json").write_text('{"components": []}')
    (tmp_path / "knowledge" / "phase1_facts" / "evidence_map.json").write_text("{}")
    (tmp_path / "knowledge" / "phase2_analysis" / "analyzed_architecture.json").write_text("{}")
    (tmp_path / "knowledge" / "phase3_synthesis" / "c4" / "c4-context.md").write_text("# C4")
    (tmp_path / "knowledge" / "phase3_synthesis" / "arc42" / "arc42.md").write_text("# Arc42")
    (tmp_path / "knowledge" / "phase4_planning" / "TASK-001_plan.json").write_text("{}")
    (tmp_path / "knowledge" / "phase5_codegen" / "TASK-001_report.json").write_text("{}")

    # Create phases_config.yaml
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
    """Patch settings to use tmp_project as project root."""
    with patch("ui.backend.services.reset_service.settings") as s, patch(
        "ui.backend.services.history_service.settings"
    ) as sh:
        s.project_root = tmp_project
        s.knowledge_dir = tmp_project / "knowledge"
        s.phases_config = tmp_project / "config" / "phases_config.yaml"
        s.run_report = tmp_project / "knowledge" / "run_report.json"
        s.run_history = tmp_project / "logs" / "run_history.jsonl"
        s.logs_dir = tmp_project / "logs"

        sh.project_root = tmp_project
        sh.knowledge_dir = tmp_project / "knowledge"
        sh.run_report = tmp_project / "knowledge" / "run_report.json"
        sh.run_history = tmp_project / "logs" / "run_history.jsonl"
        sh.logs_dir = tmp_project / "logs"

        yield s


# =============================================================================
# History Service Tests
# =============================================================================


class TestHistoryService:
    """Tests for history_service.py."""

    def test_append_and_read(self, mock_settings):
        from ui.backend.services.history_service import append_run_to_history, get_run_history

        # Append two entries
        append_run_to_history({"run_id": "abc123", "status": "completed", "trigger": "pipeline"})
        append_run_to_history({"run_id": "def456", "status": "failed", "trigger": "pipeline"})

        history = get_run_history()
        assert len(history) == 2
        # Newest first
        assert history[0]["run_id"] == "def456"
        assert history[1]["run_id"] == "abc123"

    def test_read_empty_returns_empty(self, mock_settings):
        from ui.backend.services.history_service import get_run_history

        history = get_run_history()
        assert history == []

    def test_legacy_fallback(self, mock_settings, tmp_project):
        from ui.backend.services.history_service import get_run_history

        # Create legacy run_report.json
        report = {
            "run_id": "legacy1",
            "status": "completed",
            "timestamp": "2026-01-01T00:00:00",
            "planned_phases": ["phase0_indexing"],
            "total_duration": "5m 30s",
            "environment": {"preset": "facts_only"},
            "phases": [],
        }
        (tmp_project / "knowledge" / "run_report.json").write_text(json.dumps(report))

        history = get_run_history()
        assert len(history) == 1
        assert history[0]["run_id"] == "legacy1"
        assert history[0]["trigger"] == "pipeline"
        assert history[0]["preset"] == "facts_only"

    def test_limit_and_offset(self, mock_settings):
        from ui.backend.services.history_service import append_run_to_history, get_run_history

        for i in range(10):
            append_run_to_history({"run_id": f"run_{i}", "status": "completed"})

        # Limit
        history = get_run_history(limit=3)
        assert len(history) == 3
        assert history[0]["run_id"] == "run_9"

        # Offset
        history = get_run_history(limit=3, offset=2)
        assert len(history) == 3
        assert history[0]["run_id"] == "run_7"

    def test_malformed_lines_are_skipped(self, mock_settings, tmp_project):
        from ui.backend.services.history_service import get_run_history

        # Write a file with valid + invalid lines
        path = tmp_project / "logs" / "run_history.jsonl"
        path.write_text(
            '{"run_id":"good1","status":"ok"}\n'
            'THIS IS NOT JSON\n'
            '{"run_id":"good2","status":"ok"}\n'
        )

        history = get_run_history()
        assert len(history) == 2
        assert history[0]["run_id"] == "good2"

    def test_append_creates_parent_dir(self, mock_settings, tmp_project):
        from ui.backend.services.history_service import append_run_to_history

        # Remove logs dir
        shutil.rmtree(tmp_project / "logs")
        assert not (tmp_project / "logs").exists()

        append_run_to_history({"run_id": "new1", "status": "ok"})
        assert (tmp_project / "logs" / "run_history.jsonl").exists()


# =============================================================================
# Reset Service Tests
# =============================================================================


class TestResetService:
    """Tests for reset_service.py."""

    def test_compute_cascade_single_root(self, mock_settings):
        from ui.backend.services.reset_service import compute_cascade

        result = compute_cascade(["phase0_indexing"])
        # Phase 0 cascades to everything
        assert "phase0_indexing" in result
        assert "phase1_architecture_facts" in result
        assert "phase2_architecture_analysis" in result
        assert "phase3_architecture_synthesis" in result
        assert "phase4_development_planning" in result
        assert "phase5_code_generation" in result

    def test_compute_cascade_phase2(self, mock_settings):
        from ui.backend.services.reset_service import compute_cascade

        result = compute_cascade(["phase2_architecture_analysis"])
        # Phase 2 cascades to 3, 4, 5
        assert "phase2_architecture_analysis" in result
        assert "phase3_architecture_synthesis" in result
        assert "phase4_development_planning" in result
        assert "phase5_code_generation" in result
        # But NOT phase 0 or 1
        assert "phase0_indexing" not in result
        assert "phase1_architecture_facts" not in result

    def test_compute_cascade_leaf(self, mock_settings):
        from ui.backend.services.reset_service import compute_cascade

        result = compute_cascade(["phase5_code_generation"])
        assert result == ["phase5_code_generation"]

    def test_compute_cascade_phase4(self, mock_settings):
        from ui.backend.services.reset_service import compute_cascade

        result = compute_cascade(["phase4_development_planning"])
        assert "phase4_development_planning" in result
        assert "phase5_code_generation" in result
        assert "phase3_architecture_synthesis" not in result

    def test_preview_shows_correct_files(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import preview_reset

        result = preview_reset(["phase1_architecture_facts"], cascade=False)
        assert "phase1_architecture_facts" in result["phases_to_reset"]
        assert any("architecture_facts.json" in f for f in result["files_to_delete"])

    def test_preview_with_cascade(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import preview_reset

        result = preview_reset(["phase1_architecture_facts"], cascade=True)
        assert len(result["phases_to_reset"]) >= 5  # phase1 -> 2,3,4,5

    def test_preview_no_cascade(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import preview_reset

        result = preview_reset(["phase1_architecture_facts"], cascade=False)
        assert result["phases_to_reset"] == ["phase1_architecture_facts"]

    def test_execute_deletes_phase_dir(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import execute_reset

        facts_dir = tmp_project / "knowledge" / "phase1_facts"
        assert facts_dir.exists()

        result = execute_reset(["phase1_architecture_facts"], cascade=False)

        # Dir contents deleted
        assert result["deleted_count"] >= 1
        assert "phase1_architecture_facts" in result["reset_phases"]

    def test_execute_with_cascade_deletes_dependents(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import execute_reset

        result = execute_reset(["phase2_architecture_analysis"], cascade=True)
        # Should delete phase 2, 3, 4, 5 outputs
        assert "phase2_architecture_analysis" in result["reset_phases"]
        assert "phase3_architecture_synthesis" in result["reset_phases"]
        assert "phase4_development_planning" in result["reset_phases"]
        assert "phase5_code_generation" in result["reset_phases"]

        # Verify files are gone
        assert not (tmp_project / "knowledge" / "phase2_analysis" / "analyzed_architecture.json").exists()
        assert not (tmp_project / "knowledge" / "phase3_synthesis" / "c4" / "c4-context.md").exists()

    def test_execute_recreates_empty_dirs(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import execute_reset

        execute_reset(["phase4_development_planning"], cascade=False)
        # Dir should be recreated empty
        plan_dir = tmp_project / "knowledge" / "phase4_planning"
        assert plan_dir.exists()
        assert list(plan_dir.iterdir()) == []

    def test_execute_appends_to_history(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import execute_reset

        execute_reset(["phase5_code_generation"], cascade=False)

        history_path = tmp_project / "logs" / "run_history.jsonl"
        assert history_path.exists()
        entries = [json.loads(line) for line in history_path.read_text().strip().split("\n")]
        assert len(entries) == 1
        assert entries[0]["trigger"] == "reset"
        assert entries[0]["status"] == "reset"
        assert "phase5_code_generation" in entries[0]["phases"]

    def test_execute_nonexistent_phase_no_error(self, mock_settings, tmp_project):
        from ui.backend.services.reset_service import execute_reset

        # Should not crash for a phase with no matching files
        result = execute_reset(["phase99_fake"], cascade=False)
        assert result["deleted_count"] == 0


# =============================================================================
# Schema Tests
# =============================================================================


class TestSchemas:
    """Tests for reset-related schemas."""

    def test_reset_request_defaults(self):
        from ui.backend.schemas import ResetRequest

        req = ResetRequest(phase_ids=["phase1_architecture_facts"])
        assert req.cascade is True

    def test_reset_request_override(self):
        from ui.backend.schemas import ResetRequest

        req = ResetRequest(phase_ids=["phase1_architecture_facts"], cascade=False)
        assert req.cascade is False

    def test_reset_preview_schema(self):
        from ui.backend.schemas import ResetPreview

        preview = ResetPreview(
            phases_to_reset=["phase1", "phase2"],
            files_to_delete=["/a/b.json"],
        )
        assert len(preview.phases_to_reset) == 2

    def test_reset_result_schema(self):
        from ui.backend.schemas import ResetResult

        result = ResetResult(
            reset_phases=["phase1"],
            deleted_count=5,
            timestamp="2026-02-12T00:00:00",
        )
        assert result.deleted_count == 5

    def test_run_history_entry_extended_fields(self):
        from ui.backend.schemas import RunHistoryEntry

        entry = RunHistoryEntry(
            run_id="abc",
            status="completed",
            trigger="pipeline",
            completed_at="2026-02-12T00:00:00",
            duration_seconds=120.5,
        )
        assert entry.trigger == "pipeline"
        assert entry.duration_seconds == 120.5
        assert entry.completed_at is not None

    def test_run_history_entry_reset_trigger(self):
        from ui.backend.schemas import RunHistoryEntry

        entry = RunHistoryEntry(
            run_id="reset_001",
            status="reset",
            trigger="reset",
            phases=["phase1_architecture_facts", "phase2_architecture_analysis"],
        )
        assert entry.trigger == "reset"


# =============================================================================
# Router Tests (using FastAPI TestClient)
# =============================================================================


class TestResetRouter:
    """Tests for the reset router endpoints."""

    @pytest.fixture()
    def client(self, mock_settings):
        """Create a TestClient for the FastAPI app."""
        # Patch settings in all modules that import it
        with patch("ui.backend.config.settings", mock_settings), patch(
            "ui.backend.routers.reset.executor"
        ) as mock_executor:
            mock_executor.state = "idle"

            from fastapi.testclient import TestClient

            from ui.backend.main import app

            yield TestClient(app), mock_executor

    def test_preview_endpoint(self, client):
        test_client, _ = client
        resp = test_client.post(
            "/api/reset/preview",
            json={"phase_ids": ["phase5_code_generation"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "phases_to_reset" in data
        assert "phase5_code_generation" in data["phases_to_reset"]

    def test_execute_endpoint(self, client):
        test_client, _ = client
        resp = test_client.post(
            "/api/reset/execute",
            json={"phase_ids": ["phase5_code_generation"], "cascade": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reset_phases" in data
        assert "deleted_count" in data
        assert "timestamp" in data

    def test_execute_blocked_when_running(self, client):
        test_client, mock_executor = client
        mock_executor.state = "running"
        resp = test_client.post(
            "/api/reset/execute",
            json={"phase_ids": ["phase1_architecture_facts"]},
        )
        assert resp.status_code == 409

    def test_reset_all_endpoint(self, client):
        test_client, _ = client
        resp = test_client.post("/api/reset/all")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reset_phases"]) >= 1

    def test_reset_all_blocked_when_running(self, client):
        test_client, mock_executor = client
        mock_executor.state = "running"
        resp = test_client.post("/api/reset/all")
        assert resp.status_code == 409

    def test_history_endpoint(self, client):
        test_client, _ = client
        resp = test_client.get("/api/pipeline/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
