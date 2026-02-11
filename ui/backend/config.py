"""Dashboard configuration from environment."""

import os
from pathlib import Path


class Settings:
    """Dashboard settings resolved from environment or defaults."""

    def __init__(self):
        self.project_root = Path(
            os.getenv("AICODEGENCREW_ROOT", str(Path(__file__).resolve().parents[2]))
        )
        self.knowledge_dir = self.project_root / "knowledge"
        self.logs_dir = self.project_root / "logs"
        self.metrics_file = self.logs_dir / "metrics.jsonl"
        self.phases_config = self.project_root / "config" / "phases_config.yaml"
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        self.run_report = self.project_root / "knowledge" / "run_report.json"
        self.host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
        self.port = int(os.getenv("DASHBOARD_PORT", "8001"))
        self.cors_origins = os.getenv(
            "DASHBOARD_CORS_ORIGINS", "http://localhost:4200"
        ).split(",")


settings = Settings()
