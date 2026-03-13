"""Environment configuration API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..schemas import EnvUpdate, EnvVariable
from ..services.env_manager import get_env_schema, read_env, write_env

# Whitelist of env keys that can be modified via the API
_ALLOWED_ENV_KEYS = {
    "PROJECT_PATH", "LLM_PROVIDER", "API_BASE", "OPENAI_API_KEY",
    "MODEL", "FAST_MODEL", "CODEGEN_MODEL", "VISION_MODEL",
    "EMBED_MODEL", "INDEX_MODE", "LOG_LEVEL",
    "MAX_LLM_OUTPUT_TOKENS", "LLM_CONTEXT_WINDOW",
    "TASK_INPUT_DIR", "REQUIREMENTS_DIR", "LOGS_DIR", "REFERENCE_DIR",
    "OUTPUT_DIR", "DOCS_OUTPUT_DIR", "ARC42_LANGUAGE",
    "CREWAI_TRACING_ENABLED", "CODEGEN_BUILD_VERIFY",
    "CHROMA_SERVER_HOST", "CHROMA_SERVER_PORT", "CHROMA_SERVER_SSL",
    "DASHBOARD_CORS_ORIGINS",
}

router = APIRouter(prefix="/api/env", tags=["environment"])


@router.get("", response_model=list[EnvVariable])
def get_env():
    """Get current .env values grouped by category."""
    return get_env_schema()


@router.put("")
def update_env(request: EnvUpdate):
    """Update .env values (whitelisted keys only)."""
    # Reject keys not in the whitelist
    blocked = [k for k in request.values if k not in _ALLOWED_ENV_KEYS]
    if blocked:
        raise HTTPException(
            status_code=400,
            detail=f"Keys not allowed: {', '.join(blocked)}",
        )
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
