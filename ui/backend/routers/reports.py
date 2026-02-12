"""Reports API routes (development plans + codegen reports + branches)."""

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from ..schemas import BranchList, ReportList
from ..services.report_reader import (
    delete_codegen_branch,
    list_codegen_branches,
    list_reports,
    read_report,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=ReportList)
def get_reports():
    """List all development plans and codegen reports."""
    return list_reports()


@router.get("/branches", response_model=BranchList)
def get_branches():
    """List all codegen/* git branches."""
    return list_codegen_branches()


@router.delete("/branches/{task_id}")
def remove_branch(
    task_id: str = PathParam(..., pattern=r"^[A-Za-z0-9_-]+$"),
):
    """Delete a codegen branch by task_id."""
    try:
        return delete_codegen_branch(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


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
