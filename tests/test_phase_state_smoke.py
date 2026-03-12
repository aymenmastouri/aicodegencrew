"""Smoke tests for phase_state utilities.

These tests ensure that the phase_state module works end-to-end in a fresh
environment with the real filelock/psutil dependencies installed.
"""

from pathlib import Path

from aicodegencrew.shared.utils import phase_state


def test_init_run_and_read_all_phases_tmp_dir(tmp_path: Path) -> None:
    """Basic lifecycle: init_run -> read_all_phases."""
    phase_state.configure_state_dir(tmp_path)

    phase_state.init_run("test-run-123")
    data = phase_state.read_all_phases()

    assert data["run_id"] == "test-run-123"
    assert isinstance(data["pid"], int)
    assert data["phases"] == {}


def test_set_and_read_phase_states(tmp_path: Path) -> None:
    """Set running/completed/failed phases and verify roundtrip."""
    phase_state.configure_state_dir(tmp_path)
    phase_state.init_run("test-run-456")

    phase_state.set_phase_running("triage")
    phase_state.set_phase_completed("triage", duration=1.23)
    phase_state.set_phase_failed("plan", duration=2.5, error="boom")

    data = phase_state.read_all_phases()
    phases = data["phases"]

    assert set(phases.keys()) == {"triage", "plan"}
    assert phases["triage"]["status"] in {"completed", "partial", "skipped"}
    assert phases["plan"]["status"] == "failed"
    assert isinstance(phases["plan"]["error"], str)

