"""Single source of truth for phase output paths, status detection, and cleanup.

Both phase_runner.py (status detection) and reset_service.py (cleanup)
import from here to guarantee consistency across all phases.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class PhaseOutputConfig(TypedDict):
    """Output configuration for a single phase."""

    # Primary output path used for completion detection.
    # For files: checks existence.  For directories: checks non-empty.
    primary_output: str

    # All paths to delete on reset (superset of primary_output).
    cleanup_targets: list[str]


# ─── ALL PHASES: output config (phases 0–7) ────────────────────────────────
PHASE_OUTPUTS: dict[str, PhaseOutputConfig] = {
    "discover": {
        "primary_output": "knowledge/discover",
        "cleanup_targets": [
            "knowledge/discover",
        ],
    },
    "extract": {
        "primary_output": "knowledge/extract/architecture_facts.json",
        "cleanup_targets": [
            "knowledge/extract",
        ],
    },
    "analyze": {
        "primary_output": "knowledge/analyze/analyzed_architecture.json",
        "cleanup_targets": [
            "knowledge/analyze",
        ],
    },
    "document": {
        "primary_output": "knowledge/document/c4",
        "cleanup_targets": [
            "knowledge/document",
        ],
    },
    "plan": {
        "primary_output": "knowledge/plan",
        "cleanup_targets": [
            "knowledge/plan",
        ],
    },
    "implement": {
        "primary_output": "knowledge/implement",
        "cleanup_targets": [
            "knowledge/implement",
        ],
    },
    "verify": {
        "primary_output": "knowledge/verify",
        "cleanup_targets": [
            "knowledge/verify",
        ],
    },
    "deliver": {
        "primary_output": "knowledge/deliver",
        "cleanup_targets": [
            "knowledge/deliver",
        ],
    },
}


def check_phase_output_exists(phase_id: str, project_root: Path) -> bool:
    """Check whether a phase's primary output exists and is non-empty.

    - Files: returns True if the file exists.
    - Directories: returns True if the directory exists AND contains at least one entry.
    """
    config = PHASE_OUTPUTS.get(phase_id)
    if not config:
        return False

    output_path = project_root / config["primary_output"]

    if output_path.is_dir():
        # Empty directory after reset ≠ completed
        return any(output_path.rglob("*"))
    else:
        return output_path.exists()


def get_cleanup_targets(phase_id: str) -> list[str]:
    """Return the list of relative cleanup paths for a phase."""
    config = PHASE_OUTPUTS.get(phase_id)
    if not config:
        return []
    return config["cleanup_targets"]
