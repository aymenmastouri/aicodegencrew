"""Input file management API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile

from ..services.input_manager import (
    delete_input_file,
    get_categories_metadata,
    get_category_summary,
    list_all_inputs,
    list_category_files,
    save_uploaded_file,
    CATEGORIES,
    MAX_FILE_SIZE,
)

router = APIRouter(prefix="/api/inputs", tags=["inputs"])


@router.get("")
def list_inputs():
    """List all categories with their files."""
    return list_all_inputs()


@router.get("/summary")
def inputs_summary():
    """Lightweight file counts for dashboard widgets."""
    return get_category_summary()


@router.get("/categories")
def categories_metadata():
    """Category metadata (accepted extensions, labels) for frontend rendering."""
    return get_categories_metadata()


@router.get("/{category}")
def list_category(category: str):
    """List files in a specific category."""
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")
    return list_category_files(category)


@router.post("/{category}/upload")
async def upload_file(category: str, file: UploadFile):
    """Upload a file to a category."""
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    try:
        result = save_uploaded_file(category, file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.delete("/{category}/{filename}")
def delete_file(category: str, filename: str):
    """Delete a file from a category."""
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    try:
        deleted = delete_input_file(category, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    return {"success": True, "message": f"Deleted {filename}"}
