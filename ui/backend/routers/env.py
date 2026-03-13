"""Environment configuration API routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..schemas import EnvUpdate, EnvVariable
from ..services.env_manager import get_env_schema, read_env, write_env

# Patterns in key names that indicate sensitive values
_SENSITIVE_PATTERNS = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD)", re.IGNORECASE)

# Regex matching the masked placeholder format so we can detect it on PUT
_MASKED_RE = re.compile(r"^.{0,10}\*{4,}.*$")


def _mask_value(key: str, value: str) -> str:
    """Return a masked version of *value* if *key* looks sensitive."""
    if not _SENSITIVE_PATTERNS.search(key):
        return value
    if not value or len(value) <= 4:
        return "****"
    return f"{value[:3]}****{value[-4:]}"

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
    """Get current .env values grouped by category (sensitive values masked)."""
    variables = get_env_schema()
    for var in variables:
        var.value = _mask_value(var.name, var.value)
    return variables


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

    # Drop sensitive keys whose value is still the masked placeholder —
    # the user didn't change it, so we must not overwrite the real secret.
    filtered: dict[str, str] = {}
    for key, value in request.values.items():
        if _SENSITIVE_PATTERNS.search(key) and _MASKED_RE.match(value):
            continue  # skip — still masked
        filtered[key] = value

    if not filtered:
        return {"success": True, "message": "No changes (all values were masked)"}

    try:
        write_env(filtered)
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
    """Get variable metadata with descriptions, groups, and defaults (sensitive values masked)."""
    variables = get_env_schema()
    for var in variables:
        var.value = _mask_value(var.name, var.value)
    return variables
