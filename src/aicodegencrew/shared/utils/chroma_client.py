"""ChromaDB client helpers.

Supports two modes:
- Local persistent store (PersistentClient) at a filesystem path
- Client-server mode (HttpClient) when CHROMA_SERVER_HOST is set

Keeping this logic centralized ensures all pipeline stages use the same mode,
avoiding unsafe concurrent access to the same persistent directory.
"""

from __future__ import annotations

import os
from typing import Any


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
    """Create a Chroma client (HTTP if configured, else persistent).

    Args:
        persistent_path: Required when HTTP mode is not enabled.
        settings: Optional chromadb.config.Settings.
    """
    import chromadb
    from chromadb.config import Settings

    http_cfg = get_chroma_http_config()
    if settings is None:
        settings = Settings(anonymized_telemetry=False)

    if http_cfg is not None:
        host, port, ssl = http_cfg
        return chromadb.HttpClient(host=host, port=port, ssl=ssl, settings=settings)

    if not persistent_path:
        raise ValueError("persistent_path is required when CHROMA_SERVER_HOST is not set")

    return chromadb.PersistentClient(path=persistent_path, settings=settings)
