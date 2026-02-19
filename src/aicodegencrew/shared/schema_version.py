"""Schema versioning for phase JSON outputs.

Adding ``_schema_version`` to phase outputs enables downstream readers to detect
schema changes and log warnings — fully backward-compatible (never raises).

Existing ``knowledge/`` artifacts without ``_schema_version`` are silently accepted;
the reader simply logs nothing (``stored`` is ``None``).

Usage
-----
Writing::

    from aicodegencrew.shared.schema_version import add_schema_version
    versioned = add_schema_version(my_dict, "plan")
    json.dump(versioned, f)

Reading::

    from aicodegencrew.shared.schema_version import check_schema_version
    data = json.load(f)
    check_schema_version(data, "plan")   # logs warning if version mismatch

Bumping a version
-----------------
Increment the version string in SCHEMA_VERSIONS when the JSON schema for that
phase changes in a backward-incompatible way.  Downstream code can then
conditionally migrate old artifacts based on the stored version.
"""

from .utils.logger import logger

# Current schema versions per phase. Bump when a phase output schema changes.
SCHEMA_VERSIONS: dict[str, str] = {
    "extract":   "1.0",
    "analyze":   "1.0",
    "plan":      "1.0",
    "implement": "1.0",
    "verify":    "1.0",
}


def add_schema_version(data: dict, phase_id: str) -> dict:
    """Return a shallow copy of *data* with ``_schema_version`` injected as the first key.

    Args:
        data:     The phase output dict to version.
        phase_id: Phase identifier (e.g. ``"plan"``).  Unknown IDs default to ``"1.0"``.

    Returns:
        New dict with ``_schema_version`` prepended.  The original dict is not modified.
    """
    return {"_schema_version": SCHEMA_VERSIONS.get(phase_id, "1.0"), **data}


def check_schema_version(data: dict, phase_id: str) -> None:
    """Log a warning if the stored schema version does not match the current one.

    Never raises — fully backward-compatible with existing ``knowledge/`` artifacts
    that pre-date schema versioning (``stored`` will be ``None``).

    Args:
        data:     Phase output dict loaded from disk.
        phase_id: Phase identifier (e.g. ``"extract"``).
    """
    stored = data.get("_schema_version")
    current = SCHEMA_VERSIONS.get(phase_id)
    if stored and current and stored != current:
        logger.warning(
            "[SchemaVersion] %s: stored=%s current=%s — check migration",
            phase_id, stored, current,
        )
