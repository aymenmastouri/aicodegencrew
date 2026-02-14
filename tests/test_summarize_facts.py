"""Test the _summarize_facts method for compact output."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aicodegencrew.crews.architecture_synthesis.arc42.crew import Arc42Crew
from aicodegencrew.crews.architecture_synthesis.arc42.tasks import CH08_PART2_PATTERNS


def _make_crew_with_facts(facts: dict, analysis: dict | None = None) -> Arc42Crew:
    """Create an Arc42Crew with injected facts (no file I/O)."""
    with patch.object(Arc42Crew, "__init__", lambda self, **kw: None):
        crew = Arc42Crew.__new__(Arc42Crew)
    crew.facts = facts
    crew.analysis = analysis or {}
    crew.evidence = {}
    crew.output_dir = Path(".")
    return crew


def test_summarize_facts_is_compact():
    """Verify that facts summary stays under 6000 chars for LLM context."""
    facts_path = Path(__file__).parent.parent / "knowledge" / "architecture" / "architecture_facts.json"

    if not facts_path.exists():
        pytest.skip(f"{facts_path} not found")

    with open(facts_path, encoding="utf-8") as f:
        facts = json.load(f)

    analyzed_path = facts_path.parent / "analyzed_architecture.json"
    analysis = {}
    if analyzed_path.exists():
        with open(analyzed_path, encoding="utf-8") as f:
            analysis = json.load(f)

    crew = _make_crew_with_facts(facts, analysis)
    result = crew._summarize_facts()

    assert isinstance(result, dict)

    system_summary = result.get("system_summary", "")
    assert len(system_summary) > 0, "system_summary should not be empty"
    assert len(system_summary) < 6000, f"system_summary too large: {len(system_summary)} chars"


def test_summarize_facts_minimal():
    """Verify _summarize_facts works with minimal/empty facts."""
    crew = _make_crew_with_facts({"components": [], "containers": [], "relations": [], "interfaces": []})
    result = crew._summarize_facts()

    assert isinstance(result, dict)
    assert "system_summary" in result
    assert "containers_summary" in result


def test_arc42_task_template_formatting_is_safe():
    """Arc42 task templates must format cleanly with crew template data."""
    formatted = CH08_PART2_PATTERNS.format(
        system_name="System",
        system_summary="Summary",
        containers_summary="Containers",
        components_summary="Components",
        relations_summary="Relations",
        interfaces_summary="Interfaces",
        building_blocks_data="Blocks",
    )
    assert "application-{profile}.yml" in formatted


if __name__ == "__main__":
    test_summarize_facts_is_compact()
    test_summarize_facts_minimal()
