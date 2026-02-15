"""Phase Registry — single source of truth for phase metadata.

Replaces scattered hardcoded dicts in orchestrator, cli, phase_outputs,
reset_service, and reset router.  Adding a new phase = adding one entry here.

Runtime configuration (enabled, presets) stays in phases_config.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class PhaseDescriptor:
    """Immutable descriptor for one SDLC phase."""

    phase_id: str
    display_name: str
    phase_type: Literal["pipeline", "crew", "hybrid"]
    order: int
    dependencies: tuple[str, ...]
    required: bool
    primary_output: str  # relative to project root
    cleanup_targets: tuple[str, ...]  # relative to project root
    resettable: bool = True


# ── All 8 SDLC phases ───────────────────────────────────────────────────────

PHASES: dict[str, PhaseDescriptor] = {
    "discover": PhaseDescriptor(
        "discover", "Repository Indexing", "pipeline", 0,
        (), True,
        "knowledge/discover",
        ("knowledge/discover",),
        resettable=False,
    ),
    "extract": PhaseDescriptor(
        "extract", "Architecture Facts Extraction", "pipeline", 1,
        ("discover",), True,
        "knowledge/extract/architecture_facts.json",
        ("knowledge/extract",),
    ),
    "analyze": PhaseDescriptor(
        "analyze", "Architecture Analysis", "crew", 2,
        ("extract",), True,
        "knowledge/analyze/analyzed_architecture.json",
        ("knowledge/analyze",),
    ),
    "document": PhaseDescriptor(
        "document", "Architecture Synthesis", "crew", 3,
        ("analyze",), False,
        "knowledge/document/c4",
        ("knowledge/document",),
    ),
    "plan": PhaseDescriptor(
        "plan", "Development Planning", "hybrid", 4,
        ("analyze",), False,
        "knowledge/plan",
        ("knowledge/plan",),
    ),
    "implement": PhaseDescriptor(
        "implement", "Code Generation", "hybrid", 5,
        ("plan",), False,
        "knowledge/implement",
        ("knowledge/implement",),
    ),
    "verify": PhaseDescriptor(
        "verify", "Test Generation", "crew", 6,
        ("implement",), False,
        "knowledge/verify",
        ("knowledge/verify",),
    ),
    "deliver": PhaseDescriptor(
        "deliver", "Review & Deploy", "pipeline", 7,
        ("verify",), False,
        "knowledge/deliver",
        ("knowledge/deliver",),
    ),
}


# ── Discover phase artifact paths (relative to project root) ─────────────────

DISCOVER_ARTIFACTS: dict[str, str] = {
    "symbols": "knowledge/discover/symbols.jsonl",
    "evidence": "knowledge/discover/evidence.jsonl",
    "manifest": "knowledge/discover/repo_manifest.json",
}


# ── Convenience helpers ──────────────────────────────────────────────────────


def get_phase(phase_id: str) -> PhaseDescriptor:
    """Return descriptor for *phase_id*, or raise KeyError."""
    return PHASES[phase_id]


def get_all_phases() -> list[PhaseDescriptor]:
    """All phases sorted by execution order."""
    return sorted(PHASES.values(), key=lambda p: p.order)


def get_cleanup_targets(phase_id: str) -> list[str]:
    """Relative cleanup paths for a phase (empty list if unknown)."""
    desc = PHASES.get(phase_id)
    return list(desc.cleanup_targets) if desc else []


def get_resettable_phases() -> list[str]:
    """Phase IDs that may be reset (excludes discover)."""
    return [p.phase_id for p in get_all_phases() if p.resettable]


def get_dependency_graph() -> dict[str, list[str]]:
    """Return {phase_id: [dependency_ids]} for every known phase."""
    return {p.phase_id: list(p.dependencies) for p in PHASES.values()}


def outputs_exist(phase_id: str, base: Path) -> bool:
    """Check whether a phase's primary output exists.

    Replaces the hardcoded dict in ``SDLCOrchestrator._outputs_exist``.
    """
    desc = PHASES.get(phase_id)
    if not desc:
        return False

    path = base / desc.primary_output
    if path.is_dir():
        return any(path.rglob("*"))
    return path.exists()


def check_phase_output_exists(phase_id: str, project_root: Path) -> bool:
    """Check whether a phase's primary output exists and is non-empty.

    Drop-in replacement for ``phase_outputs.check_phase_output_exists``.
    """
    return outputs_exist(phase_id, project_root)
