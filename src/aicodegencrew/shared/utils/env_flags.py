"""Environment variable helpers for feature flags."""

import os


def get_bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean from an environment variable.

    Truthy values (case-insensitive): ``1``, ``true``, ``yes``, ``on``.
    Everything else (including unset) returns *default*.
    """
    val = os.getenv(name, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on")
