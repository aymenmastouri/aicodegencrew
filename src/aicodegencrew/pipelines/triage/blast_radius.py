"""Blast-radius calculation via BFS on the component relation graph.

Loads relations from architecture_facts and builds an adjacency graph.
BFS from entry-point components to depth=3 to find the affected tree.
"""

from collections import deque
from typing import Any

from ...shared.utils.logger import setup_logger

logger = setup_logger(__name__)


def _build_adjacency(relations: list[dict]) -> dict[str, set[str]]:
    """Build bidirectional adjacency graph from relation records."""
    graph: dict[str, set[str]] = {}
    for rel in relations:
        src = rel.get("source", "") or rel.get("from", "")
        tgt = rel.get("target", "") or rel.get("to", "")
        if src and tgt:
            graph.setdefault(src, set()).add(tgt)
            graph.setdefault(tgt, set()).add(src)
    return graph


def calculate_blast_radius(
    entry_components: list[dict],
    knowledge_context: dict[str, Any],
    max_depth: int = 3,
) -> dict:
    """BFS from entry-point components to find affected components.

    Args:
        entry_components: List of entry-point dicts with "component" key.
        knowledge_context: Output from KnowledgeLoader.load_available_context().
        max_depth: Maximum BFS depth (default: 3).

    Returns:
        {
            "affected": [{"component": str, "depth": int}, ...],
            "depth": int,
            "component_count": int,
            "containers_affected": [str, ...],
        }
    """
    facts = knowledge_context.get("extract", {}).get("architecture_facts", {})
    relations = facts.get("relations", [])
    if not isinstance(relations, list):
        relations = []

    graph = _build_adjacency(relations)

    # Seed BFS with entry-point component names
    seeds = [ep.get("component", "") for ep in entry_components if ep.get("component")]
    if not seeds:
        return {"affected": [], "depth": 0, "component_count": 0, "containers_affected": []}

    visited: dict[str, int] = {}  # component → depth
    queue: deque[tuple[str, int]] = deque()
    for s in seeds:
        if s not in visited:
            visited[s] = 0
            queue.append((s, 0))

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                visited[neighbor] = depth + 1
                queue.append((neighbor, depth + 1))

    affected = [{"component": comp, "depth": d} for comp, d in visited.items()]
    affected.sort(key=lambda x: x["depth"])

    # Cross-reference with containers
    containers = facts.get("containers", [])
    container_names: list[str] = []
    if isinstance(containers, list):
        # Build component→container mapping
        comp_to_container: dict[str, str] = {}
        for c in containers:
            cname = c.get("name", "")
            for comp_ref in c.get("components", []):
                ref_name = comp_ref if isinstance(comp_ref, str) else comp_ref.get("name", "")
                if ref_name:
                    comp_to_container[ref_name] = cname

        affected_names = {a["component"] for a in affected}
        container_names = sorted({
            comp_to_container[cn]
            for cn in affected_names
            if cn in comp_to_container
        })

    max_d = max((a["depth"] for a in affected), default=0)

    logger.info(
        "[BlastRadius] %d components affected (depth=%d, containers=%d)",
        len(affected), max_d, len(container_names),
    )
    return {
        "affected": affected,
        "depth": max_d,
        "component_count": len(affected),
        "containers_affected": container_names,
    }
