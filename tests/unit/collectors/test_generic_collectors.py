"""Unit tests for generic (framework-agnostic) collectors.

Tests:
- ContainerCollector  — detects backend (pom.xml/Spring Boot) + frontend (package.json/Angular)
- DependencyCollector — extracts Maven deps from pom.xml, NPM deps from package.json

All tests are purely deterministic — no LLM calls, no network access.
"""

from pathlib import Path

import pytest

from aicodegencrew.pipelines.architecture_facts.collectors.container_collector import (
    ContainerCollector,
)
from aicodegencrew.pipelines.architecture_facts.collectors.dependency_collector import (
    DependencyCollector,
)


# =============================================================================
# ContainerCollector
# =============================================================================


class TestContainerCollector:
    def test_backend_detected(self, container_repo: Path) -> None:
        """Spring Boot backend directory must be identified as type 'backend'."""
        output = ContainerCollector(repo_path=container_repo).collect()
        assert output.fact_count >= 1
        assert any(
            "backend" in f.name.lower() or f.type == "backend"
            for f in output.facts
        ), f"No backend container found; containers: {[(f.name, f.type) for f in output.facts]}"

    def test_frontend_detected(self, container_repo: Path) -> None:
        """Angular frontend directory must be identified as type 'frontend'."""
        output = ContainerCollector(repo_path=container_repo).collect()
        assert any(
            "frontend" in f.name.lower() or f.type == "frontend"
            for f in output.facts
        ), f"No frontend container found; containers: {[(f.name, f.type) for f in output.facts]}"

    def test_empty_repo_returns_zero(self, empty_repo: Path) -> None:
        output = ContainerCollector(repo_path=empty_repo).collect()
        assert output.fact_count == 0


# =============================================================================
# DependencyCollector
# =============================================================================


class TestDependencyCollector:
    def test_maven_deps_found(self, container_repo: Path) -> None:
        """Maven dependencies from backend/pom.xml must be extracted."""
        output = DependencyCollector(repo_path=container_repo).collect()
        maven_deps = [
            f for f in output.facts
            if hasattr(f, "type") and f.type == "maven"
        ]
        assert len(maven_deps) >= 1, "No Maven dependencies found"
        # Sanity: spring-boot-starter-web should be present
        names = [f.name for f in maven_deps]
        assert any("spring-boot" in n.lower() for n in names), (
            f"spring-boot not found in Maven deps: {names}"
        )

    def test_npm_deps_found(self, container_repo: Path) -> None:
        """NPM dependencies from frontend/package.json must be extracted."""
        output = DependencyCollector(repo_path=container_repo).collect()
        npm_deps = [
            f for f in output.facts
            if hasattr(f, "type") and f.type == "npm"
        ]
        assert len(npm_deps) >= 1, "No NPM dependencies found"
        names = [f.name for f in npm_deps]
        assert any("@angular" in n for n in names), (
            f"@angular not found in NPM deps: {names}"
        )

    def test_versions_parsed(self, container_repo: Path) -> None:
        """At least some dependencies should carry a non-empty version string."""
        output = DependencyCollector(repo_path=container_repo).collect()
        assert output.fact_count >= 1
        versioned = [
            f for f in output.facts
            if hasattr(f, "version") and f.version
        ]
        assert len(versioned) >= 1, (
            f"No deps with non-empty versions; all versions: {[getattr(f, 'version', None) for f in output.facts]}"
        )
