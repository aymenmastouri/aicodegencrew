"""Unit tests for Angular collectors.

Tests:
- AngularComponentCollector — @Component (standalone, selector), @Directive
- AngularServiceCollector   — @Injectable, stereotype=service
- AngularRoutingCollector   — route paths, lazy-loaded routes

All tests are purely deterministic — no LLM calls, no network access.
"""

from pathlib import Path

from aicodegencrew.pipelines.architecture_facts.collectors.angular.component_collector import (
    AngularComponentCollector,
)
from aicodegencrew.pipelines.architecture_facts.collectors.angular.routing_collector import (
    AngularRoutingCollector,
)
from aicodegencrew.pipelines.architecture_facts.collectors.angular.service_collector import (
    AngularServiceCollector,
)

# =============================================================================
# AngularComponentCollector
# =============================================================================


class TestAngularComponentCollector:
    def test_finds_component(self, angular_repo: Path) -> None:
        output = AngularComponentCollector(repo_path=angular_repo).collect()
        assert output.fact_count >= 1
        assert any("FooComponent" in f.name for f in output.facts)

    def test_standalone_flag(self, angular_repo: Path) -> None:
        """Component with standalone: true must have the flag in metadata and tags."""
        output = AngularComponentCollector(repo_path=angular_repo).collect()
        foo = next((f for f in output.facts if f.name == "FooComponent"), None)
        assert foo is not None, "FooComponent not found in output"
        assert foo.metadata.get("standalone") is True, "standalone metadata missing"
        assert "standalone" in foo.tags, "standalone tag missing"

    def test_finds_directive(self, angular_repo: Path) -> None:
        output = AngularComponentCollector(repo_path=angular_repo).collect()
        directives = [f for f in output.facts if f.stereotype == "directive"]
        assert len(directives) >= 1, "No directive facts found"
        assert any("Highlight" in f.name for f in directives)

    def test_empty_repo_returns_zero(self, empty_repo: Path) -> None:
        output = AngularComponentCollector(repo_path=empty_repo).collect()
        assert output.fact_count == 0


# =============================================================================
# AngularServiceCollector
# =============================================================================


class TestAngularServiceCollector:
    def test_finds_service(self, angular_repo: Path) -> None:
        output = AngularServiceCollector(repo_path=angular_repo).collect()
        # At least the FooService should be detected
        services = [f for f in output.facts if hasattr(f, "stereotype") and f.stereotype == "service"]
        assert len(services) >= 1, "No service facts found"

    def test_injectable_stereotype(self, angular_repo: Path) -> None:
        output = AngularServiceCollector(repo_path=angular_repo).collect()
        foo = next((f for f in output.facts if "FooService" in f.name), None)
        assert foo is not None, "FooService not found in output"
        assert foo.stereotype == "service", f"Expected stereotype 'service', got '{foo.stereotype}'"

    def test_empty_repo_returns_zero(self, empty_repo: Path) -> None:
        output = AngularServiceCollector(repo_path=empty_repo).collect()
        assert output.fact_count == 0


# =============================================================================
# AngularRoutingCollector
# =============================================================================


class TestAngularRoutingCollector:
    def test_route_paths_extracted(self, angular_repo: Path) -> None:
        """Routing file must produce at least one RawInterface with a path."""
        output = AngularRoutingCollector(repo_path=angular_repo).collect()
        assert output.fact_count >= 1
        paths = [f.path for f in output.facts if hasattr(f, "path") and f.path is not None]
        assert len(paths) >= 1, f"No route paths found; facts: {output.facts}"

    def test_lazy_load_detected(self, angular_repo: Path) -> None:
        """The dashboard lazy route must produce a fact tagged 'lazy-loaded'."""
        output = AngularRoutingCollector(repo_path=angular_repo).collect()
        lazy = [f for f in output.facts if "lazy-loaded" in f.tags]
        assert len(lazy) >= 1, f"No lazy-loaded route found; all tags: {[f.tags for f in output.facts]}"
