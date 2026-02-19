"""Unit tests for Spring Boot collectors.

Tests:
- SpringRestCollector  — @RestController, @GetMapping/@PostMapping, HTTP methods, evidence
- SpringServiceCollector — @Service, stereotype
- SpringRepositoryCollector — @Repository / extends JpaRepository, stereotype

All tests are purely deterministic (regex/AST) — no LLM calls, no network access.
"""

from pathlib import Path

import pytest

from aicodegencrew.pipelines.architecture_facts.collectors.spring.repository_collector import (
    SpringRepositoryCollector,
)
from aicodegencrew.pipelines.architecture_facts.collectors.spring.rest_collector import (
    SpringRestCollector,
)
from aicodegencrew.pipelines.architecture_facts.collectors.spring.service_collector import (
    SpringServiceCollector,
)


# =============================================================================
# SpringRestCollector
# =============================================================================


class TestSpringRestCollector:
    def test_finds_controller(self, spring_repo: Path) -> None:
        output = SpringRestCollector(repo_path=spring_repo).collect()
        assert output.fact_count >= 1
        assert any("FooController" in f.name for f in output.facts)

    def test_finds_endpoints(self, spring_repo: Path) -> None:
        """Both @GetMapping and @PostMapping must produce RawInterface facts."""
        output = SpringRestCollector(repo_path=spring_repo).collect()
        # RawInterface has a `path` attribute; RawComponent does not
        interfaces = [f for f in output.facts if hasattr(f, "path") and f.path is not None]
        assert len(interfaces) >= 2, f"Expected ≥2 endpoints, got {len(interfaces)}: {interfaces}"

    def test_http_methods(self, spring_repo: Path) -> None:
        output = SpringRestCollector(repo_path=spring_repo).collect()
        methods = {f.method for f in output.facts if hasattr(f, "method") and f.method}
        assert "GET" in methods, f"GET not in detected methods: {methods}"
        assert "POST" in methods, f"POST not in detected methods: {methods}"

    def test_evidence_line_numbers_positive(self, spring_repo: Path) -> None:
        """Every fact must carry evidence with a positive line_start."""
        output = SpringRestCollector(repo_path=spring_repo).collect()
        for fact in output.facts:
            for ev in fact.evidence:
                assert ev.line_start >= 1, (
                    f"line_start must be ≥1, got {ev.line_start} for {fact.name}"
                )

    def test_empty_repo_returns_zero(self, empty_repo: Path) -> None:
        output = SpringRestCollector(repo_path=empty_repo).collect()
        assert output.fact_count == 0


# =============================================================================
# SpringServiceCollector
# =============================================================================


class TestSpringServiceCollector:
    def test_finds_service(self, spring_repo: Path) -> None:
        output = SpringServiceCollector(repo_path=spring_repo).collect()
        assert output.fact_count >= 1
        assert any("FooService" in f.name for f in output.facts)

    def test_stereotype_is_service(self, spring_repo: Path) -> None:
        output = SpringServiceCollector(repo_path=spring_repo).collect()
        for comp in output.facts:
            assert comp.stereotype == "service", (
                f"Expected stereotype 'service', got '{comp.stereotype}' for {comp.name}"
            )

    def test_empty_repo_returns_zero(self, empty_repo: Path) -> None:
        output = SpringServiceCollector(repo_path=empty_repo).collect()
        assert output.fact_count == 0


# =============================================================================
# SpringRepositoryCollector
# =============================================================================


class TestSpringRepositoryCollector:
    def test_finds_repository(self, spring_repo: Path) -> None:
        output = SpringRepositoryCollector(repo_path=spring_repo).collect()
        assert output.fact_count >= 1
        assert any("FooRepository" in f.name for f in output.facts)

    def test_stereotype_is_repository(self, spring_repo: Path) -> None:
        output = SpringRepositoryCollector(repo_path=spring_repo).collect()
        for comp in output.facts:
            assert comp.stereotype == "repository", (
                f"Expected stereotype 'repository', got '{comp.stereotype}' for {comp.name}"
            )

    def test_empty_repo_returns_zero(self, empty_repo: Path) -> None:
        output = SpringRepositoryCollector(repo_path=empty_repo).collect()
        assert output.fact_count == 0
