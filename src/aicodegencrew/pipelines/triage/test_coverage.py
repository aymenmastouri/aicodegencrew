"""Test coverage cross-reference for affected components.

Matches affected component file paths against test file paths from
architecture_facts.tests dimension.
"""

from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def _normalize_path(path: str) -> str:
    """Normalize a path for comparison: lowercase, forward slashes."""
    return path.replace("\\", "/").lower()


def _source_to_test_pattern(source_path: str) -> list[str]:
    """Generate candidate test file name patterns from a source path.

    e.g. 'UserService.java' → ['userservicetest', 'userservice_test', 'testuserservice']
    """
    import re

    # Extract base filename without extension
    parts = source_path.replace("\\", "/").split("/")
    filename = parts[-1] if parts else source_path
    base = filename.rsplit(".", 1)[0].lower()

    # Split camelCase
    words = re.findall(r"[a-z]+", base)
    joined = "".join(words)

    return [
        f"{joined}test",
        f"{joined}_test",
        f"test{joined}",
        f"test_{joined}",
        f"{joined}.spec",
        f"{joined}.test",
    ]


def check_test_coverage(
    affected_components: list[dict],
    knowledge_context: dict[str, Any],
) -> dict:
    """Cross-reference affected components with known tests.

    Args:
        affected_components: Blast-radius affected components (with "component" key).
        knowledge_context:   Output from KnowledgeLoader.load_available_context().

    Returns:
        {"covered": [str], "uncovered": [str], "coverage_ratio": float}
    """
    facts = knowledge_context.get("extract", {}).get("architecture_facts", {})
    tests = facts.get("tests", [])
    if not isinstance(tests, list):
        tests = []

    # Build a set of normalized test paths for fast lookup
    test_paths_norm = set()
    test_names_norm = set()
    for t in tests:
        tp = t.get("file_path", "") or t.get("path", "")
        if tp:
            test_paths_norm.add(_normalize_path(tp))
            # Also index the base filename
            base = tp.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0].lower()
            test_names_norm.add(base)

    covered: list[str] = []
    uncovered: list[str] = []

    for comp in affected_components:
        comp_name = comp.get("component", "")
        if not comp_name:
            continue

        # Try matching via test name patterns
        patterns = _source_to_test_pattern(comp_name)
        found = any(p in test_names_norm for p in patterns)

        # Also try partial path match
        if not found:
            comp_lower = comp_name.lower()
            found = any(comp_lower in tp for tp in test_paths_norm)

        if found:
            covered.append(comp_name)
        else:
            uncovered.append(comp_name)

    total = len(covered) + len(uncovered)
    ratio = round(len(covered) / total, 2) if total > 0 else 0.0

    logger.info("[TestCoverage] %d/%d covered (%.0f%%)", len(covered), total, ratio * 100)
    return {
        "covered": covered,
        "uncovered": uncovered,
        "coverage_ratio": ratio,
    }
