"""Tests for map-reduce container cache freshness and validation."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from aicodegencrew.crews.architecture_analysis.mapreduce_crew import ContainerAnalyzer, MapReduceAnalysisCrew


def _valid_payload(container: str) -> dict:
    return {
        "container": container,
        "component_count": 1,
        "relation_count": 0,
        "interface_count": 0,
        "analysis": {
            "primary_pattern": "Layered",
            "layers": ["Controller", "Service"],
            "stereotype_distribution": {"controller": 1},
            "total_components": 1,
            "total_relations": 0,
            "total_interfaces": 0,
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _build_crew(tmp_path: Path) -> tuple[MapReduceAnalysisCrew, Path, Path]:
    facts_path = tmp_path / "knowledge" / "extract" / "architecture_facts.json"
    _write_json(
        facts_path,
        {
            "system": {"name": "TestSystem"},
            "containers": [{"name": "backend"}],
            "components": [],
            "relations": [],
            "interfaces": [],
        },
    )
    output_dir = tmp_path / "knowledge" / "analyze"
    crew = MapReduceAnalysisCrew(
        facts_path=str(facts_path),
        output_dir=str(output_dir),
        parallel=False,
    )
    cache_file = crew.container_dir / "container_backend.json"
    return crew, facts_path, cache_file


def test_load_cached_container_uses_fresh_valid_cache(tmp_path: Path):
    crew, facts_path, cache_file = _build_crew(tmp_path)
    _write_json(cache_file, _valid_payload("backend"))

    now = time.time()
    os.utime(facts_path, (now - 60, now - 60))
    os.utime(cache_file, (now, now))

    cached = crew._load_cached_container("backend")
    assert cached is not None
    assert cached["container"] == "backend"


def test_load_cached_container_rejects_stale_cache(tmp_path: Path):
    crew, facts_path, cache_file = _build_crew(tmp_path)
    _write_json(cache_file, _valid_payload("backend"))

    now = time.time()
    os.utime(cache_file, (now - 60, now - 60))
    os.utime(facts_path, (now, now))

    assert crew._load_cached_container("backend") is None


def test_load_cached_container_rejects_invalid_schema(tmp_path: Path):
    crew, facts_path, cache_file = _build_crew(tmp_path)
    _write_json(cache_file, {"container": "backend", "component_count": 1})

    now = time.time()
    os.utime(facts_path, (now - 60, now - 60))
    os.utime(cache_file, (now, now))

    assert crew._load_cached_container("backend") is None


def test_map_phase_skips_analyzer_when_cache_valid(tmp_path: Path, monkeypatch):
    crew, facts_path, cache_file = _build_crew(tmp_path)
    _write_json(cache_file, _valid_payload("backend"))

    now = time.time()
    os.utime(facts_path, (now - 60, now - 60))
    os.utime(cache_file, (now, now))

    def _boom(self):
        raise AssertionError("Analyzer should not run when cache is valid.")

    monkeypatch.setattr(ContainerAnalyzer, "run", _boom)
    results = crew._map_phase(["backend"])

    assert len(results) == 1
    assert results[0]["container"] == "backend"


def test_map_phase_reanalyzes_when_cache_stale(tmp_path: Path, monkeypatch):
    crew, facts_path, cache_file = _build_crew(tmp_path)
    _write_json(cache_file, _valid_payload("backend"))

    now = time.time()
    os.utime(cache_file, (now - 60, now - 60))
    os.utime(facts_path, (now, now))

    def _fake_run(self):
        return {
            "container": "backend",
            "component_count": 2,
            "relation_count": 1,
            "interface_count": 0,
            "analysis": {
                "primary_pattern": "Layered",
                "layers": ["Controller", "Service"],
                "stereotype_distribution": {"service": 2},
            },
        }

    monkeypatch.setattr(ContainerAnalyzer, "run", _fake_run)
    results = crew._map_phase(["backend"])

    assert len(results) == 1
    assert results[0]["component_count"] == 2
