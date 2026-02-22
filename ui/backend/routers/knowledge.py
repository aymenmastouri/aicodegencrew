"""Knowledge base API routes."""

from fastapi import APIRouter, HTTPException, Query

from ..schemas import KnowledgeSummary
from ..services.knowledge_reader import (
    generate_container_diagram,
    list_knowledge_files,
    read_knowledge_file,
    search_knowledge_files,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


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
