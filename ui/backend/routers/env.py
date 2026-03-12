"""Environment configuration API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..schemas import EnvUpdate, EnvVariable
from ..services.env_manager import get_env_schema, read_env, write_env

router = APIRouter(prefix="/api/env", tags=["environment"])


@router.get("", response_model=list[EnvVariable])
def get_env():
    """Get current .env values grouped by category."""
    return get_env_schema()


@router.put("")
def update_env(request: EnvUpdate):
    """Update .env values."""
    try:
        write_env(request.values)
    except Exception as exc:
        # Surface configuration write issues as a clear API error so the UI can
        # give actionable feedback instead of failing silently.
        raise HTTPException(status_code=500, detail=f"Failed to update environment: {exc}") from exc
    return {"success": True, "message": f"Updated {len(request.values)} variables"}


@router.get("/defaults")
def env_defaults():
    """Get default values from .env.example."""
    return read_env(settings.env_example)


@router.get("/schema", response_model=list[EnvVariable])
def env_schema():
    """Get variable metadata with descriptions, groups, and defaults."""
    return get_env_schema()
