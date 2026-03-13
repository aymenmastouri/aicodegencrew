"""Diagram API routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..schemas import DiagramInfo, DiagramList

router = APIRouter(prefix="/api/diagrams", tags=["diagrams"])


@router.get("", response_model=DiagramList)
def list_diagrams():
    """List all diagram files (DrawIO + Mermaid)."""
    knowledge_dir = settings.knowledge_dir
    diagrams: list[DiagramInfo] = []

    if not knowledge_dir.exists():
        return DiagramList(diagrams=[])

    for path in sorted(knowledge_dir.rglob("*")):
        if path.is_file() and path.suffix in (".drawio", ".mmd"):
            diagrams.append(
                DiagramInfo(
                    name=path.stem,
                    path=str(path.relative_to(knowledge_dir)),
                    type="drawio" if path.suffix == ".drawio" else "mermaid",
                    size_bytes=path.stat().st_size,
                )
            )

    return DiagramList(diagrams=diagrams)


_ALLOWED_DIAGRAM_EXTENSIONS = {".drawio", ".mmd"}


@router.get("/file/{path:path}")
def get_diagram_file(path: str):
    """Download a diagram file."""
    file_path = settings.knowledge_dir / path

    # Security: prevent path traversal and symlink attacks
    try:
        file_path.resolve(strict=False).relative_to(settings.knowledge_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    if file_path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlinks are not allowed")

    if file_path.suffix.lower() not in _ALLOWED_DIAGRAM_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .drawio and .mmd files are allowed")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Diagram not found")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
