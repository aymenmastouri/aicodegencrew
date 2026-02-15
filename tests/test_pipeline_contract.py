"""Tests for the central pipeline contract."""

from __future__ import annotations

from pathlib import Path

from aicodegencrew.pipeline_contract import (
    PHASE_PROGRESS_COMPLETED,
    PHASE_PROGRESS_PARTIAL,
    PHASE_PROGRESS_SKIPPED,
    build_pipeline_contract,
    compute_run_outcome,
    load_pipeline_contract,
    normalize_phase_progress_status,
    normalize_phase_result_status,
)


def test_normalize_phase_result_status_maps_aliases() -> None:
    assert normalize_phase_result_status("completed") == "success"
    assert normalize_phase_result_status("dry_run") == "success"
    assert normalize_phase_result_status("partial") == "partial"
    assert normalize_phase_result_status("skip") == "skipped"
    assert normalize_phase_result_status("error") == "failed"


def test_normalize_phase_progress_status_maps_success_to_completed() -> None:
    assert normalize_phase_progress_status("success") == PHASE_PROGRESS_COMPLETED
    assert normalize_phase_progress_status("partial") == PHASE_PROGRESS_PARTIAL
    assert normalize_phase_progress_status("skipped") == PHASE_PROGRESS_SKIPPED


def test_compute_run_outcome_with_mixed_skipped_and_completed_is_partial() -> None:
    outcome = compute_run_outcome(["completed", "skipped"])
    assert outcome == "partial"


def test_load_pipeline_contract_empty_file_keeps_empty_raw_config(tmp_path: Path) -> None:
    config_path = tmp_path / "empty.yaml"
    config_path.write_text("", encoding="utf-8")

    contract = load_pipeline_contract(config_path=config_path, fallback_config={"phases": {"discover": {"enabled": True}}})
    assert contract.raw_config == {}


def test_build_pipeline_contract_resolve_explicit_phases_is_deduplicated() -> None:
    contract = build_pipeline_contract(
        {
            "phases": {
                "discover": {"enabled": True, "order": 0},
                "extract": {"enabled": True, "order": 1},
            },
            "presets": {"scan": ["discover", "extract"]},
        }
    )

    resolved = contract.resolve_requested_phases(preset=None, explicit_phases=["discover", "discover", "extract"])
    assert resolved == ["discover", "extract"]
