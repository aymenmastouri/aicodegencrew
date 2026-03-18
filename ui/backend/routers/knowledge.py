"""Knowledge base API routes."""

import io
import zipfile

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..schemas import KnowledgeSummary, VersionedRun, VersionedRunList, VersionStatus
from ..services.knowledge_reader import (
    generate_container_diagram,
    list_knowledge_files,
    read_knowledge_file,
    search_knowledge_files,
)
from ..services.mlflow_reader import mlflow_reader

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


# ── Existing endpoints (unchanged) ──────────────────────────────────


@router.get("", response_model=KnowledgeSummary)
def list_files():
    """List all knowledge base files."""
    return list_knowledge_files()


@router.get("/search")
def search_files(q: str = Query(..., min_length=2, max_length=100)):
    """Full-text search across knowledge files."""
    return search_knowledge_files(q)


@router.get("/architecture/diagram")
def get_architecture_diagram():
    """Generate Mermaid diagram from containers.json."""
    return {"mermaid": generate_container_diagram()}


@router.get("/file")
def get_file(path: str = Query(..., description="Relative path within knowledge/")):
    """Read a knowledge file by relative path."""
    try:
        return read_knowledge_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Version endpoints (MLflow/MinIO) ────────────────────────────────


@router.get("/versions/status", response_model=VersionStatus)
def get_version_status():
    """Check if MLflow versioning is configured. Returns instantly."""
    # Only check if configured, not if reachable (that would be slow)
    return VersionStatus(available=mlflow_reader._enabled, total_runs=0)


@router.get("/versions", response_model=VersionedRunList)
def list_versions(limit: int = Query(50, ge=1, le=200)):
    """List all MLflow runs with artifact metadata."""
    available = mlflow_reader.is_available()
    if not available:
        return VersionedRunList(available=False, runs=[])

    raw_runs = mlflow_reader.list_runs(limit=limit)
    runs = [VersionedRun(**r) for r in raw_runs]
    return VersionedRunList(available=True, runs=runs)


@router.get("/versions/artifact-counts")
def get_artifact_counts(
    run_ids: str = Query(..., description="Comma-separated list of MLflow run IDs"),
):
    """Return artifact file counts for the given runs."""
    if not mlflow_reader.is_available():
        raise HTTPException(status_code=503, detail="MLflow not available")

    ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
    if not ids:
        return {}

    return mlflow_reader.get_artifact_counts(ids)


@router.get("/versions/{run_id}/files")
def list_version_files(run_id: str):
    """List all artifacts for a specific MLflow run."""
    if not mlflow_reader.is_available():
        raise HTTPException(status_code=503, detail="MLflow not available")

    artifacts = mlflow_reader.get_run_artifacts(run_id)
    return {"run_id": run_id, "files": artifacts}


@router.get("/versions/{run_id}/file")
def get_version_file(
    run_id: str,
    path: str = Query(..., description="Artifact path within the run"),
):
    """Download a single artifact from an MLflow run."""
    if not mlflow_reader.is_available():
        raise HTTPException(status_code=503, detail="MLflow not available")

    content = mlflow_reader.download_artifact(run_id, path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {path}")

    # Return JSON-parsed content for .json files, raw string otherwise
    if path.endswith(".json"):
        import json

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content

    return content


@router.get("/versions/{run_id}/download-all")
def download_all_artifacts(run_id: str):
    """Download all artifacts for an MLflow run as a ZIP file."""
    if not mlflow_reader.is_available():
        raise HTTPException(status_code=503, detail="MLflow not available")

    artifacts = mlflow_reader.get_run_artifacts(run_id)
    if not artifacts:
        raise HTTPException(status_code=404, detail="No artifacts found for this run")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for art in artifacts:
            content = mlflow_reader.download_artifact(run_id, art["path"])
            if content is not None:
                zf.writestr(art["path"], content)
    buf.seek(0)

    filename = f"run-{run_id[:8]}-artifacts.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
