"""Dashboard configuration from environment."""

import os
from pathlib import Path


class Settings:
    """Dashboard settings resolved from environment or defaults."""

    def __init__(self):
        self.project_root = Path(os.getenv("AICODEGENCREW_ROOT", str(Path(__file__).resolve().parents[2])))
        self.knowledge_dir = self.project_root / "knowledge"
        self.logs_dir = self.project_root / "logs"
        self.metrics_file = self.logs_dir / "metrics.jsonl"
        self.phases_config = self.project_root / "config" / "phases_config.yaml"
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        self.run_report = self.project_root / "knowledge" / "run_report.json"
        self.run_history = self.logs_dir / "run_history.jsonl"
        self.host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
        try:
            self.port = int(os.getenv("DASHBOARD_PORT", "8001"))
        except ValueError:
            self.port = 8001
        origins_str = os.getenv("DASHBOARD_CORS_ORIGINS", "http://localhost:4200")
        self.cors_origins = [o.strip() for o in origins_str.split(",") if o.strip()]

        # OIDC Authentication (Authentik)
        self.oidc_enabled = os.getenv("OIDC_ENABLED", "false").strip().lower() in ("true", "1", "yes")
        self.oidc_authority = os.getenv("OIDC_AUTHORITY", "").strip()
        self.oidc_client_id = os.getenv("OIDC_CLIENT_ID", "").strip()
        self.oidc_client_secret = os.getenv("OIDC_CLIENT_SECRET", "").strip()
        self.oidc_scopes = os.getenv("OIDC_SCOPES", "openid profile email").strip()


settings = Settings()
