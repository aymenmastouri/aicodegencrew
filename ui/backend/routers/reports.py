"""Reports API routes (development plans + codegen reports)."""

from fastapi import APIRouter, HTTPException, Path as PathParam

from ..services.report_reader import list_reports, read_report
from ..schemas import ReportList

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=ReportList)
def get_reports():
    """List all development plans and codegen reports."""
    return list_reports()


@router.get("/{report_type}/{task_id}")
def get_report(
    report_type: str = PathParam(..., pattern="^(plan|report)$"),
    task_id: str = PathParam(...),
):
    """Read a specific plan or codegen report."""
    try:
        return read_report(report_type, task_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
