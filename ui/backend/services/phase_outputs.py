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
    "phase0_indexing": {
        "primary_output": "knowledge/phase0_indexing",
        "cleanup_targets": [
            "knowledge/phase0_indexing",
        ],
    },
    "phase1_architecture_facts": {
        "primary_output": "knowledge/phase1_facts/architecture_facts.json",
        "cleanup_targets": [
            "knowledge/phase1_facts",
        ],
    },
    "phase2_architecture_analysis": {
        "primary_output": "knowledge/phase2_analysis/analyzed_architecture.json",
        "cleanup_targets": [
            "knowledge/phase2_analysis",
        ],
    },
    "phase3_architecture_synthesis": {
        "primary_output": "knowledge/phase3_synthesis/c4",
        "cleanup_targets": [
            "knowledge/phase3_synthesis",
        ],
    },
    "phase4_development_planning": {
        "primary_output": "knowledge/phase4_planning",
        "cleanup_targets": [
            "knowledge/phase4_planning",
        ],
    },
    "phase5_code_generation": {
        "primary_output": "knowledge/phase5_codegen",
        "cleanup_targets": [
            "knowledge/phase5_codegen",
        ],
    },
    "phase6_test_generation": {
        "primary_output": "knowledge/phase6_testing",
        "cleanup_targets": [
            "knowledge/phase6_testing",
        ],
    },
    "phase7_review_deploy": {
        "primary_output": "knowledge/phase7_deployment",
        "cleanup_targets": [
            "knowledge/phase7_deployment",
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
