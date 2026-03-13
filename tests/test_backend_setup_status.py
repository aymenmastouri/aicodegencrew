"""Tests for the /api/health/setup-status endpoint and env API error handling."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from ui.backend.main import app


def _write_env(path: Path, values: dict[str, Any]) -> None:
    lines = [f"{k}={v}\n" for k, v in values.items()]
    path.write_text("".join(lines), encoding="utf-8")


def test_setup_status_reports_missing_project_and_llm(tmp_path, monkeypatch):
    """When PROJECT_PATH/LLM vars are missing, errors list should describe it."""
    env_path = tmp_path / ".env"
    _write_env(env_path, {"SOME_OTHER": "1"})

    from ui.backend import config as backend_config

    # Point settings at tmp directories
    monkeypatch.setattr(backend_config.settings, "project_root", tmp_path)
    monkeypatch.setattr(backend_config.settings, "env_file", env_path)
    monkeypatch.setattr(backend_config.settings, "run_history", tmp_path / "logs" / "run_history.jsonl")

    client = TestClient(app)
    resp = client.get("/api/health/setup-status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["repo_configured"] is False
    assert data["llm_configured"] is False
    # At least one descriptive error for repo + one for LLM config
    errors = " ".join(data.get("errors", []))
    assert "PROJECT_PATH" in errors
    assert "Missing LLM configuration" in errors


def test_setup_status_with_valid_project_and_llm(tmp_path, monkeypatch):
    """Valid PROJECT_PATH and LLM config should clear the corresponding errors."""
    project_dir = tmp_path / "repo"
    project_dir.mkdir()
    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        {
            "PROJECT_PATH": str(project_dir),
            "LLM_PROVIDER": "openai-compatible",
            "MODEL": "gpt-oss-120b",
            "API_BASE": "http://localhost:8080",
        },
    )

    from ui.backend import config as backend_config

    monkeypatch.setattr(backend_config.settings, "project_root", tmp_path)
    monkeypatch.setattr(backend_config.settings, "env_file", env_path)
    monkeypatch.setattr(backend_config.settings, "run_history", tmp_path / "logs" / "run_history.jsonl")

    client = TestClient(app)
    resp = client.get("/api/health/setup-status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["repo_configured"] is True
    assert data["llm_configured"] is True


def test_update_env_propagates_write_errors(tmp_path, monkeypatch):
    """Env update should surface write_env failures as HTTP 500."""
    from ui.backend import config as backend_config
    from ui.backend.routers import env as env_router

    # Ensure settings paths are valid so only write_env is mocked as failing
    monkeypatch.setattr(backend_config.settings, "project_root", tmp_path)
    monkeypatch.setattr(backend_config.settings, "env_file", tmp_path / ".env")

    def _boom(values):
        raise RuntimeError("disk full")

    monkeypatch.setattr(env_router, "write_env", _boom)

    client = TestClient(app)
    resp = client.put("/api/env", json={"values": {"PROJECT_PATH": "/tmp/test"}})
    assert resp.status_code == 500
    assert "Failed to update environment" in resp.json()["detail"]

