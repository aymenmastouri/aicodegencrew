"""
Test Pattern Tool - Query test patterns from architecture facts.

Reads the `tests` dimension from architecture facts to provide agents with
existing test patterns (frameworks, assertion styles, directory conventions,
mock patterns) for generating consistent tests.
"""

import json
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ....shared.utils.logger import setup_logger
from ....shared.utils.token_budget import truncate_response

logger = setup_logger(__name__)


class TestPatternInput(BaseModel):
    """Input schema for TestPatternTool."""

    container: str = Field(
        default="",
        description="Filter by container name (e.g. 'backend', 'frontend')",
    )
    stereotype: str = Field(
        default="",
        description="Filter by tested component stereotype (e.g. 'service', 'controller', 'component')",
    )
    limit: int = Field(
        default=20,
        description="Maximum number of test patterns to return",
    )


class TestPatternTool(BaseTool):
    """
    Query test patterns from architecture facts.

    Reads the `tests` dimension to discover existing test conventions:
    frameworks, assertion styles, directory structure, and mock patterns.

    Usage Examples:
    1. query_test_patterns(container="backend", stereotype="service")
    2. query_test_patterns(container="frontend", limit=10)
    """

    name: str = "query_test_patterns"
    description: str = (
        "Query existing test patterns from architecture facts. "
        "Returns test frameworks, assertion styles, directory conventions, and mock patterns. "
        "Filter by container and/or tested component stereotype."
    )
    args_schema: type[BaseModel] = TestPatternInput

    # Configuration
    facts_dir: str = "knowledge/extract"

    # Cache
    _tests_data: dict | list | None = None

    def __init__(self, facts_dir: str = "knowledge/extract", **kwargs):
        """Initialize with facts directory."""
        super().__init__(**kwargs)
        if facts_dir:
            self.facts_dir = facts_dir
        self._tests_data = None

    def _load_tests(self) -> dict | list:
        """Load tests dimension data with caching."""
        if self._tests_data is not None:
            return self._tests_data

        # Try dimension file first
        tests_path = Path(self.facts_dir) / "tests.json"
        if tests_path.exists():
            try:
                with open(tests_path, encoding="utf-8") as f:
                    self._tests_data = json.load(f)
                logger.info(f"Loaded tests dimension from {tests_path}")
                return self._tests_data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not read tests.json: {e}")

        # Fallback to monolithic architecture_facts.json
        facts_path = Path(self.facts_dir) / "architecture_facts.json"
        if facts_path.exists():
            try:
                with open(facts_path, encoding="utf-8") as f:
                    facts = json.load(f)
                self._tests_data = facts.get("tests", {})
                logger.info("Loaded tests from architecture_facts.json")
                return self._tests_data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not read architecture_facts.json: {e}")

        self._tests_data = {}
        return self._tests_data

    def _run(
        self,
        container: str = "",
        stereotype: str = "",
        limit: int = 20,
    ) -> str:
        """Query test patterns with optional filtering."""
        try:
            tests_data = self._load_tests()
            limit = min(limit, 100)
            container_lower = container.lower() if container else ""
            stereotype_lower = stereotype.lower() if stereotype else ""

            # Handle different data structures
            if isinstance(tests_data, dict):
                patterns = self._extract_patterns_from_dict(tests_data, container_lower, stereotype_lower, limit)
            elif isinstance(tests_data, list):
                patterns = self._extract_patterns_from_list(tests_data, container_lower, stereotype_lower, limit)
            else:
                patterns = []

            result = {
                "container_filter": container,
                "stereotype_filter": stereotype,
                "total_count": len(patterns),
                "patterns": patterns[:limit],
            }

            output = json.dumps(result, indent=2, ensure_ascii=False)
            return truncate_response(output, hint="use filters to narrow results")

        except Exception as e:
            logger.error(f"TestPatternTool error: {e}")
            return json.dumps({"error": str(e), "patterns": [], "total_count": 0})

    def _extract_patterns_from_dict(
        self,
        data: dict,
        container_filter: str,
        stereotype_filter: str,
        limit: int,
    ) -> list[dict]:
        """Extract patterns from dict-structured tests data."""
        patterns = []

        # Common keys in tests dimension
        items = data.get("items", data.get("tests", []))
        if isinstance(items, list):
            for item in items:
                if self._matches_filters(item, container_filter, stereotype_filter):
                    patterns.append(self._normalize_pattern(item))
                    if len(patterns) >= limit:
                        break

        # Also include summary info if present
        if not patterns:
            # Return the dict structure itself as a single pattern summary
            summary = {}
            for key in ("frameworks", "assertion_styles", "directories", "mock_patterns", "total", "summary"):
                if key in data:
                    summary[key] = data[key]
            if summary:
                patterns.append(summary)

        return patterns

    def _extract_patterns_from_list(
        self,
        items: list,
        container_filter: str,
        stereotype_filter: str,
        limit: int,
    ) -> list[dict]:
        """Extract patterns from list-structured tests data."""
        patterns = []
        for item in items:
            if isinstance(item, dict) and self._matches_filters(item, container_filter, stereotype_filter):
                patterns.append(self._normalize_pattern(item))
                if len(patterns) >= limit:
                    break
        return patterns

    @staticmethod
    def _matches_filters(item: dict, container_filter: str, stereotype_filter: str) -> bool:
        """Check if a test pattern matches the given filters."""
        if container_filter:
            item_container = (item.get("container", "") or item.get("module", "") or "").lower()
            if container_filter not in item_container:
                return False

        if stereotype_filter:
            item_stereotype = (
                item.get("stereotype", "") or item.get("tested_stereotype", "") or item.get("type", "") or ""
            ).lower()
            if stereotype_filter not in item_stereotype:
                return False

        return True

    @staticmethod
    def _normalize_pattern(item: dict) -> dict:
        """Normalize a test pattern to a consistent structure."""
        return {
            "name": item.get("name", ""),
            "file_path": item.get("file_path", ""),
            "container": item.get("container", ""),
            "framework": item.get("framework", item.get("test_framework", "")),
            "assertion_style": item.get("assertion_style", ""),
            "directory": item.get("directory", item.get("test_directory", "")),
            "mock_patterns": item.get("mock_patterns", item.get("mocks", [])),
            "tested_component": item.get("tested_component", ""),
            "stereotype": item.get("stereotype", item.get("tested_stereotype", "")),
        }
