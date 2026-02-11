"""Log file API routes."""

from fastapi import APIRouter, Query

from ..services.log_reader import read_log, list_log_files
from ..schemas import LogResponse

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/files")
def get_log_files() -> list[str]:
    """List available log files."""
    return list_log_files()


@router.get("", response_model=LogResponse)
def get_log(
    filename: str = Query("aicodegencrew.log"),
    tail: int = Query(200, ge=1, le=5000),
):
    """Read the last N lines of a log file."""
    return read_log(filename=filename, tail=tail)
