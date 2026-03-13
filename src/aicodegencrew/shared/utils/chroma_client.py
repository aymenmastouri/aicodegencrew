"""ChromaDB client helpers.

Supports two modes:
- Local persistent store (PersistentClient) at a filesystem path
- Client-server mode (HttpClient) when CHROMA_SERVER_HOST is set

Keeping this logic centralized ensures all pipeline stages use the same mode,
avoiding unsafe concurrent access to the same persistent directory.

IMPORTANT: ChromaDB forbids multiple PersistentClient instances for the same
path with different Settings objects within the same process.  All code MUST
use ``get_or_create_chroma_client()`` (or ``create_chroma_client()`` which
delegates to it) to get a cached, shared client instance per path.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Module-level cache: normalized_path -> client instance
_client_cache: dict[str, Any] = {}


def get_chroma_http_config() -> tuple[str, int, bool] | None:
    """Return (host, port, ssl) if HTTP mode is enabled via env vars."""
    host = os.getenv("CHROMA_SERVER_HOST", "").strip()
    if not host:
        return None

    port_raw = os.getenv("CHROMA_SERVER_PORT", "8000").strip()
    try:
        port = int(port_raw)
    except ValueError:
        raise ValueError(f"Invalid CHROMA_SERVER_PORT={port_raw!r} (must be an integer)") from None

    ssl = os.getenv("CHROMA_SERVER_SSL", "").strip().lower() in ("1", "true", "yes", "on")
    return host, port, ssl


def create_chroma_client(*, persistent_path: str | None = None, settings: Any | None = None):
    """Create or retrieve a cached Chroma client.

    Uses a per-path cache so that only one PersistentClient instance exists
    for any given directory within the process.  The *settings* parameter is
    applied only when the client is first created; subsequent calls for the
    same path return the cached instance (settings argument is ignored).

    Args:
        persistent_path: Required when HTTP mode is not enabled.
        settings: Optional chromadb.config.Settings (used on first creation only).
    """
    import chromadb
    from chromadb.config import Settings

    http_cfg = get_chroma_http_config()

    # Canonical settings used everywhere — include allow_reset so that
    # both indexing (which needs reset) and querying (which doesn't) can
    # share the same client instance without a settings mismatch.
    if settings is None:
        settings = Settings(anonymized_telemetry=False, allow_reset=True)

    if http_cfg is not None:
        host, port, ssl = http_cfg
        cache_key = f"http://{host}:{port}"
        if cache_key not in _client_cache:
            _client_cache[cache_key] = chromadb.HttpClient(
                host=host, port=port, ssl=ssl, settings=settings,
            )
        return _client_cache[cache_key]

    if not persistent_path:
        raise ValueError("persistent_path is required when CHROMA_SERVER_HOST is not set")

    # Normalize path so "knowledge/discover" and "knowledge/discover/" hit same cache entry
    cache_key = str(Path(persistent_path).resolve())
    if cache_key not in _client_cache:
        _client_cache[cache_key] = chromadb.PersistentClient(
            path=persistent_path, settings=settings,
        )
    return _client_cache[cache_key]
