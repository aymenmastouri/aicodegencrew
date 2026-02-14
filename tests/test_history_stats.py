"""
Tests for History Stats (aggregated operational intelligence).

Covers:
- get_history_stats: counts, rates, durations, preset frequency, phase frequency
- _aggregate_tokens: metrics.jsonl parsing
- _enrich_tokens: per-entry token attachment
- API endpoint: /api/pipeline/history/stats
- Route ordering: /stats not shadowed by /{run_id}
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_project(tmp_path):
    """Create a temporary project structure."""
    (tmp_path / "knowledge" / "discover").mkdir(parents=True)
    (tmp_path / "knowledge" / "extract").mkdir(parents=True)
    (tmp_path / "logs").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "phases_config.yaml").write_text(
        """
phases:
  discover:
    enabled: true
    name: "Repository Indexing"
    order: 0
    dependencies: []
  extract:
    enabled: true
    name: "Architecture Facts"
    order: 1
    dependencies: [discover]
"""
    )
    return tmp_path


@pytest.fixture()
def mock_settings(tmp_project):
    """Patch settings to use tmp_project as project root."""
    with patch("ui.backend.services.history_service.settings") as sh:
        sh.project_root = tmp_project
        sh.knowledge_dir = tmp_project / "knowledge"
        sh.run_report = tmp_project / "knowledge" / "run_report.json"
        sh.run_history = tmp_project / "logs" / "run_history.jsonl"
        sh.logs_dir = tmp_project / "logs"
        sh.metrics_file = tmp_project / "logs" / "metrics.jsonl"
        yield sh


def _append(path: Path, entry: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# =============================================================================
# Tests
# =============================================================================


class TestHistoryStats:
    """Tests for get_history_stats()."""

    def test_get_history_stats_empty(self, mock_settings):
        """Zeroed stats on empty JSONL."""
        from ui.backend.services.history_service import get_history_stats

        stats = get_history_stats()
        assert stats["total_runs"] == 0
        assert stats["total_resets"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration_seconds"] == 0.0
        assert stats["total_tokens"] == 0
        assert stats["total_deleted_files"] == 0
        assert stats["most_used_preset"] is None
        assert stats["last_run_at"] is None
        assert stats["phase_frequency"] == {}

    def test_get_history_stats_basic(self, mock_settings, tmp_project):
        """Counts, rate, avg_duration from a few entries."""
        from ui.backend.services.history_service import get_history_stats

        hist = tmp_project / "logs" / "run_history.jsonl"
        _append(hist, {
            "run_id": "r1", "status": "completed", "trigger": "pipeline",
            "preset": "full", "phases": ["discover", "extract"],
            "started_at": "2026-01-01T10:00:00", "duration_seconds": 120,
        })
        _append(hist, {
            "run_id": "r2", "status": "completed", "trigger": "pipeline",
            "preset": "full", "phases": ["discover"],
            "started_at": "2026-01-02T10:00:00", "duration_seconds": 60,
        })

        stats = get_history_stats()
        assert stats["total_runs"] == 2
        assert stats["total_resets"] == 0
        assert stats["success_count"] == 2
        assert stats["success_rate"] == 100.0
        assert stats["avg_duration_seconds"] == 90.0

    def test_get_history_stats_success_rate(self, mock_settings, tmp_project):
        """2 success + 1 fail = 66.7%."""
        from ui.backend.services.history_service import get_history_stats

        hist = tmp_project / "logs" / "run_history.jsonl"
        _append(hist, {"run_id": "r1", "status": "completed", "trigger": "pipeline",
                       "duration_seconds": 30})
        _append(hist, {"run_id": "r2", "status": "completed", "trigger": "pipeline",
                       "duration_seconds": 60})
        _append(hist, {"run_id": "r3", "status": "failed", "trigger": "pipeline"})

        stats = get_history_stats()
        assert stats["success_count"] == 2
        assert stats["failed_count"] == 1
        assert stats["success_rate"] == 66.7

    def test_get_history_stats_preset_frequency(self, mock_settings, tmp_project):
        """Most_used_preset picks the most frequent."""
        from ui.backend.services.history_service import get_history_stats

        hist = tmp_project / "logs" / "run_history.jsonl"
        _append(hist, {"run_id": "r1", "status": "completed", "trigger": "pipeline",
                       "preset": "quick", "duration_seconds": 10})
        _append(hist, {"run_id": "r2", "status": "completed", "trigger": "pipeline",
                       "preset": "full", "duration_seconds": 20})
        _append(hist, {"run_id": "r3", "status": "completed", "trigger": "pipeline",
                       "preset": "full", "duration_seconds": 30})

        stats = get_history_stats()
        assert stats["most_used_preset"] == "full"

    def test_get_history_stats_phase_frequency(self, mock_settings, tmp_project):
        """Phase_frequency dict is computed correctly."""
        from ui.backend.services.history_service import get_history_stats

        hist = tmp_project / "logs" / "run_history.jsonl"
        _append(hist, {"run_id": "r1", "status": "completed", "trigger": "pipeline",
                       "phases": ["discover", "extract"], "duration_seconds": 10})
        _append(hist, {"run_id": "r2", "status": "completed", "trigger": "pipeline",
                       "phases": ["discover"], "duration_seconds": 20})

        stats = get_history_stats()
        assert stats["phase_frequency"] == {"discover": 2, "extract": 1}

    def test_get_history_stats_deleted_files(self, mock_settings, tmp_project):
        """Total_deleted_files sums deleted_count from resets."""
        from ui.backend.services.history_service import get_history_stats

        hist = tmp_project / "logs" / "run_history.jsonl"
        _append(hist, {"run_id": "reset1", "status": "completed", "trigger": "reset",
                       "deleted_count": 5})
        _append(hist, {"run_id": "reset2", "status": "completed", "trigger": "reset",
                       "deleted_count": 3})
        _append(hist, {"run_id": "r1", "status": "completed", "trigger": "pipeline",
                       "duration_seconds": 10})

        stats = get_history_stats()
        assert stats["total_resets"] == 2
        assert stats["total_deleted_files"] == 8

    def test_history_stats_api_endpoint(self, mock_settings):
        """TestClient GET /api/pipeline/history/stats returns valid JSON."""
        from fastapi.testclient import TestClient

        from ui.backend.routers.pipeline import router

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        resp = client.get("/api/pipeline/history/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_runs" in data
        assert "success_rate" in data
        assert "phase_frequency" in data

    def test_history_entry_includes_deleted_count(self, mock_settings, tmp_project):
        """Reset entries return deleted_count."""
        from ui.backend.services.history_service import get_run_history, append_run_to_history

        append_run_to_history({
            "run_id": "reset1", "status": "completed", "trigger": "reset",
            "phases": ["extract"], "deleted_count": 7,
        })

        history = get_run_history()
        assert len(history) == 1
        assert history[0]["deleted_count"] == 7

    def test_history_entry_includes_total_tokens(self, mock_settings, tmp_project):
        """Token enrichment works — metrics.jsonl tokens attached to entries."""
        from ui.backend.services.history_service import append_run_to_history, get_run_history

        append_run_to_history({
            "run_id": "run1", "status": "completed", "trigger": "pipeline",
            "phases": ["discover"], "duration_seconds": 30,
        })

        # Write metrics events
        metrics_path = tmp_project / "logs" / "metrics.jsonl"
        _append(metrics_path, {
            "msg": "mini_crew_complete",
            "data": {"event": "mini_crew_complete", "run_id": "run1", "total_tokens": 500},
        })
        _append(metrics_path, {
            "msg": "mini_crew_complete",
            "data": {"event": "mini_crew_complete", "run_id": "run1", "total_tokens": 300},
        })

        history = get_run_history()
        assert history[0]["total_tokens"] == 800

    def test_history_entry_tokens_use_engine_run_id(self, mock_settings, tmp_project):
        """If UI run_id differs, token enrichment falls back to engine_run_id."""
        from ui.backend.services.history_service import append_run_to_history, get_run_history

        append_run_to_history({
            "run_id": "ui_run_1",
            "engine_run_id": "eng12345",
            "status": "completed",
            "trigger": "pipeline",
            "phases": ["discover"],
        })

        metrics_path = tmp_project / "logs" / "metrics.jsonl"
        _append(metrics_path, {
            "msg": "mini_crew_complete",
            "data": {"event": "mini_crew_complete", "run_id": "eng12345", "total_tokens": 750},
        })

        history = get_run_history()
        assert history[0]["run_id"] == "ui_run_1"
        assert history[0]["total_tokens"] == 750

    def test_run_detail_matches_report_by_engine_run_id(self, mock_settings, tmp_project):
        """Run detail should enrich from run_report when report uses engine_run_id."""
        from ui.backend.services.history_service import append_run_to_history, get_run_detail

        append_run_to_history({
            "run_id": "ui_run_2",
            "engine_run_id": "eng99999",
            "status": "completed",
            "trigger": "pipeline",
            "phases": ["extract"],
        })

        report = {
            "run_id": "eng99999",
            "status": "success",
            "environment": {"preset": "full"},
            "phases": [{"phase": "extract", "status": "completed"}],
        }
        (tmp_project / "knowledge" / "run_report.json").write_text(json.dumps(report), encoding="utf-8")

        metrics_path = tmp_project / "logs" / "metrics.jsonl"
        _append(metrics_path, {
            "msg": "mini_crew_complete",
            "data": {"event": "mini_crew_complete", "run_id": "eng99999", "total_tokens": 123},
        })

        detail = get_run_detail("ui_run_2")
        assert detail is not None
        assert detail["phase_results"] == [{"phase": "extract", "status": "completed"}]
        assert detail["environment"]["preset"] == "full"
        assert len(detail["metrics_events"]) == 1

    def test_stats_route_before_run_id(self, mock_settings):
        """/stats not treated as run_id — both routes work."""
        from fastapi.testclient import TestClient

        from ui.backend.routers.pipeline import router

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        # /stats should return 200 with stats JSON
        resp_stats = client.get("/api/pipeline/history/stats")
        assert resp_stats.status_code == 200
        assert "total_runs" in resp_stats.json()

        # /nonexistent should return 404 (run_id not found)
        resp_detail = client.get("/api/pipeline/history/nonexistent")
        assert resp_detail.status_code == 404


