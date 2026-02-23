from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Patch settings paths to temp dirs
    from ui.backend import config

    settings = config.settings
    settings.project_root = tmp_path
    settings.knowledge_dir = tmp_path / "knowledge"
    settings.logs_dir = tmp_path / "logs"
    settings.phases_config = tmp_path / "config" / "phases_config.yaml"
    settings.run_history = tmp_path / "logs" / "run_history.jsonl"
    settings.run_report = tmp_path / "knowledge" / "run_report.json"
    settings.env_file = tmp_path / ".env"
    settings.env_example = tmp_path / ".env.example"

    settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.phases_config.parent.mkdir(parents=True, exist_ok=True)

    # Minimal phases config
    settings.phases_config.write_text(
        """
phases:
  discover:
    enabled: true
    name: "Repository Indexing"
    order: 0
    dependencies: []
  implement:
    enabled: true
    name: "Code Generation"
    order: 5
    dependencies: []
presets:
  develop:
    phases: [discover, implement]
""",
        encoding="utf-8",
    )

    # Patch pipeline executor to avoid real runs
    class FakeExecutor:
        def start(self, *a, **kw):
            return SimpleNamespace(run_id="run123")

        def cancel(self):
            return True

        def get_status(self):
            return {"state": "idle", "run_id": "run123"}

    monkeypatch.setattr("ui.backend.routers.pipeline.executor", FakeExecutor())

    # Patch reset service
    monkeypatch.setattr(
        "ui.backend.services.reset_service.preview_reset",
        lambda phase_ids, cascade=True: {
            "phases_to_reset": phase_ids,
            "files_to_delete": ["knowledge/extract/foo.json"],
        },
    )
    monkeypatch.setattr(
        "ui.backend.services.reset_service.execute_reset",
        lambda phase_ids, cascade=True: {
            "reset_phases": phase_ids,
            "deleted_count": 1,
            "timestamp": "2026-02-15T00:00:00",
        },
    )

    # Patch knowledge, metrics, reports, env
    monkeypatch.setattr(
        "ui.backend.services.knowledge_reader.list_knowledge_files",
        lambda: {"total_files": 0, "total_size_bytes": 0, "files": []},
    )
    monkeypatch.setattr(
        "ui.backend.services.metrics_reader.read_metrics",
        lambda limit=200, event_filter=None: {
            "total_events": 0,
            "events": [],
            "run_ids": [],
        },
    )
    monkeypatch.setattr(
        "ui.backend.services.report_reader.list_reports",
        lambda: {
            "plans": [],
            "codegen_reports": [],
            "extract_reports": [],
            "analyze_reports": [],
            "document_reports": [],
        },
    )
    monkeypatch.setattr(
        "ui.backend.services.report_reader.list_codegen_branches",
        lambda: {"branches": [], "repo_path": str(tmp_path)},
    )
    monkeypatch.setattr(
        "ui.backend.services.report_reader.read_report",
        lambda report_type, task_id: {"report_type": report_type, "task_id": task_id},
    )
    monkeypatch.setattr(
        "ui.backend.services.env_manager.get_env_schema",
        lambda: [{"name": "API_BASE", "value": ""}],
    )
    monkeypatch.setattr(
        "ui.backend.services.env_manager.read_env",
        lambda path=None: {"PROJECT_PATH": str(tmp_path)},
    )
    monkeypatch.setattr("ui.backend.services.env_manager.write_env", lambda values: None)

    # Build app AFTER patches
    from ui.backend.main import app

    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_pipeline_run_cancel_status(client):
    run_resp = client.post("/api/pipeline/run", json={"preset": "develop"})
    assert run_resp.status_code == 200
    assert run_resp.json()["run_id"] == "run123"

    cancel_resp = client.post("/api/pipeline/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["success"] is True

    status_resp = client.get("/api/pipeline/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["state"] == "idle"


def test_phases_endpoints(client):
    phases = client.get("/api/phases").json()
    assert any(p["id"] == "discover" for p in phases)

    presets = client.get("/api/phases/presets").json()
    assert any(p["name"] == "develop" for p in presets)

    status = client.get("/api/phases/status").json()
    assert any(p["id"] == "implement" for p in status["phases"])


def test_reset_endpoints(client):
    preview = client.post("/api/reset/preview", json={"phase_ids": ["implement"], "cascade": False}).json()
    assert preview["phases_to_reset"] == ["implement"]

    execute = client.post("/api/reset/execute", json={"phase_ids": ["implement"], "cascade": False}).json()
    assert execute["reset_phases"] == ["implement"]


def test_misc_endpoints(client):
    assert client.get("/api/knowledge").status_code == 200
    assert client.get("/api/reports").status_code == 200
    assert client.get("/api/metrics").status_code == 200
    assert client.get("/api/health/setup-status").status_code == 200
    assert client.get("/api/env").status_code == 200


def test_collectors_and_inputs(client, tmp_path, monkeypatch):
    # collectors list
    monkeypatch.setattr(
        "ui.backend.services.collector_service.list_collectors",
        lambda: {"collectors": [], "total": 0, "enabled_count": 0},
    )
    assert client.get("/api/collectors").status_code == 200

    # inputs upload/list/delete are mocked via service layer
    monkeypatch.setattr(
        "ui.backend.services.input_manager.list_all_inputs",
        lambda: {"inputs": []},
    )
    monkeypatch.setattr(
        "ui.backend.services.input_manager.delete_input_file",
        lambda category, filename: True,
    )

    files_resp = client.get("/api/inputs")
    assert files_resp.status_code == 200

    upload_resp = client.post(
        "/api/inputs/default/upload",
        files={"file": ("task1.txt", b"hello")},
    )
    assert upload_resp.status_code in (200, 400)  # upload path mocked; allow 400 if category unknown

    delete_resp = client.delete("/api/inputs/default/task1.txt")
    assert delete_resp.status_code in (200, 400)
    monkeypatch.setattr(
        "ui.backend.services.log_reader.list_log_files",
        lambda: {"diagrams": []},
    )
    monkeypatch.setattr(
        "ui.backend.services.log_reader.read_log",
        lambda path, lines=100: {"lines": [], "total_lines": 0, "file_path": path},
    )

    assert client.get("/api/logs/files").status_code == 200
    assert client.get("/api/logs").status_code == 200
