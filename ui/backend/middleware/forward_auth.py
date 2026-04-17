"""Authentik ForwardAuth Header Middleware.

Defense-in-depth layer for Kubernetes deployments behind a Traefik
ForwardAuth middleware pointing at an Authentik proxy outpost.

Traefik sets the following request headers after a successful session
validation by the outpost:

    X-Authentik-Username
    X-Authentik-Email
    X-Authentik-Groups
    X-Authentik-Name
    X-Authentik-Uid
    X-Authentik-Jwt

If none of them is present the request bypassed the edge proxy (e.g.
direct pod-to-pod call inside the cluster) and is rejected with 401.

Controlled by env var:
    FORWARD_AUTH_ENABLED=true|false (default: false)

Kubelet liveness/readiness probes hit the pod IP directly (not through
Traefik), so their paths are exempted. /metrics is exempted for
Prometheus scraping.
"""

from __future__ import annotations

import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Paths allowed without Authentik headers (only reachable from inside
# the cluster — external traffic is still blocked by Traefik ForwardAuth)
_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/api/health",
        "/api/health/setup-status",
        "/metrics",
    }
)

_USERNAME_HEADER = "x-authentik-username"


def _is_enabled() -> bool:
    return os.getenv("FORWARD_AUTH_ENABLED", "false").strip().lower() in (
        "true",
        "1",
        "yes",
    )


class ForwardAuthMiddleware(BaseHTTPMiddleware):
    """Require X-Authentik-Username on every non-exempt request."""

    async def dispatch(self, request: Request, call_next):
        if not _is_enabled():
            return await call_next(request)

        path = request.url.path
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        # OPTIONS requests (CORS preflight) must pass — they are stripped
        # of headers by the browser and validated by CORS middleware.
        if request.method == "OPTIONS":
            return await call_next(request)

        username = request.headers.get(_USERNAME_HEADER)
        if not username:
            logger.warning(
                "[ForwardAuth] Blocked unauthenticated request path=%s "
                "method=%s client=%s",
                path,
                request.method,
                request.client.host if request.client else "?",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        "Authentication required. This service is only "
                        "accessible via Authentik SSO."
                    )
                },
            )

        # Populate request.state.user for downstream handlers
        request.state.user = {
            "sub": request.headers.get("x-authentik-uid", ""),
            "username": username,
            "email": request.headers.get("x-authentik-email", ""),
            "name": request.headers.get("x-authentik-name", ""),
            "groups": [
                g
                for g in request.headers.get("x-authentik-groups", "").split("|")
                if g
            ],
        }

        return await call_next(request)
