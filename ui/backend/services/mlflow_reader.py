"""MLflow artifact reader for the Knowledge Explorer.

Reads runs and artifacts from MLflow (MinIO backend) to support
document versioning in the Knowledge Explorer UI.

Uses MLflow's artifact proxy (mlflow-artifacts:// scheme) so no
direct S3/MinIO credentials are required on the client.

All methods are no-op when MLFLOW_TRACKING_URI is not set.
"""

import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MLflowReader:
    """Reads pipeline runs and their artifacts from MLflow/MinIO.

    Pattern follows mlflow_tracker.py: env-check in constructor,
    all methods return safe defaults when disabled.
    """

    def __init__(self) -> None:
        self._enabled = bool(os.getenv("MLFLOW_TRACKING_URI", "").strip())
        self._client = None
        self._tracking_uri = ""

        self._artifact_count_cache: dict[str, int] = {}

        if self._enabled:
            try:
                # Disable SSL verification for self-signed certificates
                os.environ.setdefault("MLFLOW_TRACKING_INSECURE_TLS", "true")
                os.environ.setdefault("MLFLOW_S3_IGNORE_TLS", "true")

                from mlflow import MlflowClient

                self._tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "")
                self._client = MlflowClient(tracking_uri=self._tracking_uri)
                self._experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "aicodegencrew")
                logger.info("[MLflowReader] Configured (experiment=%s)", self._experiment_name)
            except ImportError:
                logger.warning("[MLflowReader] mlflow package not installed — reader disabled")
                self._enabled = False
            except Exception as exc:
                logger.warning("[MLflowReader] Failed to configure: %s", exc)
                self._enabled = False

    def _get_proxy_repo(self, mlflow_run_id: str):
        """Create a proxy-based artifact repository for a given run.

        Uses mlflow-artifacts:// scheme so the MLflow server proxies
        S3/MinIO access — no AWS credentials needed on the client.
        """
        try:
            from mlflow.store.artifact.mlflow_artifacts_repo import MlflowArtifactsRepository

            parsed = urlparse(self._tracking_uri)
            host = parsed.hostname
            port = f":{parsed.port}" if parsed.port else ""
            uri = f"mlflow-artifacts://{host}{port}/{mlflow_run_id}/artifacts"
            return MlflowArtifactsRepository(uri)
        except Exception as exc:
            logger.debug("[MLflowReader] Failed to create proxy repo: %s", exc)
            return None

    def is_available(self) -> bool:
        """Check if MLflow is configured and reachable."""
        if not self._enabled:
            return False
        # Use cached result (refreshed every 60 seconds)
        import time

        now = time.monotonic()
        if hasattr(self, "_available_cache") and now - self._available_cache_time < 60:
            return self._available_cache
        try:
            experiment = self._client.get_experiment_by_name(self._experiment_name)
            self._available_cache = experiment is not None
            self._available_cache_time = now
            return self._available_cache
        except Exception as exc:
            logger.debug("[MLflowReader] availability check failed: %s", exc)
            self._available_cache = False
            self._available_cache_time = now
            return False

    def list_runs(self, limit: int = 50) -> list[dict]:
        """List recent MLflow runs.

        Returns list of dicts with keys:
            mlflow_run_id, pipeline_run_id, started_at, status, outcome, has_documents

        Note: has_documents is always False here for performance.
        The actual check happens when the user selects a run (get_run_artifacts).
        """
        if not self._enabled:
            return []
        try:
            experiment = self._client.get_experiment_by_name(self._experiment_name)
            if not experiment:
                return []

            from mlflow.entities import ViewType

            runs = self._client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=limit,
                run_view_type=ViewType.ACTIVE_ONLY,
            )

            result = []
            for run in runs:
                params = run.data.params
                info = run.info

                started_at = None
                if info.start_time:
                    from datetime import datetime, timezone

                    started_at = datetime.fromtimestamp(
                        info.start_time / 1000, tz=timezone.utc
                    ).isoformat()

                result.append(
                    {
                        "mlflow_run_id": info.run_id,
                        "pipeline_run_id": params.get("pipeline_run_id"),
                        "started_at": started_at,
                        "status": info.status,  # FINISHED | FAILED | RUNNING
                        "outcome": params.get("pipeline_outcome"),
                        "has_documents": False,
                    }
                )

            return result
        except Exception as exc:
            logger.warning("[MLflowReader] list_runs failed: %s", exc)
            return []

    def get_run_artifacts(self, mlflow_run_id: str, path: str = "") -> list[dict]:
        """List artifacts for a specific run via proxy.

        Returns list of dicts with keys:
            path, file_size, is_dir
        """
        if not self._enabled:
            return []
        try:
            repo = self._get_proxy_repo(mlflow_run_id)
            if not repo:
                return []
            artifacts = repo.list_artifacts(path or None)
            result = []
            for art in artifacts:
                if art.is_dir:
                    children = self.get_run_artifacts(mlflow_run_id, art.path)
                    result.extend(children)
                else:
                    result.append(
                        {
                            "path": art.path,
                            "file_size": art.file_size or 0,
                            "is_dir": False,
                        }
                    )
            return result
        except Exception as exc:
            logger.warning("[MLflowReader] get_run_artifacts failed: %s", exc)
            return []

    def download_artifact(self, mlflow_run_id: str, artifact_path: str) -> str | None:
        """Download a single artifact via proxy and return its content as string.

        Returns None if the artifact cannot be downloaded.
        """
        if not self._enabled:
            return None
        try:
            repo = self._get_proxy_repo(mlflow_run_id)
            if not repo:
                return None
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_path = repo.download_artifacts(artifact_path, dst_path=tmp_dir)
                local_file = Path(local_path)
                if local_file.is_file():
                    return local_file.read_text(encoding="utf-8", errors="replace")
                return None
        except Exception as exc:
            logger.warning(
                "[MLflowReader] download_artifact failed for %s/%s: %s",
                mlflow_run_id,
                artifact_path,
                exc,
            )
            return None

    def get_artifact_counts(self, run_ids: list[str]) -> dict[str, int]:
        """Return artifact count per run, using a cache to avoid repeated lookups.

        Args:
            run_ids: List of MLflow run IDs to count artifacts for.

        Returns:
            Dict mapping run_id to the number of artifacts (files) in that run.
        """
        result: dict[str, int] = {}
        uncached = [rid for rid in run_ids if rid not in self._artifact_count_cache]

        for rid in uncached:
            artifacts = self.get_run_artifacts(rid)
            self._artifact_count_cache[rid] = len(artifacts)

        for rid in run_ids:
            result[rid] = self._artifact_count_cache.get(rid, 0)

        return result

    def find_run_by_pipeline_id(self, pipeline_run_id: str) -> str | None:
        """Find an MLflow run ID by pipeline_run_id parameter.

        Returns the mlflow_run_id or None if not found.
        """
        if not self._enabled:
            return None
        try:
            experiment = self._client.get_experiment_by_name(self._experiment_name)
            if not experiment:
                return None

            runs = self._client.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string=f"params.pipeline_run_id = '{pipeline_run_id}'",
                max_results=1,
            )
            if runs:
                return runs[0].info.run_id
            return None
        except Exception as exc:
            logger.debug("[MLflowReader] find_run_by_pipeline_id failed: %s", exc)
            return None


# Module-level singleton for use in routers
mlflow_reader = MLflowReader()
