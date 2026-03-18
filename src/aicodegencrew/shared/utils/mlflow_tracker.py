"""MLflow experiment tracking for SDLC pipeline runs.

All methods are no-op when MLFLOW_TRACKING_URI is not set.
Artifacts are uploaded via MLflow's artifact proxy (--serve-artifacts)
so no direct S3/MinIO credentials are required on the client.
"""

import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MLflowTracker:
    """Tracks pipeline runs as MLflow experiments.

    Usage:
        tracker = MLflowTracker()
        tracker.start_run(run_id="abc123")
        tracker.log_phase_metrics("analyze", duration=12.3, tokens=1500, status="success")
        tracker.log_artifact("knowledge/extract/architecture_facts.json")
        tracker.end_run("success")
    """

    def __init__(self):
        self._enabled = bool(os.getenv("MLFLOW_TRACKING_URI", "").strip())
        self._run = None
        self._mlflow = None
        self._artifact_repo = None

        if self._enabled:
            try:
                import mlflow

                # Disable SSL verification for self-signed certificates
                os.environ.setdefault("MLFLOW_TRACKING_INSECURE_TLS", "true")
                os.environ.setdefault("MLFLOW_S3_IGNORE_TLS", "true")

                self._mlflow = mlflow
                self._tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
                mlflow.set_tracking_uri(self._tracking_uri)
                experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "aicodegencrew")
                mlflow.set_experiment(experiment_name)
                logger.info("[MLflow] Configured (experiment=%s)", experiment_name)
            except ImportError:
                logger.warning("[MLflow] mlflow package not installed — tracking disabled")
                self._enabled = False
            except Exception as exc:
                logger.warning("[MLflow] Failed to configure: %s", exc)
                self._enabled = False

    def _get_proxy_repo(self):
        """Get or create an artifact repository using MLflow's proxy.

        Uses mlflow-artifacts:// scheme so the MLflow server proxies
        S3/MinIO access — no AWS credentials needed on the client.
        """
        if self._artifact_repo is not None:
            return self._artifact_repo
        if not self._run:
            return None
        try:
            from mlflow.store.artifact.mlflow_artifacts_repo import MlflowArtifactsRepository

            parsed = urlparse(self._tracking_uri)
            host = parsed.hostname
            port = f":{parsed.port}" if parsed.port else ""
            scheme = "https" if parsed.scheme == "https" else "http"
            run_id = self._run.info.run_id
            uri = f"mlflow-artifacts://{host}{port}/{run_id}/artifacts"
            self._artifact_repo = MlflowArtifactsRepository(uri)
            return self._artifact_repo
        except Exception as exc:
            logger.debug("[MLflow] Failed to create proxy artifact repo: %s", exc)
            return None

    def start_run(self, run_id: str | None = None) -> None:
        """Start a new MLflow run."""
        if not self._enabled:
            return
        try:
            self._artifact_repo = None  # Reset for new run
            self._run = self._mlflow.start_run(run_name=run_id)
            if run_id:
                self._mlflow.log_param("pipeline_run_id", run_id)
            logger.info("[MLflow] Run started")
        except Exception as exc:
            logger.warning("[MLflow] start_run failed: %s", exc)

    def log_phase_metrics(
        self,
        phase_id: str,
        duration: float,
        tokens: int = 0,
        status: str = "success",
    ) -> None:
        """Log metrics for a completed phase."""
        if not self._enabled:
            return
        try:
            self._mlflow.log_metrics(
                {
                    f"{phase_id}_duration_seconds": round(duration, 2),
                    f"{phase_id}_tokens": tokens,
                },
            )
            self._mlflow.log_param(f"{phase_id}_status", status)
        except Exception as exc:
            logger.debug("[MLflow] log_phase_metrics failed: %s", exc)

    def log_metrics(self, metrics: dict[str, float | int]) -> None:
        """Log arbitrary metrics to the current MLflow run."""
        if not self._enabled:
            return
        try:
            self._mlflow.log_metrics(metrics)
        except Exception as exc:
            logger.debug("[MLflow] log_metrics failed: %s", exc)

    def log_artifact(self, path: str) -> None:
        """Log a file as an MLflow artifact via proxy."""
        if not self._enabled:
            return
        try:
            from pathlib import Path

            if not Path(path).exists():
                return
            repo = self._get_proxy_repo()
            if repo:
                repo.log_artifact(path)
            else:
                self._mlflow.log_artifact(path)
        except Exception as exc:
            logger.debug("[MLflow] log_artifact failed: %s", exc)

    def log_artifact_dir(self, local_dir: str, artifact_path: str | None = None) -> None:
        """Log an entire directory as MLflow artifacts (stored in MinIO via proxy).

        Args:
            local_dir: Local directory to upload.
            artifact_path: Optional subdirectory in the artifact store
                           (e.g., "documents/arc42").
        """
        if not self._enabled:
            return
        try:
            from pathlib import Path

            dir_path = Path(local_dir)
            if dir_path.is_dir() and any(dir_path.iterdir()):
                repo = self._get_proxy_repo()
                if repo:
                    repo.log_artifacts(str(dir_path), artifact_path=artifact_path)
                else:
                    self._mlflow.log_artifacts(str(dir_path), artifact_path=artifact_path)
                file_count = sum(1 for _ in dir_path.rglob("*") if _.is_file())
                logger.info("[MLflow] Logged %d files from %s → %s", file_count, local_dir, artifact_path or "/")
        except Exception as exc:
            logger.warning("[MLflow] log_artifact_dir failed for %s: %s", local_dir, exc)

    def end_run(self, outcome: str = "success") -> None:
        """End the current MLflow run."""
        if not self._enabled or self._run is None:
            return
        try:
            status = "FINISHED" if outcome in ("success", "partial") else "FAILED"
            self._mlflow.log_param("pipeline_outcome", outcome)
            self._mlflow.end_run(status=status)
            logger.info("[MLflow] Run ended (outcome=%s)", outcome)
        except Exception as exc:
            logger.debug("[MLflow] end_run failed: %s", exc)
        finally:
            self._run = None
            self._artifact_repo = None
