"""OIDC Authentication Middleware for Authentik integration.

Validates JWT Bearer tokens from the Authorization header using JWKS
from the OIDC discovery endpoint. Passthrough when OIDC_ENABLED=false.

Env vars:
    OIDC_ENABLED: true|false (default: false)
    OIDC_AUTHORITY: OIDC provider URL (e.g. https://auth.example.com/application/o/aicodegencrew/)
    OIDC_CLIENT_ID: Client ID for token audience validation
    OIDC_CLIENT_SECRET: Client secret (unused for JWT validation, but needed for token exchange)
    OIDC_SCOPES: Space-separated scopes (default: "openid profile email")
"""

import logging
import os
import time
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths exempt from authentication
_EXEMPT_PATHS: set[str] = {
    "/api/health",
    "/api/health/setup-status",
    "/api/auth/config",
    "/api/auth/token",
    "/metrics",
}

# JWKS cache: (keys, fetched_at)
_jwks_cache: tuple[list[dict], float] = ([], 0)
_JWKS_CACHE_TTL = 3600  # 1 hour


def _is_oidc_enabled() -> bool:
    return os.getenv("OIDC_ENABLED", "false").strip().lower() in ("true", "1", "yes")


def _get_oidc_config() -> dict[str, str]:
    return {
        "authority": os.getenv("OIDC_AUTHORITY", "").strip().rstrip("/"),
        "client_id": os.getenv("OIDC_CLIENT_ID", "").strip(),
        "scopes": os.getenv("OIDC_SCOPES", "openid profile email").strip(),
    }


def _fetch_jwks(authority: str) -> list[dict]:
    """Fetch JWKS from OIDC discovery endpoint with caching."""
    global _jwks_cache

    now = time.time()
    if _jwks_cache[0] and (now - _jwks_cache[1]) < _JWKS_CACHE_TTL:
        return _jwks_cache[0]

    try:
        import httpx

        # Discover JWKS URI
        discovery_url = f"{authority}/.well-known/openid-configuration"
        with httpx.Client(timeout=10) as client:
            disco = client.get(discovery_url).json()
            jwks_uri = disco.get("jwks_uri", f"{authority}/jwks")
            jwks_response = client.get(jwks_uri).json()

        keys = jwks_response.get("keys", [])
        _jwks_cache = (keys, now)
        return keys
    except Exception as exc:
        logger.error("[OIDC] Failed to fetch JWKS: %s", exc)
        return _jwks_cache[0]  # Return stale cache if available


def _validate_token(token: str, config: dict[str, str]) -> dict[str, Any] | None:
    """Validate JWT token and return claims. Returns None on failure."""
    try:
        from jose import jwt as jose_jwt
        from jose.exceptions import JWTError

        authority = config["authority"]
        client_id = config["client_id"]

        keys = _fetch_jwks(authority)
        if not keys:
            logger.error("[OIDC] No JWKS keys available")
            return None

        # Try each key until one works
        for key in keys:
            try:
                claims = jose_jwt.decode(
                    token,
                    key,
                    algorithms=["RS256", "ES256"],
                    audience=client_id,
                    issuer=authority,
                    options={"verify_exp": True},
                )
                return claims
            except JWTError:
                continue

        logger.warning("[OIDC] Token validation failed with all keys")
        return None
    except ImportError:
        logger.error("[OIDC] python-jose not installed — pip install 'python-jose[cryptography]'")
        return None
    except Exception as exc:
        logger.error("[OIDC] Token validation error: %s", exc)
        return None


class OIDCAuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for OIDC JWT validation.

    When OIDC_ENABLED=false, all requests pass through unchanged.
    When enabled, validates Bearer tokens and sets request.state.user.
    """

    async def dispatch(self, request: Request, call_next):
        if not _is_oidc_enabled():
            return await call_next(request)

        # Exempt paths
        path = request.url.path
        if path in _EXEMPT_PATHS or not path.startswith("/api"):
            return await call_next(request)

        # Allow userinfo endpoint (used by frontend to get current user)
        if path == "/api/auth/userinfo":
            pass  # Still validate token below

        # Extract Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        token = auth_header[7:]  # Strip "Bearer "
        config = _get_oidc_config()
        claims = _validate_token(token, config)

        if claims is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        # Set user info on request state
        request.state.user = {
            "sub": claims.get("sub", ""),
            "email": claims.get("email", ""),
            "name": claims.get("name", claims.get("preferred_username", "")),
            "groups": claims.get("groups", []),
        }

        return await call_next(request)
