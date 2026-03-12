"""Smoke tests for history stats and phase frequency aggregation."""

import json
from pathlib import Path

from ui.backend.services import history_service


def test_phase_frequency_and_tokens_aggregated(tmp_path, monkeypatch):
  """get_history_stats should expose phase_frequency and token totals."""
  # Prepare a fake run_history.jsonl
  history_path = tmp_path / "logs" / "run_history.jsonl"
  history_path.parent.mkdir(parents=True, exist_ok=True)
  entries = [
    {
      "run_id": "r1",
      "status": "completed",
      "trigger": "pipeline",
      "preset": "plan",
      "phases": ["triage", "plan"],
      "duration_seconds": 12.3,
    },
    {
      "run_id": "r2",
      "status": "failed",
      "trigger": "pipeline",
      "preset": "plan",
      "phases": ["triage", "plan", "implement"],
      "duration_seconds": 30.0,
    },
  ]
  with open(history_path, "w", encoding="utf-8") as f:
    for e in entries:
      f.write(json.dumps(e) + "\n")

  # Prepare a fake metrics.jsonl with mini_crew_complete for r1
  metrics_path = tmp_path / "logs" / "metrics.jsonl"
  metrics_path.write_text(
    "\n".join(
      [
        json.dumps({"data": {"event": "mini_crew_complete", "run_id": "r1", "total_tokens": 1000}}),
        json.dumps({"data": {"event": "mini_crew_complete", "run_id": "r1", "total_tokens": 500}}),
      ]
    ),
    encoding="utf-8",
  )

  # Point settings at tmp paths
  from ui.backend import config as backend_config

  monkeypatch.setattr(backend_config.settings, "run_history", history_path)
  monkeypatch.setattr(backend_config.settings, "metrics_file", metrics_path)

  stats = history_service.get_history_stats()

  assert stats["total_runs"] == 2
  # triage appears in both, plan in both, implement once
  assert stats["phase_frequency"]["triage"] == 2
  assert stats["phase_frequency"]["plan"] == 2
  assert stats["phase_frequency"]["implement"] == 1
  # token total aggregated from metrics.jsonl (1000 + 500)
  assert stats["total_tokens"] == 1500

