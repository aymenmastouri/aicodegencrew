"""Environment configuration API routes."""

from __future__ import annotations

from fastapi import APIRouter

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
    write_env(request.values)
    return {"success": True, "message": f"Updated {len(request.values)} variables"}


@router.get("/schema", response_model=list[EnvVariable])
def env_schema():
    """Get variable metadata with descriptions, groups, and defaults."""
    return get_env_schema()
