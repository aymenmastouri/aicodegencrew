"""Preflight: Dependency graph builder for affected files.

Topological sort of affected files so base-level files are generated
before their consumers. Deterministic — no LLM calls.

Duration: 1-2s (graph algorithm only)
"""

import json
from collections import defaultdict, deque
from pathlib import Path

from ....shared.utils.logger import setup_logger
from ..schemas import ComponentTarget, FileGenerationEntry, GenerationOrder
from .import_index import ImportIndex

logger = setup_logger(__name__)


class DependencyGraphBuilder:
    """Build a dependency graph and topologically sort affected files."""

    def __init__(self, facts_path: str = "knowledge/extract/architecture_facts.json"):
        self.facts_path = Path(facts_path)

    def run(
        self,
        affected_components: list[ComponentTarget],
        import_index: ImportIndex,
    ) -> GenerationOrder:
        if not affected_components:
            return GenerationOrder()

        affected_paths = {c.file_path for c in affected_components}
        comp_by_path = {c.file_path: c for c in affected_components}

        graph = self._build_graph(affected_paths, import_index)
        ordered, tiers = self._topo_sort(graph, affected_paths)

        entries = []
        for file_path in ordered:
            tier = tiers.get(file_path, 0)
            deps = [d for d in graph.get(file_path, []) if d in affected_paths]
            consumers = [
                f for f, dep_list in graph.items()
                if file_path in dep_list and f in affected_paths
            ]
            entries.append(FileGenerationEntry(
                file_path=file_path,
                component=comp_by_path.get(file_path),
                depends_on=deps,
                depended_by=consumers,
                generation_tier=tier,
            ))

        result = GenerationOrder(
            ordered_files=entries,
            dependency_graph={f: list(deps) for f, deps in graph.items() if f in affected_paths},
        )

        logger.info(
            "[Preflight] Dependency graph: %d files, %d tiers",
            len(entries),
            max(tiers.values()) + 1 if tiers else 1,
        )
        for tier_num in sorted(set(tiers.values())):
            tier_files = [Path(f).name for f, t in tiers.items() if t == tier_num]
            logger.info("[Preflight]   Tier %d: %s", tier_num, ", ".join(tier_files))

        return result

    def _build_graph(
        self,
        affected_paths: set[str],
        import_index: ImportIndex,
    ) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {f: [] for f in affected_paths}

        facts_deps = self._load_facts_relations(affected_paths)
        for source, targets in facts_deps.items():
            for target in targets:
                if target in affected_paths and target != source:
                    if target not in graph[source]:
                        graph[source].append(target)

        # Reserved for future enrichment from import_index (currently deterministic facts + heuristics).
        _ = import_index

        self._infer_module_dependencies(graph, affected_paths)
        return graph

    def _load_facts_relations(self, affected_paths: set[str]) -> dict[str, list[str]]:
        deps: dict[str, list[str]] = defaultdict(list)

        if not self.facts_path.exists():
            return deps

        try:
            with open(self.facts_path, encoding="utf-8") as f:
                facts = json.load(f)
        except Exception as e:
            logger.debug("[Preflight] Could not load architecture_facts: %s", e)
            return deps

        norm_affected: dict[str, str] = {}
        for p in affected_paths:
            norm = p.replace("\\", "/")
            norm_affected[norm] = p
            norm_affected[Path(p).name] = p

        id_to_path: dict[str, str] = {}
        for comp in facts.get("components", []):
            comp_id = comp.get("id", "")
            raw_paths = comp.get("file_paths") or []
            if isinstance(raw_paths, str):
                raw_paths = [raw_paths]
            comp_path = comp.get("file_path", "")
            if comp_path:
                raw_paths = [comp_path, *raw_paths]

            if not comp_id or not raw_paths:
                continue

            for p in raw_paths:
                norm = str(p).replace("\\", "/")
                if norm in norm_affected:
                    id_to_path[comp_id] = norm_affected[norm]
                    break
                name = Path(str(p)).name
                if name in norm_affected:
                    id_to_path[comp_id] = norm_affected[name]
                    break

        for rel in facts.get("relations", []):
            source_id = rel.get("from") or rel.get("source") or rel.get("from_id", "")
            target_id = rel.get("to") or rel.get("target") or rel.get("to_id", "")
            source_path = id_to_path.get(source_id)
            target_path = id_to_path.get(target_id)
            if source_path and target_path and source_path != target_path:
                deps[source_path].append(target_path)

        return deps

    @staticmethod
    def _infer_module_dependencies(graph: dict[str, list[str]], affected_paths: set[str]) -> None:
        modules: dict[str, str] = {}
        for p in affected_paths:
            name = Path(p).name.lower()
            if ".module." in name:
                key = name.split(".module.")[0]
                modules[key] = p

        app_mod = modules.get("app")
        if app_mod:
            for key in ("core", "shared"):
                dep = modules.get(key)
                if dep and dep not in graph.get(app_mod, []):
                    graph[app_mod].append(dep)

        routing_mod = modules.get("app-routing") or modules.get("app.routing")
        if routing_mod:
            for key, path in modules.items():
                if key not in ("app", "app-routing", "app.routing", "core", "shared"):
                    if path not in graph.get(routing_mod, []):
                        graph[routing_mod].append(path)

    @staticmethod
    def _topo_sort(
        graph: dict[str, list[str]],
        affected_paths: set[str],
    ) -> tuple[list[str], dict[str, int]]:
        in_degree: dict[str, int] = {f: 0 for f in affected_paths}
        adj: dict[str, list[str]] = {f: [] for f in affected_paths}

        for node, deps in graph.items():
            if node not in affected_paths:
                continue
            for dep in deps:
                if dep in affected_paths and dep != node:
                    adj[dep].append(node)
                    in_degree[node] = in_degree.get(node, 0) + 1

        queue: deque[str] = deque()
        tiers: dict[str, int] = {}
        for node in affected_paths:
            if in_degree.get(node, 0) == 0:
                queue.append(node)
                tiers[node] = 0

        ordered: list[str] = []
        while queue:
            node = queue.popleft()
            ordered.append(node)
            for consumer in adj.get(node, []):
                in_degree[consumer] -= 1
                if in_degree[consumer] == 0:
                    queue.append(consumer)
                    tiers[consumer] = tiers[node] + 1

        remaining = affected_paths - set(ordered)
        if remaining:
            max_tier = max(tiers.values()) + 1 if tiers else 0
            logger.warning(
                "[Preflight] Cycle detected among %d files, placing at tier %d",
                len(remaining), max_tier,
            )
            for node in sorted(remaining):
                ordered.append(node)
                tiers[node] = max_tier

        return ordered, tiers
